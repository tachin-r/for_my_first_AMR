#!/usr/bin/env python3
"""
scan_qos_bridge.py
รับ /scan แบบ BestEffort แล้ว republish เป็น /scan_reliable แบบ Reliable
เพื่อแก้ปัญหา QoS mismatch ระหว่าง YDLiDAR และ slam_toolbox
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan


class ScanQoSBridge(Node):
    def __init__(self):
        super().__init__('scan_qos_bridge')

        # Subscriber: BEST_EFFORT (ตรงกับ YDLiDAR publisher)
        sub_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )

        # Publisher: RELIABLE (ตรงกับที่ slam_toolbox ต้องการ)
        pub_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )

        self.sub = self.create_subscription(
            LaserScan, '/scan', self.callback, sub_qos)
        self.pub = self.create_publisher(
            LaserScan, '/scan_reliable', pub_qos)

        self.get_logger().info('✅ Scan QoS Bridge: /scan (BestEffort) → /scan_reliable (Reliable)')

    def callback(self, msg):
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = ScanQoSBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
