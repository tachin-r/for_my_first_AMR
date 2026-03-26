#!/usr/bin/env python3
# type: ignore  # ROS2 packages only available at runtime (on Pi5 / Docker)
"""
esp32_bridge.py — ROS2 Serial Bridge Node
==========================================
หน้าที่:
  1. Subscribe /cmd_vel (geometry_msgs/Twist)
     → แปลงเป็น left/right wheel velocity (m/s)
     → ส่ง {"l": v_l, "r": v_r} ให้ ESP32 ผ่าน Serial

  2. อ่าน odometry จาก ESP32 (JSON: lt, rt, lv, rv, dt)
     → คำนวณ dead-reckoning (x, y, theta)
     → publish nav_msgs/Odometry ที่ /odom
     → broadcast TF: odom → base_link

รัน: ros2 run amr_base esp32_bridge
"""

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster
import math
import serial
import json
import threading
import time

class ESP32Bridge(Node):
    def __init__(self):
        super().__init__('esp32_bridge')

        # ---- Parameters ----
        self.declare_parameter('esp32_port',    '/dev/esp32')
        self.declare_parameter('esp32_baud',    115200)
        self.declare_parameter('wheel_diameter', 0.065)
        self.declare_parameter('wheelbase',      0.200)
        self.declare_parameter('encoder_ppr',    506)
        self.declare_parameter('encoder_x2',     True)
        self.declare_parameter('max_linear',     0.5)
        self.declare_parameter('max_angular',    2.0)
        self.declare_parameter('odom_frame',     'odom')
        self.declare_parameter('base_frame',     'base_link')
        self.declare_parameter('cmd_vel_topic',  '/cmd_vel')
        self.declare_parameter('odom_topic',     '/odom')

        port  = self.get_parameter('esp32_port').value
        baud  = self.get_parameter('esp32_baud').value
        self.wheel_diameter = self.get_parameter('wheel_diameter').value
        self.wheelbase      = self.get_parameter('wheelbase').value
        ppr                 = self.get_parameter('encoder_ppr').value
        x2                  = self.get_parameter('encoder_x2').value
        self.max_linear     = self.get_parameter('max_linear').value
        self.max_angular    = self.get_parameter('max_angular').value
        self.odom_frame     = self.get_parameter('odom_frame').value
        self.base_frame     = self.get_parameter('base_frame').value

        cpr = ppr * 2 if x2 else ppr
        self.dist_per_count = (math.pi * self.wheel_diameter) / cpr

        # ---- Odometry state ----
        self.x     = 0.0
        self.y     = 0.0
        self.theta = 0.0
        self.prev_lt = None
        self.prev_rt = None
        self._odom_lock = threading.Lock()

        # ---- Serial ----
        try:
            self.ser = serial.Serial(port, baud, timeout=0.1)
            time.sleep(1.5)  # รอ ESP32 boot
            self.get_logger().info(f'✅ ESP32 connected: {port} @ {baud}')
        except serial.SerialException as e:
            self.get_logger().fatal(f'❌ Cannot open {port}: {e}')
            raise SystemExit(1)

        # ---- ROS2 Publishers / Subscribers ----
        self.odom_pub = self.create_publisher(
            Odometry, self.get_parameter('odom_topic').value, 10)
        self.tf_bcast = TransformBroadcaster(self)

        self.cmd_sub = self.create_subscription(
            Twist, self.get_parameter('cmd_vel_topic').value,
            self.cmd_vel_callback, 10)

        # ---- Serial Reader Thread ----
        self._running = True
        self._read_thread = threading.Thread(target=self._serial_reader, daemon=True)
        self._read_thread.start()

        self.get_logger().info('🚀 ESP32 Bridge node started')

    # ------------------------------------------------------------------
    #  cmd_vel → ESP32
    # ------------------------------------------------------------------
    def cmd_vel_callback(self, msg: Twist):
        v   = msg.linear.x
        w   = msg.angular.z

        # diff-drive kinematics
        v_l = v - (w * self.wheelbase / 2.0)
        v_r = v + (w * self.wheelbase / 2.0)

        # Safety clamp
        v_l = max(-self.max_linear, min(self.max_linear, v_l))
        v_r = max(-self.max_linear, min(self.max_linear, v_r))

        cmd = json.dumps({'l': round(v_l, 4), 'r': round(v_r, 4)}) + '\n'
        try:
            self.ser.write(cmd.encode('ascii'))
        except serial.SerialException as e:
            self.get_logger().error(f'Serial write error: {e}')

    # ------------------------------------------------------------------
    #  Serial reader (runs in separate thread)
    # ------------------------------------------------------------------
    def _serial_reader(self):
        while self._running:
            try:
                raw = self.ser.readline().decode('ascii', errors='ignore').strip()
                if not raw:
                    continue
                data = json.loads(raw)

                # ข้าม status message
                if 'status' in data:
                    self.get_logger().info(f'ESP32: {data}')
                    continue

                lt = data.get('lt', 0)
                rt = data.get('rt', 0)

                with self._odom_lock:
                    self._update_odometry(lt, rt)

            except json.JSONDecodeError:
                pass   # skip malformed lines
            except serial.SerialException as e:
                self.get_logger().error(f'Serial read error: {e}')
                time.sleep(0.5)
            except Exception as e:
                self.get_logger().warn(f'Bridge error: {e}')

    # ------------------------------------------------------------------
    #  Dead-reckoning odometry
    # ------------------------------------------------------------------
    def _update_odometry(self, lt: int, rt: int):
        if self.prev_lt is None:
            self.prev_lt = lt
            self.prev_rt = rt
            return

        d_lt = lt - self.prev_lt
        d_rt = rt - self.prev_rt
        self.prev_lt = lt
        self.prev_rt = rt

        d_left  = d_lt * self.dist_per_count   # m
        d_right = d_rt * self.dist_per_count   # m
        d_center = (d_left + d_right) / 2.0
        d_theta  = (d_left - d_right) / self.wheelbase  # swapped: fix inverted rotation

        self.theta += d_theta
        self.x     += d_center * math.cos(self.theta)
        self.y     += d_center * math.sin(self.theta)

        now = self.get_clock().now()
        now_msg = now.to_msg()

        # ---- TF: odom → base_link ----
        tf = TransformStamped()
        tf.header.stamp    = now_msg
        tf.header.frame_id = self.odom_frame
        tf.child_frame_id  = self.base_frame
        tf.transform.translation.x = self.x
        tf.transform.translation.y = self.y
        tf.transform.translation.z = 0.0
        q = self._yaw_to_quat(self.theta)
        tf.transform.rotation.x = q[0]
        tf.transform.rotation.y = q[1]
        tf.transform.rotation.z = q[2]
        tf.transform.rotation.w = q[3]
        self.tf_bcast.sendTransform(tf)

        # ---- Odometry message ----
        odom = Odometry()
        odom.header.stamp    = now_msg
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id  = self.base_frame
        odom.pose.pose.position.x    = self.x
        odom.pose.pose.position.y    = self.y
        odom.pose.pose.orientation.x = q[0]
        odom.pose.pose.orientation.y = q[1]
        odom.pose.pose.orientation.z = q[2]
        odom.pose.pose.orientation.w = q[3]
        self.odom_pub.publish(odom)

    @staticmethod
    def _yaw_to_quat(yaw: float):
        """Convert yaw angle (rad) to quaternion [x, y, z, w]."""
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        return [0.0, 0.0, sy, cy]

    def destroy_node(self):
        self._running = False
        try:
            self.ser.write(b'{"l":0.0,"r":0.0}\n')  # หยุดมอเตอร์ก่อน shutdown
            self.ser.close()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ESP32Bridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
