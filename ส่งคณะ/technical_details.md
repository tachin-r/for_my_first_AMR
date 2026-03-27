# Technical Details Summary — DIY AMR Robot

---

## 1. Hardware Stack

### 1.1 Computing
| Component | Spec |
|-----------|------|
| **Main Computer** | Raspberry Pi 5 |
| **OS** | Ubuntu 24.04 (64-bit) |
| **Microcontroller** | ESP32 DevKit 38-pin |
| **Communication** | USB Serial (JSON, 115200 baud) |

### 1.2 Sensors
| Component | Spec |
|-----------|------|
| **LiDAR** | YDLiDAR X3 Pro (Model: S2PRO) |
| → Sample Rate | 4,000 Hz |
| → Points/Scan | 720 points |
| → Scan Rate | 10 Hz |
| → Range | 0.1 – 8.0 m |
| **Encoders** | Quadrature Encoder × 2 |
| → PPR | 506 (Phase A rising edge) |
| → CPR (x2 counting) | 1,012 counts/rev |
| → Gear Ratio | 1:46 |

### 1.3 Actuators
| Component | Spec |
|-----------|------|
| **Motor Driver** | L298N Dual H-Bridge |
| **Motors** | DC Motor × 2 |
| **Drive Type** | Differential Drive |
| **Wheels** | Ø65 mm × 2 (drive) + 1 caster (front) |
| **Wheelbase** | 200 mm (center-to-center) |
| **Chassis** | DIY frame 16 × 16 cm |

### 1.4 ESP32 GPIO Pinout
| Function | GPIO Pin |
|----------|----------|
| Motor A PWM (ENA) | 14 |
| Motor A DIR (IN1/IN2) | 26, 27 |
| Motor B PWM (ENB) | 21 |
| Motor B DIR (IN3/IN4) | 22, 23 |
| Encoder A (Phase A / Phase B) | 32, 33 |
| Encoder B (Phase A / Phase B) | 19, 18 |

---

## 2. Software Stack

### 2.1 ROS2 Ecosystem
| Layer | Technology | Version |
|-------|-----------|---------|
| Middleware | ROS2 | Jazzy LTS (→ May 2029) |
| SLAM | slam_toolbox | Online Async mode |
| Navigation | Nav2 | Full stack |
| LiDAR Driver | ydlidar_ros2_driver | humble branch |
| Robot Model | URDF | amr.urdf.xml |

### 2.2 ESP32 Firmware
| Item | Detail |
|------|--------|
| Framework | Arduino (via PlatformIO) |
| Language | C++ |
| JSON Library | ArduinoJson |
| Control Loop | PID @ 20 Hz (50 ms) |
| PWM Method | `analogWrite()` (8-bit, 0–255) |

### 2.3 Custom ROS2 Nodes (amr_base package)
| Node | File | หน้าที่ |
|------|------|---------|
| esp32_bridge | `esp32_bridge.py` | cmd_vel ↔ ESP32 Serial, Odometry, TF broadcast |
| scan_qos_bridge | `scan_qos_bridge.py` | แปลง LiDAR QoS: BEST_EFFORT → RELIABLE |
| goal_relay | `goal_relay.py` | RViz 2D Goal Pose → Nav2 NavigateToPose action |

### 2.4 ROS2 Topic/TF Map
```
Topics:
  /cmd_vel          ← Twist         (teleop / Nav2 → bridge)
  /odom             ← Odometry      (bridge → Nav2)
  /scan             ← LaserScan     (LiDAR driver, BEST_EFFORT)
  /scan_reliable    ← LaserScan     (QoS bridge, RELIABLE)
  /map              ← OccupancyGrid (slam_toolbox)

TF Tree:
  map → odom → base_link → base_laser
  (slam)  (bridge)  (robot_state_publisher)
```

---

## 3. Algorithm Summary

### 3.1 Motor Control (ESP32)
| Item | Value |
|------|-------|
| **Algorithm** | PID Velocity Control |
| **Loop Rate** | 20 Hz (50 ms) |
| **Kp / Ki / Kd** | 400 / 50 / 2 |
| **MAX_PWM** | 250 |
| **MIN_START_PWM** | 120 (dead-zone kickstart) |
| **Safety Timeout** | 500 ms (auto-stop) |
| **Anti-Windup** | Integral limit = 200/Ki |
| **Encoder Resolution** | 0.2018 mm/count |

