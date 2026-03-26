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
| Wheel | Ø65mm drive wheels + caster |
| Chassis | DIY 16x16cm frame |

### Software Stack
| Layer | เทคโนโลยี |
|-------|----------|
| OS | Ubuntu 24.04 + ROS2 Jazzy |
| SLAM | slam_toolbox (Online Async) |
| Navigation | Nav2 (RegulatedPurePursuit) |
| Localization | AMCL |
| Motor Control | ESP32 PID Controller |

---

## 🗺️ ขั้นตอนที่ 1: สร้างแผนที่ (SLAM)

### 1.1 เตรียมเครื่อง Pi5

```bash
# SSH เข้า Pi5
ssh khaitapad@<PI5_IP>

# รันหุ่น (SLAM mode)
cd ~/amr/ros2_ws
source install/setup.bash
ros2 launch amr_base nav2_launch.py
```

> **หมายเหตุ:** ถ้าไม่ระบุ `map:=` จะเข้าโหมด SLAM อัตโนมัติ

### 1.2 เปิด RViz บน Dev Machine

```bash
# Terminal 1: RViz + Teleop
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

**เคล็ดลับ:** ขับช้าๆ ให้ LiDAR scan ซ้อนทับกัน → แผนที่จะชัดขึ้น

### 1.4 บันทึกแผนที่

```bash
# Terminal ใหม่บน Pi5
cd ~/maps
ros2 run nav2_map_server map_saver_cli -f my_room
```

ได้ไฟล์ 2 ไฟล์:
- `my_room.pgm` — ภาพแผนที่ (grayscale)
- `my_room.yaml` — metadata (resolution, origin)

---

## 🧭 ขั้นตอนที่ 2: นำทางอัตโนมัติ (Nav2)

### 2.1 รัน Nav2 บน Pi5

```bash
ros2 launch amr_base nav2_launch.py map:=/home/khaitapad/maps/my_room.yaml
```

### 2.2 เปิด RViz (Nav2 mode)

```bash
# Dev Machine
ros2 launch amr_base dev_launch.py mode:=nav2
```

### 2.3 ตั้งตำแหน่งเริ่มต้น

> **หมายเหตุ:** AMCL ตั้ง initial pose ที่ origin อัตโนมัติแล้ว
> ถ้าตำแหน่งไม่ตรง ให้กด **2D Pose Estimate** ใน RViz แล้วคลิกจุดที่หุ่นอยู่จริง

### 2.4 ส่งเป้าหมาย (Goal)

**วิธีที่ 1 — RViz (GUI):**
1. กด **2D Goal Pose** ใน toolbar
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

### ตรวจสอบ Localization
```bash
ros2 topic echo /amcl_pose --once
# ต้องเห็น position ของหุ่น
```

### Clear Costmap (ถ้าติด)
```bash
ros2 service call /clear_all_costmaps nav2_msgs/srv/ClearEntireCostmap '{}'
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
│   ├── my_room.pgm
│   └── my_room.yaml
└── docs/                     # Documentation
    ├── demo_guide.md          # ← คู่มือนี้
    ├── pi5_setup_guide.md     # การติดตั้ง Pi5
    ├── ydlidar_x3pro_setup.md # การตั้งค่า LiDAR
    └── operation_guide.md     # คู่มือใช้งาน
```

---

## 🎯 Algorithm ที่ใช้

| ส่วน | Algorithm | เหตุผล |
|------|-----------|--------|
| SLAM | **slam_toolbox** (Online Async) | เบา, เหมาะกับ Pi5, แม่นยำ |
| Localization | **AMCL** (Adaptive MCL) | Particle filter มาตรฐาน, ใช้ LiDAR scan matching |
| Path Planning | **NavfnPlanner** (Dijkstra) | วางแผนเส้นทาง global |
| Path Following | **RegulatedPurePursuit** | วิ่งตามเส้นทาง smooth, ลด oscillation |
| Motor Control | **PID** (on ESP32) | ควบคุมความเร็วล้อ, 20Hz loop |

---

## 📹 การสาธิต (Demo Flow)

### สาธิต SLAM (3-5 นาที)
1. เปิดหุ่น + RViz
2. ขับสำรวจห้องด้วย teleop
3. แสดงแผนที่ที่สร้างเสร็จใน RViz
4. บันทึกแผนที่ด้วย `map_saver_cli`

### สาธิต Navigation (3-5 นาที)
1. โหลดแผนที่ที่บันทึกไว้
2. แสดง costmap + robot pose ใน RViz
3. กด 2D Goal Pose → หุ่นวางแผนและวิ่งไปเอง
4. แสดง path planning (เส้นสีเขียว) + obstacle avoidance
