# AMR Stack — Architecture & Code Reference

> คู่มือนี้อธิบาย code ที่เขียนทั้งหมด เพื่อใช้ deploy บน Raspberry Pi 5

---

## ภาพรวมระบบ

```
┌─────────────────────────────────────────────────────┐
│                  Raspberry Pi 5                     │
│                                                     │
│  ┌─────────────┐    ┌──────────────────────────┐    │
│  │ YDLiDAR     │    │  ROS2 Jazzy              │    │
│  │ Driver Node │    │                          │    │
│  │ /scan topic │    │  esp32_bridge.py         │    │
│  └──────┬──────┘    │  ├─ sub: /cmd_vel        │    │
│         │           │  ├─ pub: /odom           │    │
│  USB    │           │  └─ broadcast: TF        │    │
│ ttyUSB1 │           └──────────┬───────────────┘    │
│         │                      │ USB ttyUSB0        │
└─────────┼──────────────────────┼────────────────────┘
          │                      │
    ┌─────▼──────┐        ┌──────▼───────────────────┐
    │ YD-LiDAR   │        │       ESP32              │
    │  X3 Pro    │        │                          │
    │ 720 pts/   │        │  ┌─────────────────────┐ │
    │ scan 10Hz  │        │  │ Motor Control (PWM) │ │
    └────────────┘        │  │ L298N → 2x Motors   │ │
                          │  ├─────────────────────┤ │
                          │  │ Encoder ISR (x2)    │ │
                          │  │ 1012 counts/rev     │ │
                          │  ├─────────────────────┤ │
                          │  │ PID Velocity Ctrl   │ │
                          │  │ 20Hz control loop   │ │
                          │  └─────────────────────┘ │
                          └──────────────────────────┘
```

---

## 1. ESP32 Firmware (`esp32_firmware/src/main.cpp`)

### Hardware Pinout

| Function | GPIO |
|---|---|
| Motor A PWM (ENA) | 14 |
| Motor A DIR 1 (IN1) | 26 |
| Motor A DIR 2 (IN2) | 27 |
| Motor B PWM (ENB) | 21 |
| Motor B DIR 1 (IN3) | 22 |
| Motor B DIR 2 (IN4) | 23 |
| Encoder A Phase A (INT) | 32 |
| Encoder A Phase B (DIR) | 33 |
| Encoder B Phase A (INT) | 19 |
| Encoder B Phase B (DIR) | 18 |

### Robot Physical Specs

```cpp
WHEEL_DIAMETER_M   = 0.065f    // 65mm
WHEEL_CIRCUMFERENCE = π × 0.065 = 0.2042m
ENCODER_PPR        = 506       // pulses per wheel-rev (Phase A edge)
ENCODER_CPR        = 1012      // x2 (CHANGE interrupt = both edges)
DIST_PER_COUNT     = 0.2042 / 1012 ≈ 0.000202 m/count
WHEELBASE_M        = 0.200f    // 200mm
```

### Serial Protocol (115200 baud)

**Pi5 → ESP32** (คำสั่ง):
```json
{"l": 0.10, "r": 0.10}
```
- `l` = left wheel velocity (m/s)
- `r` = right wheel velocity (m/s)
- ส่งอย่างน้อย 1 ครั้งต่อ 500ms ไม่งั้นหยุดอัตโนมัติ (safety timeout)

**ESP32 → Pi5** (odometry ทุก 50ms):
```json
{"lt": 12048, "rt": 11932, "lv": 0.0991, "rv": 0.0988, "dt": 50}
```
- `lt` / `rt` = cumulative encoder ticks (ซ้าย / ขวา)
- `lv` / `rv` = current velocity m/s
- `dt` = actual loop time ms

**Runtime PID tuning (ไม่ต้อง flash ใหม่)**:
```json
{"pid_kp": 400, "pid_ki": 50, "pid_kd": 2}
```

**Reset encoder counts**:
```json
{"reset": 1}
```

### PID Controller

```
KP = 400   (proportional — response เร็ว)
KI = 50    (integral — compensate steady-state error)
KD = 2     (derivative — ลด overshoot)
MIN_START_PWM = 65  (kickstart ผ่าน motor dead-zone)
MAX_PWM = 230
Loop rate: 20Hz (50ms)
```

**ลำดับการทำงาน:**
1. รอรับ JSON จาก Serial
2. Safety timeout 500ms → หยุด target velocity
3. **ทุก 50ms**: อ่าน encoder → คำนวณ velocity → PID → analogWrite → ส่ง JSON odometry

---

