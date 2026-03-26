# 🤖 DIY Autonomous Mobile Robot (AMR) — คู่มือสาธิต

## 📋 ภาพรวมโปรเจค

หุ่นยนต์ขับเคลื่อนอัตโนมัติ (AMR) สร้างเองจากศูนย์ ใช้ **ROS2 Jazzy** บน **Raspberry Pi 5** ร่วมกับ **ESP32** ควบคุมมอเตอร์

### สถาปัตยกรรม

```
┌──────────────┐    Serial/USB     ┌───────────────┐
│  ESP32       │ ◄──────────────►  │  Raspberry    │
│  Motor PID   │  JSON protocol    │  Pi 5 (Jazzy) │
│  Encoder     │                   │  Nav2 / SLAM  │
└──────────────┘                   │  LiDAR driver │
                                   └───────┬───────┘
                                    WiFi   │
                                   ┌───────▼───────┐
                                   │  Dev Machine  │
                                   │  RViz / Teleop│
                                   └───────────────┘
```

### Hardware
| ชิ้นส่วน | รายละเอียด |
|---------|-----------|
| Compute | Raspberry Pi 5, ESP32 DevKit |
| Motor | DC Motor x2 + L298N Driver |
| Encoder | Quadrature Encoder 506 PPR x2 |
| LiDAR | YDLiDAR X3 Pro |
| Wheel | Ø65mm drive wheels + caster (front) |
| Chassis | DIY 16x16cm frame |

### Software Stack
| Layer | เทคโนโลยี |
|-------|----------|
| OS | Ubuntu 24.04 + ROS2 Jazzy |
| SLAM | slam_toolbox (Online Async) |
| Navigation | Nav2 (RegulatedPurePursuit) |
| Localization | slam_toolbox (Scan Matching) |
| Motor Control | ESP32 PID Controller |

---

## 🗺️ ขั้นตอนที่ 1: สร้างแผนที่ (SLAM)

### 1.1 เตรียมเครื่อง Pi5

```bash
# SSH เข้า Pi5
ssh khaitapad@<PI5_IP>

# อัพเดทโค้ด (ถ้ามีการเปลี่ยนแปลง)
cd ~/amr && git pull
cd ros2_ws && colcon build --packages-select amr_base --symlink-install
source install/setup.bash

# รันหุ่น (SLAM mode — default)
ros2 launch amr_base nav2_launch.py
```

### 1.2 เปิด RViz บน Dev Machine

```bash
cd ~/for_my_first_AMR/ros2_ws
source install/setup.bash
ros2 launch amr_base dev_launch.py mode:=slam
```

### 1.3 ขับหุ่นสำรวจห้อง

ใช้ **Teleop Keyboard** (หน้าต่าง xterm ที่เปิดอัตโนมัติ):

| ปุ่ม | การทำงาน |
|------|---------|
| `i` | เดินหน้า |
| `,` | ถอยหลัง |
| `j` | เลี้ยวซ้าย |
| `l` | เลี้ยวขวา |
| `k` | หยุด |
| `q`/`z` | เพิ่ม/ลดความเร็ว |

**เคล็ดลับ:**
- ขับ **ช้าๆ** ให้ LiDAR scan ซ้อนทับกัน → แผนที่จะชัดขึ้น
- เดินตามผนังห้องเป็นวง → ได้ loop closure จะแม่นยำมาก
- ดู RViz: scan สีแดงต้อง **เกาะผนัง** map สีเทา

### 1.4 บันทึกแผนที่ (ต้องทั้ง 2 แบบ)

```bash
# Terminal ใหม่บน Pi5

# แบบ 1: Map ปกติ (สำหรับ costmap — .pgm/.yaml)
mkdir -p ~/maps
ros2 run nav2_map_server map_saver_cli -f ~/maps/my_room \
  --ros-args -p map_subscribe_transient_local:=true

# แบบ 2: Serialized Map (สำหรับ localization — .posegraph/.data)
ros2 service call /slam_toolbox/serialize_map \
  slam_toolbox/srv/SerializePoseGraph \
  "{filename: '/home/khaitapad/maps/my_room_serialized'}"
```

ได้ไฟล์ 4 ไฟล์:
- `my_room.pgm` + `my_room.yaml` — ภาพแผนที่สำหรับ costmap
- `my_room_serialized.posegraph` + `my_room_serialized.data` — สำหรับ localization

---

## 🧭 ขั้นตอนที่ 2: นำทางอัตโนมัติ (Nav2)

### 2.1 รัน Nav2 บน Pi5

```bash
# หยุด SLAM ก่อน (Ctrl+C)
# แล้วรัน Nav2 mode
ros2 launch amr_base nav2_launch.py mode:=nav2
```

> **หมายเหตุ:** Default map path = `~/maps/my_room.yaml` + `~/maps/my_room_serialized`
> ถ้า save ไว้ที่อื่น ระบุเอง:
> ```bash
> ros2 launch amr_base nav2_launch.py mode:=nav2 \
>   map:=/path/to/map.yaml \
>   serialized_map:=/path/to/serialized_map
> ```

### 2.2 เปิด RViz (Nav2 mode)

