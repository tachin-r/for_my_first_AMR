# 🍓 Pi5 Setup Guide — AMR Stack

> ทำตามลำดับ! ข้ามขั้นไหนไม่ได้ มีปัญหาไปดู [Troubleshooting](#troubleshooting)

---

## Prerequisites — Pi5 ต้องมีก่อน

- Ubuntu 24.04 (64-bit) ติดตั้งบน Pi5
- ROS2 Jazzy ติดตั้งแล้ว
- เชื่อม internet ได้
- เสียบ ESP32 + LiDAR ผ่าน USB Hub

---

## Step 1 — Clone Repo

```bash
git clone https://github.com/tachin-r/for_my_first_AMR.git ~/amr
cd ~/amr
```

---

## Step 2 — ติดตั้ง Dependencies

```bash
# ROS2 packages
sudo apt update
sudo apt install -y \
  ros-jazzy-slam-toolbox \
  ros-jazzy-nav2-map-server \
  ros-jazzy-robot-state-publisher \
  ros-jazzy-teleop-twist-keyboard \
  ros-jazzy-tf2-tools

# Python serial
pip install pyserial --break-system-packages
```

---

## Step 3 — ติดตั้ง YDLidar-SDK

> ⚠️ ต้องทำก่อน build ros2 workspace เสมอ

```bash
cd /tmp
git clone --depth 1 https://github.com/YDLIDAR/YDLidar-SDK.git
cd YDLidar-SDK && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j4        # Pi5 ใช้ -j4
sudo make install
sudo ldconfig
echo "✅ YDLidar-SDK installed"
```

---

## Step 4 — Clone YDLidar ROS2 Driver

```bash
cd ~/amr/ros2_ws/src
git clone -b humble https://github.com/YDLIDAR/ydlidar_ros2_driver.git
```

---

## Step 5 — Build Workspace

```bash
source /opt/ros/jazzy/setup.bash
cd ~/amr/ros2_ws
colcon build --symlink-install
echo "✅ Build done"
```

> ⏳ Pi5 ใช้เวลา ~5-10 นาที รอได้เลย

---

## Step 6 — Auto-source (ทำครั้งเดียว)

```bash
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
echo 'source ~/amr/ros2_ws/install/setup.bash' >> ~/.bashrc
source ~/.bashrc
echo "✅ Auto-source set"
```

---

## Step 7 — Lock USB Ports (udev)

> ⚠️ เสียบ ESP32 และ LiDAR ก่อนรันคำสั่งนี้

```bash
sudo bash ~/amr/scripts/setup_udev.sh
```

แล้ว **ถอดเสียบ USB ใหม่** แล้วตรวจสอบ:

```bash
ls -la /dev/esp32 /dev/lidar
# ต้องเห็น:
# /dev/esp32 -> ttyUSBx
# /dev/lidar -> ttyUSBy
```

ถ้าไม่เห็น symlink → ดู [Troubleshooting: USB](#usb-port-ไม่ถูก)

---

## Step 8 — ตรวจสอบก่อนรัน

```bash
# เช็ค USB permissions
groups | grep dialout      # ต้องมี "dialout"

# ถ้าไม่มี
sudo usermod -a -G dialout $USER
# แล้ว logout/login ใหม่
```

---

## Step 9 — รัน (เลือกอย่างใดอย่างหนึ่ง)

### A. Full Stack เฉยๆ (ไม่ SLAM)

```bash
ros2 launch amr_base amr_launch.py
```

### B. SLAM Mode (แนะนำ)

```bash
ros2 launch amr_base slam_launch.py
```

### ถ้ายังไม่ทำ udev ใช้แบบนี้แทน

```bash
ros2 launch amr_base slam_launch.py \
  esp32_port:=/dev/ttyUSB0 \
  lidar_port:=/dev/ttyUSB1
```

---

## Step 10 — ขับและ Map ห้อง

Terminal ใหม่:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

| ปุ่ม | การเคลื่อนที่ |
|---|---|
| `i` | เดินหน้า |
| `,` | ถอยหลัง |
| `j` / `l` | หมุนซ้าย / ขวา |
| `k` | หยุด |
| `q` / `z` | เพิ่ม / ลด speed |

ขับวนรอบห้องจนแผนที่ครบ ดูใน RViz (Fixed Frame: `map`)

---

## Step 11 — Save Map

```bash
mkdir -p ~/maps
ros2 run nav2_map_server map_saver_cli -f ~/maps/my_room
# ได้: my_room.pgm + my_room.yaml
```

---

## ตรวจสอบระบบ

```bash
ros2 topic list          # ต้องเห็น /scan /odom /cmd_vel /tf /map
ros2 topic hz /scan      # ~10 Hz
ros2 topic hz /odom      # ~20 Hz
ros2 run tf2_tools view_frames   # export TF graph
```

---

## Troubleshooting

### USB port ไม่ถูก (symlink ไม่ขึ้น)

> เกิดเมื่อ Pi5 มี USB path แตกต่างจาก default (`7-2.2`, `7-2.4`) ในสคริปต์

**1. หา USB path จริงบน Pi5:**
```bash
for f in /sys/class/tty/ttyUSB*; do
  echo "$f → $(readlink -f $f/../../../)"
done
# เช่น: /sys/class/tty/ttyUSB0 → .../2-1
#        /sys/class/tty/ttyUSB1 → .../4-1
```

**2. หาว่า path ไหนคือ ESP32 ไหนคือ LiDAR:**
```bash
# ถอด USB สาย ESP32 ออก → ดูว่า ttyUSBx ไหนหาย
ls /dev/ttyUSB*
# เสียบคืน แล้วถอด LiDAR → ดูอีกที
```

**3. แก้ udev rule ตรงๆ:**
```bash
sudo nano /etc/udev/rules.d/99-amr-usb.rules
```
แก้ path ให้ตรง (ตัวอย่าง Pi5: ESP32=2-1, LiDAR=4-1):
```
SUBSYSTEM=="tty", DEVPATH=="*2-1*", SYMLINK+="esp32", GROUP="dialout", MODE="0666"
SUBSYSTEM=="tty", DEVPATH=="*4-1*", SYMLINK+="lidar", GROUP="dialout", MODE="0666"
```

**4. Reload แล้วตรวจสอบ:**
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
# ถอดเสียบ USB ใหม่
ls -la /dev/esp32 /dev/lidar
# ต้องเห็น: /dev/esp32 -> ttyUSBx และ /dev/lidar -> ttyUSBy
```

### LiDAR เชื่อมไม่ได้

```bash
# ทดสอบตรงๆ
ros2 run ydlidar_ros2_driver ydlidar_ros2_driver_node \
  --ros-args --params-file \
  ~/amr/ros2_ws/src/ydlidar_ros2_driver/params/X3Pro.yaml
# ดู docs/ydlidar_x3pro_setup.md สำหรับ error แต่ละแบบ
```

### Motor ไม่หมุน

```bash
# ส่งคำสั่งตรงๆ ข้าม ROS2
echo '{"l":0.1,"r":0.1}' > /dev/esp32
# แล้วดู response
cat /dev/esp32
```

### SLAM ไม่สร้าง map — QoS Mismatch

> **อาการ:** `/map` ไม่โผล่ใน `ros2 topic list`, warn: `requesting incompatible QoS... RELIABILITY_QOS_POLICY`

**สาเหตุ:** YDLiDAR publish `/scan` แบบ `BEST_EFFORT` แต่ slam_toolbox subscribe แบบ `RELIABLE` → ไม่รับ scan เลย

**แก้:** ใช้ `scan_qos_bridge` node (มีอยู่แล้วใน slam_launch.py) ที่แปลง QoS ให้อัตโนมัติ  
ตรวจว่า node รันอยู่:
```bash
ros2 node list | grep bridge
# ต้องเห็น /scan_qos_bridge
```

---

### SLAM ไม่สร้าง map — Lifecycle Not Activated

> **อาการ:** `/map` ไม่โผล่, `ros2 node info /slam_toolbox | grep Subscribers` เห็นแค่ `/parameter_events`

**สาเหตุ:** slam_toolbox เป็น lifecycle node ที่ไม่ถูก activate → ไม่เคย subscribe `/scan` เลย

**แก้ Option 1** (ถาวร — ทำใน slam_launch.py แล้ว):
```python
parameters=[slam_params, {
    'use_sim_time': False,
    'use_lifecycle_manager': False,  # auto-activate
}]
```

**แก้ Option 2** (manual ชั่วคราว):
```bash
ros2 lifecycle set /slam_toolbox configure
ros2 lifecycle set /slam_toolbox activate
```

หลังแก้แล้ว `/map` จะโผล่ทันทีที่หุ่นเคลื่อนที่ครับ


### Rebuild หลัง git pull

```bash
cd ~/amr/ros2_ws
colcon build --packages-select amr_base --symlink-install
source install/setup.bash
```

---

## Git Pull อัปเดต

```bash
cd ~/amr
git pull
cd ros2_ws
colcon build --packages-select amr_base --symlink-install
source install/setup.bash

---

## 💻 Remote Ubuntu Machine (RViz + Teleop)

> ใช้เมื่อ dev machine มี WiFi ดีกว่า Pi5 หรือต้องการดู map บนจอใหญ่

### ต้องมีก่อน
- Ubuntu 24.04 + ROS2 Jazzy ติดตั้งแล้ว
- อยู่ WiFi เดียวกับ Pi5

### Step 1 — ติดตั้ง packages ที่จำเป็น

```bash
sudo apt update
sudo apt install -y \
  ros-jazzy-slam-toolbox \
  ros-jazzy-robot-state-publisher \
  ros-jazzy-teleop-twist-keyboard \
  ros-jazzy-rviz2
```

### Step 2 — Clone repo (แค่เพื่อได้ RViz config)

```bash
git clone https://github.com/tachin-r/for_my_first_AMR.git ~/amr
source /opt/ros/jazzy/setup.bash
cd ~/amr/ros2_ws
colcon build --packages-select amr_base --symlink-install
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
echo 'source ~/amr/ros2_ws/install/setup.bash' >> ~/.bashrc
source ~/.bashrc
```

### Step 3 — ตั้ง ROS_DOMAIN_ID ให้ตรงกับ Pi5

```bash
# ทั้งสองเครื่องต้องใช้ค่าเดียวกัน (default = 0)
echo 'export ROS_DOMAIN_ID=0' >> ~/.bashrc
source ~/.bashrc
```

### Step 4 — เปิด RViz ดู map

```bash
rviz2 -d ~/amr/ros2_ws/src/amr_base/rviz/slam.rviz
```

> ⚠️ ถ้า map ไม่ขึ้น → เปลี่ยน **Fixed Frame** จาก `map` เป็น `odom` ก่อน  
> แล้วค่อยเปลี่ยนกลับเมื่อ SLAM เริ่ม publish map

### Step 5 — ควบคุมหุ่น (Terminal ใหม่)

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

### ตรวจสอบว่าเห็น Pi5 topics

```bash
ros2 topic list
# ต้องเห็น /scan /odom /map /cmd_vel /tf
# ถ้าไม่เห็น → เช็คว่า Pi5 รัน launch อยู่ และ ROS_DOMAIN_ID ตรงกัน
```

### ถ้า topics ไม่ cross เครื่อง

```bash
# ลอง ping Pi5 ก่อน
ping <Pi5_IP>

# ถ้า ping ได้แต่ topics ไม่เห็น → ใช้ CycloneDDS (ดีกว่าบน WiFi)
sudo apt install -y ros-jazzy-rmw-cyclonedds-cpp
echo 'export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp' >> ~/.bashrc
source ~/.bashrc
# ตั้งทั้งสองเครื่อง!
```

### สรุป workflow

```
Pi5:          ros2 launch amr_base slam_launch.py launch_rviz:=false
Ubuntu dev:   rviz2 -d ~/amr/ros2_ws/src/amr_base/rviz/slam.rviz
Ubuntu dev:   ros2 run teleop_twist_keyboard teleop_twist_keyboard
```
```
