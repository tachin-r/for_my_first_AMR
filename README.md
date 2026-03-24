# 🤖 AMR (Autonomous Mobile Robot) — ROS2 Jazzy

> **เครื่องมือ:** Raspberry Pi 5 + ESP32 + YD-LiDAR X3 Pro + L298N Motor Driver  
> **OS:** Ubuntu 24.04 | **ROS2:** Jazzy LTS (May 2029)

## 🍓 Deploy บน Pi5?
ดู **[docs/pi5_setup_guide.md](docs/pi5_setup_guide.md)** — ทำตามทีละขั้น จาก clone → SLAM


---

## ⚠️ อ่านก่อน — ข้อผิดพลาดที่เจอบ่อย

| ปัญหา | สาเหตุ | แก้ไข |
|---|---|---|
| `cannot bind to serial port` | ไม่มีสิทธิ์ access USB | ทำ udev (Step 3) หรือ `sudo chmod 666 /dev/ttyUSBx` |
| `Failed to start scan mode` | `isSingleChannel` ผิด | ต้อง `true` สำหรับ X3 Pro |
| `No executable found` | ไม่มี setup.cfg | ต้อง rebuild หลังสร้าง setup.cfg |
| `ledcAttach not declared` | arduino-esp32 version ผิด | ใช้ `analogWrite()` แทน (แก้แล้วในโค้ด) |
| motor ไม่หมุน 10 วินาที | KP ต่ำเกินไป | ค่าใหม่ KP=400 แก้แล้ว |
| `/dev/esp32` not found | ยังไม่ทำ udev | ทำ Step 3 หรือใช้ `/dev/ttyUSB0` แทน |

---

## Hardware

```
Raspberry Pi 5
├── USB → YD-LiDAR X3 Pro   (/dev/lidar หลัง udev)
└── USB → ESP32              (/dev/esp32 หลัง udev)
         └── GPIO → L298N Motor Driver
                   ├── Motor A (Left)  + Encoder A
                   └── Motor B (Right) + Encoder B
```

| ส่วน | รายละเอียด |
|---|---|
| LiDAR | YD-LiDAR X3 Pro (Model: S2PRO) — 4kHz, 720 pts/scan, 10Hz |
| MCU | ESP32 38-pin (ESP32dev) |
| Motor Driver | L298N |
| Encoders | Quadrature, 506 PPR, 1:46 gear, ล้อ 65mm |
| Wheelbase | 200mm (center-to-center) |

---

## 📁 โครงสร้าง Project

```
for_my_first_AMR/
├── docs/                          ← คู่มือทุกอย่าง
│   ├── ydlidar_x3pro_setup.md    ← LiDAR setup + troubleshooting
│   └── amr_stack_reference.md   ← Architecture + code reference
├── esp32_firmware/               ← PlatformIO project
│   ├── platformio.ini
│   └── src/main.cpp              ← PID motor controller
├── scripts/
│   └── setup_udev.sh            ← lock USB ports (ทำครั้งเดียว)
└── ros2_ws/src/amr_base/        ← ROS2 package
    ├── amr_base/esp32_bridge.py ← Serial bridge node
    ├── config/amr_config.yaml   ← Robot parameters
    ├── launch/amr_launch.py     ← Launch everything
    └── params/X3Pro.yaml        ← LiDAR params (confirmed)
```

---

## 🚀 Setup Guide (ทำตามลำดับ!)

### Step 1: Clone & Install YDLidar-SDK

> ⚠️ **ต้องทำก่อน build ros2 workspace** ไม่งั้น build ไม่ผ่าน

```bash
git clone https://github.com/tachin-r/for_my_first_AMR.git ~/amr
cd /tmp
git clone --depth 1 https://github.com/YDLIDAR/YDLidar-SDK.git
cd YDLidar-SDK && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install && sudo ldconfig
```

### Step 2: Build ROS2 Workspace

```bash
source /opt/ros/jazzy/setup.bash
cd ~/amr/ros2_ws

# Clone ydlidar driver (ต้องทำทุกครั้งที่ clone repo ใหม่)
git clone -b humble https://github.com/YDLIDAR/ydlidar_ros2_driver.git src/ydlidar_ros2_driver

# Build
colcon build --symlink-install

# Auto-source (ทำครั้งเดียว)
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
echo 'source ~/amr/ros2_ws/install/setup.bash' >> ~/.bashrc
source ~/.bashrc
```

### Step 3: Setup USB Port Lock (udev)

> ทั้ง ESP32 และ LiDAR มี CP210x ที่ SerialNumber เหมือนกัน ต้อง lock ด้วย physical path

```bash
# เสียบ ESP32 และ LiDAR ก่อน
sudo bash ~/amr/scripts/setup_udev.sh

# ถอดแล้วเสียบ USB ใหม่ทั้งสองสาย แล้วตรวจสอบ
ls -la /dev/esp32 /dev/lidar
# ต้องเห็น symlink: /dev/esp32 → ttyUSBx, /dev/lidar → ttyUSBy
```

### Step 4: Flash ESP32 Firmware

```bash
# เปิด esp32_firmware/ ใน VSCode
# ติดตั้ง PlatformIO IDE extension
# กด ✓ Build แล้ว → Upload
# ตรวจสอบใน Serial Monitor: {"status":"ready","fw":"1.0"}
```

### Step 5: รัน Full Stack

```bash
# วิธีที่ 1 — หลังทำ udev แล้ว (แนะนำ)
ros2 launch amr_base amr_launch.py

# วิธีที่ 2 — ก่อนทำ udev (ใช้ ttyUSB โดยตรง)
ros2 launch amr_base amr_launch.py \
  esp32_port:=/dev/ttyUSB0 \
  lidar_port:=/dev/ttyUSB1
```

### Step 6: ตรวจสอบ

```bash
# Terminal 2
ros2 topic list
# ต้องเห็น: /scan, /odom, /cmd_vel, /tf

ros2 topic hz /scan    # ~10 Hz
ros2 topic hz /odom    # ~20 Hz

# ทดสอบขับ
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.1}, angular: {z: 0.0}}" --rate 10
```

---

## 🔧 Troubleshooting

### LiDAR ไม่ scan

```bash
# ดู error
ros2 run ydlidar_ros2_driver ydlidar_ros2_driver_node \
  --ros-args --params-file ros2_ws/src/ydlidar_ros2_driver/params/X3Pro.yaml
# ดู docs/ydlidar_x3pro_setup.md สำหรับ error แต่ละอย่าง
```

### ESP32 ไม่ตอบสนอง

```bash
# ทดสอบ serial ตรงๆ
screen /dev/ttyUSB0 115200
# พิมพ์: {"l":0.1,"r":0.1}  แล้วกด Enter
# กด Ctrl+A K เพื่อออก
```

### Rebuild หลัง pull code ใหม่

```bash
cd ~/amr/ros2_ws
colcon build --packages-select amr_base --symlink-install
source install/setup.bash
```

---

## 📌 Notes สำคัญ

- `ydlidar_ros2_driver` ไม่ได้ commit ไว้ใน repo (ใน .gitignore) → ต้อง `git clone` ทุกครั้ง
- `ros2_ws/build/` และ `install/` ไม่ได้ commit → ต้อง `colcon build` ทุกครั้งที่ clone ใหม่
- PID tune ได้ real-time: `echo '{"pid_kp":400}' > /dev/esp32`
- Safety timeout 500ms: ESP32 หยุดมอเตอร์ถ้าไม่ได้รับคำสั่งนาน 500ms