```bash
# Dev Machine
ros2 launch amr_base dev_launch.py mode:=nav2
```

### 2.3 ส่งเป้าหมาย (Goal)

**วิธีที่ 1 — RViz (GUI):**
1. กด **Nav2 Goal** หรือ **2D Goal Pose** ใน toolbar
2. คลิกจุดบน map ที่ต้องการ → ลากลูกศรบอกทิศ → ปล่อย
3. หุ่นจะวางแผนเส้นทาง (สีเขียว) แล้ววิ่งไปเอง

**วิธีที่ 2 — CLI:**
```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  '{pose: {header: {frame_id: "map"}, pose: {position: {x: 1.0, y: 0.5, z: 0.0}, orientation: {w: 1.0}}}}'
```

---

## 🔧 ขั้นตอนที่ 3: Debug & Monitor

### ตรวจสอบ TF Chain
```bash
ros2 run tf2_ros tf2_echo map base_link
# ต้องเห็นค่า Translation + Rotation
```

### ตรวจสอบ cmd_vel
```bash
ros2 topic echo /cmd_vel
# ต้องเห็นค่าเมื่อหุ่นเคลื่อนที่
```

### ตรวจสอบ Scan
```bash
ros2 topic hz /scan_reliable
# ต้องได้ ~10-12 Hz
```

### Clear Costmap (ถ้าติด)
```bash
ros2 service call /local_costmap/clear_entirely_local_costmap nav2_msgs/srv/ClearEntireCostmap '{}'
ros2 service call /global_costmap/clear_entirely_global_costmap nav2_msgs/srv/ClearEntireCostmap '{}'
```

---

## 📁 โครงสร้างโปรเจค

```
for_my_first_AMR/
├── esp32_firmware/           # ESP32 Motor Controller
│   └── src/main.cpp          # PID velocity control + encoder
├── ros2_ws/src/amr_base/     # ROS2 Package
│   ├── amr_base/
│   │   ├── esp32_bridge.py   # Serial bridge (cmd_vel ↔ ESP32)
│   │   ├── scan_qos_bridge.py # QoS adapter for LiDAR
│   │   └── goal_relay.py     # RViz goal → Nav2 action
│   ├── config/
│   │   └── nav2_params.yaml  # Nav2 configuration
│   ├── launch/
│   │   ├── nav2_launch.py    # Pi5 launch (SLAM/Nav2)
│   │   └── dev_launch.py     # Dev machine launch (RViz)
│   ├── urdf/
│   │   └── amr.urdf.xml      # Robot model
│   └── rviz/
│       ├── slam.rviz         # SLAM visualization
│       └── nav2.rviz         # Navigation visualization
├── maps/                     # Saved maps
│   ├── my_room.pgm / .yaml           # สำหรับ costmap
│   └── my_room_serialized.posegraph   # สำหรับ localization
└── docs/                     # Documentation
    ├── demo_guide.md          # ← คู่มือนี้
    ├── pi5_setup_guide.md     # การติดตั้ง Pi5
    └── operation_guide.md     # คู่มือใช้งาน
```

---

## 🎯 Algorithm ที่ใช้

| ส่วน | Algorithm | เหตุผล |
|------|-----------|--------|
| SLAM | **slam_toolbox** (Online Async) | เบา, เหมาะกับ Pi5, แม่นยำ |
| Localization | **slam_toolbox** (Scan Matching) | ใช้ LiDAR เป็นหลัก, แม่นกว่า AMCL สำหรับหุ่นเล็ก |
| Path Planning | **NavfnPlanner** (Dijkstra) | วางแผนเส้นทาง global |
| Path Following | **RegulatedPurePursuit** | วิ่งตามเส้นทาง smooth, ลด oscillation |
| Motor Control | **PID** (on ESP32) | ควบคุมความเร็วล้อ, 20Hz loop |

---

## 📹 การสาธิต (Demo Flow)

### สาธิต SLAM (3-5 นาที)
1. เปิดหุ่น + RViz (SLAM mode)
2. ขับสำรวจห้องด้วย teleop → ดู map สร้างขึ้นมาเรื่อยๆ
3. แสดงแผนที่ที่สร้างเสร็จใน RViz
4. บันทึกแผนที่ด้วย `map_saver_cli` + `serialize_map`

### สาธิต Navigation (3-5 นาที)
1. Switch เป็น Nav2 mode → โหลดแผนที่ที่บันทึกไว้
2. แสดง costmap + robot pose ใน RViz
3. กด **Nav2 Goal** → หุ่นวางแผนและวิ่งไปเอง
4. แสดง path planning (เส้นสีเขียว) + obstacle avoidance

---

## 🔄 อัพเดทหุ่น

```bash
# Pi5
cd ~/amr && git pull
cd ros2_ws && colcon build --packages-select amr_base --symlink-install
source install/setup.bash

# Dev Machine
cd ~/for_my_first_AMR && git pull
cd ros2_ws && colcon build --packages-select amr_base --symlink-install
source install/setup.bash
```

## 🔌 Upload Firmware (ถ้ามีแก้ ESP32)

```bash
cd ~/for_my_first_AMR/esp32_firmware
pio run --target upload
```