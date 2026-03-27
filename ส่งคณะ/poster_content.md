# เนื้อหาสำหรับ Poster — AMR (Autonomous Mobile Robot)
# ใช้ copy ไปวางใน template PPTX ของคณะ (KMITL School of Engineering)

---

## ชื่อโปรเจค / Title
**DIY Autonomous Mobile Robot using ROS2 and LiDAR-based Navigation**
(หุ่นยนต์เคลื่อนที่อัตโนมัติด้วย ROS2 และ LiDAR)

---

## Background

Autonomous Mobile Robots (AMRs) are increasingly used in logistics, healthcare, and exploration.
Unlike AGVs that follow fixed paths, AMRs can build maps, plan routes, and avoid obstacles autonomously.
However, commercial AMR platforms are expensive and difficult to customize.

This project develops a low-cost, fully DIY AMR from scratch using open-source software (ROS2)
and affordable hardware (Raspberry Pi 5, ESP32, YDLiDAR X3 Pro) to study the complete
robotics stack — from low-level motor control to autonomous navigation.

---

## Objective

1. Design and build a Differential Drive mobile robot with accurate motor control
2. Implement SLAM (Simultaneous Localization and Mapping) for 2D map building using LiDAR
3. Develop autonomous navigation with path planning and obstacle avoidance
4. Apply ROS2 Jazzy as the robotics middleware framework

---

## Methodology

### System Architecture
- **ESP32** (Low-Level): PID velocity control at 20Hz, quadrature encoder reading, motor PWM via L298N
- **Raspberry Pi 5** (High-Level): ROS2 Jazzy, LiDAR processing, SLAM, Nav2 navigation
- **Communication**: USB Serial with JSON protocol at 115200 baud

### Hardware
| Component | Specification |
|-----------|--------------|
| Computer | Raspberry Pi 5 (Ubuntu 24.04) |
| MCU | ESP32 DevKit |
| LiDAR | YDLiDAR X3 Pro (720 pts/scan, 10Hz) |
| Motors | DC Motor ×2 + Quadrature Encoder (506 PPR) |
| Driver | L298N Dual H-Bridge |
| Wheels | Ø65mm ×2 + Caster, Wheelbase 200mm |
| Chassis | DIY 16×16 cm |

### Software Stack
| Layer | Technology |
|-------|-----------|
| OS + Middleware | Ubuntu 24.04 + ROS2 Jazzy |
| SLAM | slam_toolbox (Online Async) |
| Navigation | Nav2 (RegulatedPurePursuit) |
| Localization | slam_toolbox (Scan Matching) |
| Path Planning | NavfnPlanner (Dijkstra) |
| Motor Control | PID on ESP32 (Kp=400, Ki=50, Kd=2) |

**📷 [ใส่รูป: ภาพ System Architecture / Block Diagram]**
**📷 [ใส่รูป: ภาพหุ่นยนต์ AMR ทั้งคัน]**

---

## Data Collection

1. **Encoder Data** — Quadrature encoder ×2 (1012 counts/rev, x2 counting)
   → ใช้คำนวณ Dead-Reckoning Odometry (position x, y, θ)
2. **LiDAR Scan Data** — YDLiDAR X3 Pro (720 points/scan, 10Hz, range 0.1–8m)
   → ใช้สร้างแผนที่ (SLAM) และหลบสิ่งกีดขวาง (Costmap)
3. **PID Response** — Target vs Actual velocity (logged at 20Hz)
   → ใช้ปรับค่า Kp, Ki, Kd ให้เหมาะสม

**📷 [ใส่รูป: กราฟ PID Response — ใช้ไฟล์ pid_response_graph.png ที่ gen จาก Colab]**

---

## Data Analysis

### PID Tuning
- เริ่มจาก Kp=80 → มอเตอร์ตอบสนองช้า, steady-state error สูง
- ปรับเป็น Kp=400, Ki=50, Kd=2 → response เร็ว, error < 5%
- เพิ่ม Dead-Zone Kickstart (MIN_PWM=120) → เอาชนะ static friction ทันที

### SLAM Quality
- ใช้ slam_toolbox (Online Async) → สร้างแผนที่ห้องได้สำเร็จ
- Loop Closure ทำงาน → แผนที่ไม่ drift เมื่อเดินวนรอบ
- แก้ QoS Mismatch (BEST_EFFORT→RELIABLE) ด้วย scan_qos_bridge node

### Navigation Performance
- RegulatedPurePursuit Controller → เส้นทาง smooth, ไม่ oscillate
- หลบสิ่งกีดขวางได้ → replan อัตโนมัติเมื่อเจอสิ่งกีดขวางใหม่
- Recovery behaviors (spin, backup) → กู้คืนเมื่อติด

---

## Results

| Test | Result |
|------|--------|
| Motor PID Control (20Hz) | ✅ Steady-state error < 5% |
| Encoder Odometry (~20Hz) | ✅ Accurate short-distance |
| LiDAR Scan (10Hz) | ✅ 720 points/scan |
| SLAM Map Building | ✅ Complete room map |
| Loop Closure | ✅ No drift on loop |
| Autonomous Navigation | ✅ Goal reached |
| Obstacle Avoidance | ✅ Dynamic replanning |
| Recovery Behavior | ✅ Spin/BackUp works |

**📷 [ใส่รูป: แผนที่ที่สร้างจาก SLAM (screenshot RViz)]**
**📷 [ใส่รูป: Nav2 navigation path ใน RViz — เส้นสีเขียว + costmap]**

---

## Conclusion

- สร้าง AMR จากศูนย์ได้สำเร็จ ด้วยต้นทุนต่ำ ใช้ open-source ทั้งหมด
- ระบบ SLAM สร้างแผนที่ 2D ได้แม่นยำ ด้วย LiDAR + slam_toolbox
- ระบบ Nav2 นำทางอัตโนมัติ วางแผนเส้นทาง + หลบสิ่งกีดขวาง ได้จริง
- PID Controller บน ESP32 ควบคุมความเร็วมอเตอร์ได้ดี ที่ 20Hz
- ข้อจำกัด: Odometry drift ในระยะไกล → ใช้ LiDAR-based localization ชดเชย

### Future Work
- เพิ่ม IMU + EKF เพื่อลด odometry drift
- เพิ่ม Depth Camera สำหรับ 3D obstacle detection
- พัฒนา Web Interface สำหรับสั่งงานระยะไกล

---

## Acknowledgement

ขอขอบคุณคณะวิศวกรรมศาสตร์ สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง (KMITL)
ที่สนับสนุนโปรเจคนี้ และขอขอบคุณชุมชน Open Source ของ ROS2, Nav2, slam_toolbox
และ YDLiDAR ที่ทำให้โปรเจคนี้เป็นไปได้

---

## References

1. ROS2 Jazzy Documentation — https://docs.ros.org/en/jazzy/
2. Nav2 Documentation — https://navigation.ros.org/
3. slam_toolbox — https://github.com/SteveMacenski/slam_toolbox
4. YDLiDAR SDK — https://github.com/YDLIDAR/
5. PlatformIO — https://platformio.org/
6. Siegwart, R. et al. "Introduction to Autonomous Mobile Robots." MIT Press, 2011.
