#!/usr/bin/env python3
"""
dev_launch.py — รันบน Dev Machine เท่านั้น
Pi5 ต้องรัน: ros2 launch amr_base slam_launch.py launch_rviz:=false

รัน: ros2 launch amr_base dev_launch.py
"""

import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg = get_package_share_directory('amr_base')
    rviz_config = os.path.join(pkg, 'rviz', 'slam.rviz')

    # ── RViz2 ──────────────────────────────────────────────────────
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        output='screen',
    )

    # ── Teleop Keyboard ────────────────────────────────────────────
    teleop = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop',
        output='screen',
        prefix='xterm -e',    # เปิด terminal ใหม่สำหรับ keyboard input
    )

    return LaunchDescription([
        rviz,
        teleop,
    ])