## 2. ROS2 Bridge Node (`ros2_ws/src/amr_base/amr_base/esp32_bridge.py`)

### หน้าที่

| Input | → | Output |
|---|---|---|
| `/cmd_vel` (Twist) | diff-drive kinematics | Serial JSON ไป ESP32 |
| Serial JSON จาก ESP32 | dead-reckoning | `/odom` (Odometry) |
| encoder ticks | TF transform | `odom → base_link` |

### Diff-Drive Kinematics (cmd_vel → wheel velocities)

```python
v_left  = linear.x - (angular.z × wheelbase / 2)
v_right = linear.x + (angular.z × wheelbase / 2)
# แปลงเป็น JSON ส่ง ESP32
```

### Dead-Reckoning Odometry (encoder → position)

```python
d_left   = delta_ticks_left  × DIST_PER_COUNT
d_right  = delta_ticks_right × DIST_PER_COUNT
d_center = (d_left + d_right) / 2
d_theta  = (d_right - d_left) / WHEELBASE

x     += d_center × cos(theta)
y     += d_center × sin(theta)
theta += d_theta
```

### ROS2 Topics & Params

| Topic | Type | หน้าที่ |
|---|---|---|
| `/cmd_vel` (sub) | geometry_msgs/Twist | รับคำสั่งความเร็ว |
| `/odom` (pub) | nav_msgs/Odometry | ส่ง dead-reckoning position |
| `/tf` (broadcast) | TF | odom → base_link transform |

| Parameter | Default | หน้าที่ |
|---|---|---|
| `esp32_port` | `/dev/esp32` | Serial port |
| `esp32_baud` | `115200` | Baud rate |
| `wheel_diameter` | `0.065` | เส้นผ่านศูนย์กลางล้อ (m) |
| `wheelbase` | `0.200` | ระยะห่างล้อ (m) |
| `encoder_ppr` | `506` | Pulses per revolution |

---

## 3. Deploy บน Raspberry Pi 5

### ขั้นตอน (ทำครั้งเดียว)

```bash
# 1. Copy project ไป Pi5
rsync -avz /home/tachin/for_my_first_AMR/ pi@<PI5_IP>:~/amr/

# 2. SSH เข้า Pi5
ssh pi@<PI5_IP>

# 3. ติดตั้ง YDLidar-SDK (ดู docs/ydlidar_x3pro_setup.md)
cd /tmp && git clone --depth 1 https://github.com/YDLIDAR/YDLidar-SDK.git
cd YDLidar-SDK && mkdir build && cd build
cmake .. && make -j4 && sudo make install && sudo ldconfig

# 4. Lock USB ports
sudo bash ~/amr/scripts/setup_udev.sh
# แล้วถอดเสียบ USB ใหม่

# 5. Build workspace
source /opt/ros/jazzy/setup.bash
cd ~/amr/ros2_ws
colcon build --symlink-install

# 6. Source อัตโนมัติ
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
echo 'source ~/amr/ros2_ws/install/setup.bash' >> ~/.bashrc
source ~/.bashrc
```

### รัน Stack ทั้งหมด

```bash
# รัน LiDAR + ESP32 Bridge พร้อมกัน
ros2 launch amr_base amr_launch.py
```

### ตรวจสอบว่าทำงานถูกต้อง

```bash
# Terminal 2: ดู topics
ros2 topic list
# ต้องเห็น: /scan, /odom, /cmd_vel, /tf

# ดู scan data
ros2 topic hz /scan      # ต้องได้ ~10 Hz

# ดู odometry
ros2 topic hz /odom      # ต้องได้ ~20 Hz

# ทดสอบขับ
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.1}, angular: {z: 0.0}}" --rate 10
```

---

## 4. โครงสร้างไฟล์

```
for_my_first_AMR/
├── docs/
│   ├── ydlidar_x3pro_setup.md     ← setup guide + troubleshooting
│   └── amr_stack_reference.md     ← ไฟล์นี้
├── esp32_firmware/
│   ├── platformio.ini
│   └── src/main.cpp               ← PID motor controller
├── scripts/
│   └── setup_udev.sh              ← lock USB ports
├── ros2_ws/src/amr_base/
│   ├── amr_base/esp32_bridge.py  ← ROS2 serial bridge
│   ├── config/amr_config.yaml    ← robot parameters
│   ├── launch/amr_launch.py      ← launch LiDAR + bridge
│   ├── params/X3Pro.yaml         ← LiDAR params (confirmed)
│   └── setup.cfg                 ← บอก colcon install path ถูกต้อง
└── docker/                       ← alternative: Docker deployment
```
