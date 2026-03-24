# YD-LiDAR X3 Pro — ROS2 Jazzy Setup Guide

> **Tested on:** Ubuntu 24.04 + ROS2 Jazzy  
> **Hardware confirmed:** Model S2PRO, FW 3.1, HW 3, 4kHz, 720 pts/scan

---

## ⚠️ ก่อนเริ่ม — สิ่งที่ต้องรู้

### X3 Pro ≠ X3 ธรรมดา — params ต่างกัน!
| Parameter | X3 ธรรมดา | **X3 Pro (S2PRO)** |
|---|---|---|
| `baudrate` | 115200 | **115200** (เหมือนกัน) |
| `isSingleChannel` | true | **true** |
| `support_motor_dtr` | true | **true** |
| `sample_rate` | 3 | **4** |
| `fixed_resolution` | true | **true** |

### USB Port Conflict
X3 Pro และ ESP32/Arduino ใช้ชิป **CP210x** เหมือนกัน → ต้องระวังเสียบผิด port

---

## Step 1: ติดตั้ง YDLidar-SDK (ทำก่อนเสมอ!)

```bash
# Clone SDK
cd /tmp
git clone --depth 1 https://github.com/YDLIDAR/YDLidar-SDK.git

# Build
cd YDLidar-SDK
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)

# Install (system-wide)
sudo make install
sudo ldconfig
```

> **ถ้าข้าม step นี้** → `colcon build` จะ error ว่าหา SDK ไม่เจอ

---

## Step 2: Clone และ Build ROS2 Driver

```bash
# สร้าง workspace (ถ้ายังไม่มี)
mkdir -p ~/amr_ws/src && cd ~/amr_ws/src

# Clone branch humble (รองรับ Jazzy ด้วย)
git clone -b humble https://github.com/YDLIDAR/ydlidar_ros2_driver.git

# Build
cd ~/amr_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

> Warnings เรื่อง `unused parameter` เป็นเรื่องปกติ — ไม่ใช่ error

---

## Step 3: ตั้งค่า USB Permission

```bash
# เพิ่ม user เข้า dialout group (ทำครั้งเดียว)
sudo usermod -a -G dialout $USER

# Logout แล้ว Login ใหม่ จากนั้นยืนยัน
groups | grep dialout
```

---

## Step 4: ระบุ Port ของ LiDAR

```bash
# ดู USB devices
lsusb | grep -i silicon

# ดู port ที่ assign
ls /dev/ttyUSB*

# ทดสอบว่า port ไหนคือ LiDAR (เสีย LiDAR แล้วดูว่า port ไหนหาย)
```

---

## Step 5: รัน Driver

```bash
source /opt/ros/jazzy/setup.bash
source ~/amr_ws/install/setup.bash

ros2 run ydlidar_ros2_driver ydlidar_ros2_driver_node \
  --ros-args --params-file \
  ~/amr_ws/src/ydlidar_ros2_driver/params/X3Pro.yaml
```

**Output ที่ถูกต้อง:**
```
[info] Lidar successfully connected [/dev/ttyUSB1:115200]
[info] Lidar running correctly! The health status good
[info] Successed to start scan mode...
[info] Now lidar is scanning...
```

---

## Step 6: ยืนยันว่า Scan Data มา

```bash
# Terminal ใหม่
source /opt/ros/jazzy/setup.bash
source ~/amr_ws/install/setup.bash

ros2 topic echo /scan --once
# ต้องเห็น ranges: [0.xxx, 0.xxx, ...] เต็มๆ
```

---

## Params File (X3Pro.yaml) — Final Confirmed

```yaml
ydlidar_ros2_driver_node:
  ros__parameters:
    port: /dev/ttyUSB1        # แก้ตาม port จริง
    frame_id: laser_frame
    ignore_array: ""
    baudrate: 115200
    lidar_type: 1
    device_type: 0
    isSingleChannel: true
    support_motor_dtr: true
    intensity: false
    intensity_bit: 0
    sample_rate: 4            # 4kHz (confirmed from device)
    frequency: 10.0
    fixed_resolution: true    # 720 pts/scan
    abnormal_check_count: 4
    auto_reconnect: true
    angle_max: 180.0
    angle_min: -180.0
    range_max: 8.0
    range_min: 0.1
    reversion: false
    inverted: false
    invalid_range_is_inf: false
    debug: false
```

---

## Troubleshooting

| Error | สาเหตุ | แก้ไข |
|---|---|---|
| `Error, cannot bind to serial port` | ไม่มีสิทธิ์ access port | `sudo usermod -a -G dialout $USER` แล้ว login ใหม่ |
| `Failed to start scan mode -1` | `isSingleChannel` ผิด | เปลี่ยนเป็น `true` |
| `Cannot retrieve Lidar health code` | ปกติสำหรับ X3 Pro | ไม่ต้องสนใจ — scan ยังทำงานได้ |
| `Fail to get baseplate device information` | ปกติสำหรับ X3 Pro | ไม่ต้องสนใจ — scan ยังทำงานได้ |
| เชื่อมต่อได้แต่ scan ไม่มาข้อมูล | ต่อผิด port (ต่อกับ ESP32 แทน) | ลอง ttyUSB0/1 สลับกัน |
| `colcon build` error หา SDK ไม่เจอ | ไม่ได้ติดตั้ง YDLidar-SDK ก่อน | ทำ Step 1 ก่อน |

---

## Lock Port ถาวร (udev rule)

เนื่องจาก X3 Pro และ ESP32 ใช้ CP210x ที่มี `SerialNumber=0001` เหมือนกัน  
ต้อง lock ด้วย **physical USB port path** แทน serial number:

```bash
# ดู USB path จาก dmesg หลังเสียบ LiDAR
dmesg | tail -10 | grep "usb\|ttyUSB"
# หา path เช่น "7-2.4" → นั่นคือ physical port ของ LiDAR

# ตัวอย่าง udev rule
echo 'SUBSYSTEM=="tty", DEVPATH=="*7-2.4*", SYMLINK+="lidar", MODE="0666"' \
  | sudo tee /etc/udev/rules.d/99-amr-usb.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

หรือรัน script อัตโนมัติ:
```bash
sudo bash /home/tachin/for_my_first_AMR/scripts/setup_udev.sh
```
