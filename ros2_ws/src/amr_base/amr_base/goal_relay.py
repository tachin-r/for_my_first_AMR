#!/usr/bin/env python3
"""
goal_relay.py — เชื่อม /goal_pose (RViz 2D Goal Pose) กับ Nav2 action server
รันบน Dev Machine: ros2 run amr_base goal_relay
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose


class GoalRelay(Node):
    def __init__(self):
        super().__init__('goal_relay')
        self._client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self._sub = self.create_subscription(
            PoseStamped, '/goal_pose', self._goal_cb, 10)
        self.get_logger().info('🎯 Goal Relay: /goal_pose → navigate_to_pose action')

    def _goal_cb(self, msg: PoseStamped):
        if not self._client.wait_for_server(timeout_sec=2.0):
            self.get_logger().warn('navigate_to_pose action server ไม่พร้อม')
            return

        goal = NavigateToPose.Goal()
        goal.pose = msg
        self.get_logger().info(
            f'📍 Sending goal: ({msg.pose.position.x:.2f}, {msg.pose.position.y:.2f})')
        future = self._client.send_goal_async(goal)
        future.add_done_callback(self._goal_response_cb)

    def _goal_response_cb(self, future):
        handle = future.result()
        if not handle.accepted:
            self.get_logger().warn('❌ Goal rejected by Nav2')
            return
        self.get_logger().info('✅ Goal accepted! Robot navigating...')
        result_future = handle.get_result_async()
        result_future.add_done_callback(self._result_cb)

    def _result_cb(self, future):
        result = future.result().result
        if result.error_code == 0:
            self.get_logger().info('🏁 Goal reached successfully!')
        else:
            self.get_logger().warn(f'⚠️ Navigation failed: {result.error_msg}')


def main():
    rclpy.init()
    node = GoalRelay()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
