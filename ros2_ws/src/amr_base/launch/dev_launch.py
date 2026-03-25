#!/usr/bin/env python3
"""
dev_launch.py — รันบน Dev Machine เท่านั้น

SLAM mode:  ros2 launch amr_base dev_launch.py            (default)
Nav2 mode:  ros2 launch amr_base dev_launch.py mode:=nav2
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch.conditions import IfCondition
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg = get_package_share_directory('amr_base')
    slam_rviz = os.path.join(pkg, 'rviz', 'slam.rviz')
    nav2_rviz = os.path.join(pkg, 'rviz', 'nav2.rviz')

    mode_arg = DeclareLaunchArgument(
        'mode', default_value='slam',
        description='slam หรือ nav2')
    mode = LaunchConfiguration('mode')

    is_nav2 = PythonExpression(['"', mode, '" == "nav2"'])
    is_slam  = PythonExpression(['"', mode, '" != "nav2"'])

    # ── RViz (เลือก config ตาม mode) ──────────────────────────────
    rviz_slam = Node(
        package='rviz2', executable='rviz2', name='rviz2',
        arguments=['-d', slam_rviz], output='screen',
        condition=IfCondition(is_slam),
    )
    rviz_nav2 = Node(
        package='rviz2', executable='rviz2', name='rviz2',
        arguments=['-d', nav2_rviz], output='screen',
        condition=IfCondition(is_nav2),
    )

    # ── Teleop (SLAM เท่านั้น) ──────────────────────────────────────
    teleop = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop', output='screen',
        prefix='xterm -e',
        condition=IfCondition(is_slam),
    )

    # ── Goal Relay (nav2 เท่านั้น) — /goal_pose → navigate_to_pose ──
    goal_relay = Node(
        package='amr_base',
        executable='goal_relay',
        name='goal_relay', output='screen',
        condition=IfCondition(is_nav2),
    )

    return LaunchDescription([
        mode_arg,
        rviz_slam,
        rviz_nav2,
        teleop,
        goal_relay,
    ])
