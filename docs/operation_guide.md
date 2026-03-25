# 🤖 AMR Operation Guide — วิธีใช้งานจริง

> **2 โหมด**: SLAM (สร้างแผนที่) และ Nav2 (นำทางอัตโนมัติ)  
> สีที่ใช้: 🍓 = รันบน Pi5 | 💻 = รันบน Dev Machine (Ubuntu)

---

## โหมด 1: SLAM — สร้างแผนที่ใหม่

ใช้เมื่อ: เข้าห้องใหม่ หรือแผนที่เก่าไม่ถูกต้อง

### 🍓 Pi5 — Terminal 1

```bash
source ~/amr/ros2_ws/install/setup.bash
ros2 launch amr_base slam_launch.py launch_rviz:=false
```

รอจนเห็น:
```
✅ ESP32 connected: /dev/esp32 @ 115200
✅ Scan QoS Bridge: /scan → /scan_reliable
Now lidar is scanning...
```

---

### 💻 Dev Machine — Terminal 1 (ดู Map)

```bash
source ~/for_my_first_AMR/ros2_ws/install/setup.bash
ros2 launch amr_base dev_launch.py
```

ใน **RViz**:
1. กด **Add** → **By topic** → `/map` → **Map** → OK
2. เปลี่ยน **Fixed Frame** เป็น `map`

---

### 💻 Dev Machine — Terminal 2 (ขับหุ่น)

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

> ⚠️ กด **`z`** ก่อน 2-3 ครั้ง เพื่อลด speed จาก 0.5 → 0.2 m/s  
> กด **`e`** 2 ครั้ง เพื่อเพิ่ม angular speed เป็น 2.0 (หมุนได้คล่อง)

| ปุ่ม | การเคลื่อนที่ |
|---|---|
| `i` | เดินหน้า |
| `,` | ถอยหลัง |
| `j` | หมุนซ้าย |
| `l` | หมุนขวา |
| `k` | **หยุด** |
| `e` / `c` | เพิ่ม/ลด angular speed |
| `w` / `x` | เพิ่ม/ลด linear speed |

ขับวนรอบห้องช้าๆ จนแผนที่ใน RViz สมบูรณ์

---

### 🍓 Pi5 — Save Map (ทำก่อนปิด SLAM)

```bash
# Terminal ใหม่บน Pi5
mkdir -p ~/maps
ros2 run nav2_map_server map_saver_cli -f ~/maps/my_room
```

ได้ไฟล์:
- `~/maps/my_room.pgm` — รูปแผนที่
- `~/maps/my_room.yaml` — metadata

---

## โหมด 2: Nav2 — นำทางอัตโนมัติ

> ✅ ต้องมี map สำเร็จก่อน (จาก SLAM Mode หรือ `~/maps/`)

### 🍓 Pi5 — Terminal 1

```bash
source ~/amr/ros2_ws/install/setup.bash
# ⚠️ ต้องใช้ absolute path (~ ไม่ทำงานกับ map_server)
ros2 launch amr_base nav2_launch.py map:=/home/khaitapad/maps/my_room.yaml
```

รอจนเห็น:
```
[lifecycle_manager] Managed nodes are active
[amcl] Received a 2D Pose Estimate
```

---

### 💻 Dev Machine — RViz

```bash
source ~/for_my_first_AMR/ros2_ws/install/setup.bash
ros2 launch amr_base dev_launch.py
```

**ขั้นตอนใน RViz:**

1. **บอกตำแหน่งเริ่มต้น** — กด **`2D Pose Estimate`** (toolbar บน)
   - คลิกบน map ตรงที่หุ่นอยู่จริง
   - ลากเพื่อกำหนดทิศ

2. **กำหนดจุดหมาย** — กด **`2D Goal Pose`**
   - คลิกบน map ตรงที่อยากให้หุ่นไป
   - หุ่นจะวางแผนเส้นทางและวิ่งเองอัตโนมัติ

---

## Quick Reference — Checklist ก่อนรัน

```
□ เสียบ ESP32 + LiDAR ทั้งคู่ก่อนเปิด Pi5
□ ls -la /dev/esp32 /dev/lidar   ← ต้องเห็น symlink
□ ros2 topic list | grep scan    ← ต้องเห็น /scan
□ เครื่อง dev อยู่ WiFi เดียวกับ Pi5
□ export ROS_DOMAIN_ID=0 (ทั้งสองเครื่อง)
```

---

## Troubleshooting ฉบับเร็ว

| อาการ | แก้ |
|---|---|
| `/dev/esp32` ไม่มี | รัน `sudo bash ~/amr/scripts/setup_udev.sh` |
| scan ไม่โผล่ | รัน `ros2 topic hz /scan` → ถ้า 0Hz = LiDAR ปัญหา |
| `/map` ไม่โผล่ | รัน `ros2 node list \| grep slam` → ต้องเห็น `/slam_toolbox` |
| RViz ไม่เห็น topics | ตรวจ `ROS_DOMAIN_ID=0` ทั้งสองเครื่อง |
| หุ่นหมุนช้า | กด `e` ใน teleop จนถึง angular=2.0 |

---

> 📁 ดูรายละเอียดเพิ่มเติม: [`pi5_setup_guide.md`](pi5_setup_guide.md)