### 3.2 Odometry (ROS2 Bridge)
| Item | Value |
|------|-------|
| **Algorithm** | Dead-Reckoning (encoder-based) |
| **Update Rate** | ~20 Hz |
| **Distance/Count** | π × 0.065 / 1012 ≈ 0.000202 m |
| **Output** | /odom + TF (odom → base_link) |

### 3.3 SLAM
| Item | Value |
|------|-------|
| **Package** | slam_toolbox |
| **Mode** | Online Asynchronous |
| **Input** | /scan_reliable (RELIABLE QoS) |
| **Output** | /map (OccupancyGrid) + TF (map → odom) |
| **Map Format** | .pgm/.yaml (costmap) + .posegraph/.data (localization) |
| **เหตุผลที่เลือก** | เบา, เหมาะกับ Pi5, แม่นยำ, รองรับ serialized map |

### 3.4 Localization
| Item | Value |
|------|-------|
| **Package** | slam_toolbox (Localization mode) |
| **Algorithm** | LiDAR Scan Matching |
| **Input** | /scan_reliable + serialized map |
| **เหตุผลที่เลือก** | ใช้ LiDAR เป็นหลัก — แม่นกว่า AMCL สำหรับหุ่นเล็ก |

### 3.5 Path Planning
| Item | Value |
|------|-------|
| **Plugin** | NavfnPlanner |
| **Algorithm** | Dijkstra |
| **Tolerance** | 0.5 m |
| **Allow Unknown** | true |

### 3.6 Path Following (Controller)
| Item | Value |
|------|-------|
| **Plugin** | RegulatedPurePursuitController |
| **Max Linear Vel** | 1.0 m/s |
| **Lookahead** | 0.3 – 0.9 m |
| **Rotate-to-Heading** | 2.3 rad/s |
| **Allow Reversing** | true |
| **Controller Freq** | 10 Hz |
| **เหตุผลที่เลือก** | Smooth path following, ลด oscillation |

### 3.7 Costmaps
| Costmap | Size | Resolution | Update Rate |
|---------|------|-----------|-------------|
| Local | 3×3 m (rolling) | 0.05 m | 5 Hz |
| Global | Full map | 0.05 m | 1 Hz |
| Robot Radius | 0.10 m | — | — |
| Inflation Radius | 0.15 m | — | — |

### 3.8 Recovery Behaviors
| Behavior | Plugin |
|----------|--------|
| Spin | nav2_behaviors::Spin |
| BackUp | nav2_behaviors::BackUp |
| DriveOnHeading | nav2_behaviors::DriveOnHeading |
| Wait | nav2_behaviors::Wait |

---

## 4. Communication Protocol

### 4.1 Pi5 → ESP32 (Command)
```json
{"l": 0.10, "r": 0.10}       ← wheel velocity (m/s)
{"pid_kp": 400, "pid_ki": 50} ← runtime PID tuning
{"reset": 1}                   ← reset encoder counts
```

### 4.2 ESP32 → Pi5 (Odometry, every 50ms)
```json
{"lt": 12048, "rt": 11932, "lv": 0.0991, "rv": 0.0988, "dt": 50}
```
| Field | Meaning |
|-------|---------|
| lt/rt | Cumulative encoder ticks (left/right) |
| lv/rv | Current velocity (m/s) |
| dt | Actual loop time (ms) |

---

## 5. Development Tools

| Tool | Purpose |
|------|---------|
| **PlatformIO** | ESP32 firmware build & upload |
| **colcon** | ROS2 workspace build system |
| **RViz2** | 3D visualization (map, path, TF, scan) |
| **teleop_twist_keyboard** | Manual robot control via keyboard |
| **Git/GitHub** | Version control |

---

## 6. USB Device Management

ใช้ **udev rules** เพื่อ lock USB port ตาม physical path:
```
/dev/esp32  → ESP32 (via ttyUSBx)
/dev/lidar  → YDLiDAR X3 Pro (via ttyUSBy)
```
เหตุผล: ทั้ง ESP32 และ LiDAR ใช้ CP210x ที่ Serial Number เหมือนกัน จึงไม่สามารถแยกด้วย serial number ได้

---

## 7. Launch Modes

| Mode | Command | ใช้เมื่อ |
|------|---------|----------|
| **SLAM** | `ros2 launch amr_base slam_launch.py` | สร้างแผนที่ใหม่ |
| **Nav2** | `ros2 launch amr_base nav2_launch.py mode:=nav2` | นำทางอัตโนมัติ |
| **Base** | `ros2 launch amr_base amr_launch.py` | ทดสอบพื้นฐาน |
| **Dev (RViz)** | `ros2 launch amr_base dev_launch.py` | monitor จาก dev machine |
