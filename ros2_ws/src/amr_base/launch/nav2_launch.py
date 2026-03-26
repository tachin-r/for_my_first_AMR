#!/usr/bin/env python3
"""
nav2_launch.py — Pi5 Launch: SLAM or Nav2
==========================================
SLAM mode (สร้างแผนที่):
  ros2 launch amr_base nav2_launch.py
  ros2 launch amr_base nav2_launch.py mode:=slam

Nav2 mode (นำทาง):
  ros2 launch amr_base nav2_launch.py mode:=nav2 map:=~/maps/my_room.yaml
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import (
    LaunchConfiguration, Command, PythonExpression)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg         = get_package_share_directory('amr_base')
    urdf_file   = os.path.join(pkg, 'urdf', 'amr.urdf.xml')
    nav2_params = os.path.join(pkg, 'config', 'nav2_params.yaml')

    # ── Launch Arguments ──────────────────────────────────────────────
    mode_arg = DeclareLaunchArgument(
        'mode', default_value='slam',
        description='slam (สร้างแผนที่) หรือ nav2 (นำทาง)')
    map_arg = DeclareLaunchArgument(
        'map',
        default_value=os.path.expanduser('~/maps/my_room.yaml'),
        description='Path to map YAML file (เฉพาะ nav2 mode)')
    launch_rviz_arg = DeclareLaunchArgument(
        'launch_rviz', default_value='false',
        description='เปิด RViz บน Pi5 ไหม')

    mode        = LaunchConfiguration('mode')
    map_file    = LaunchConfiguration('map')
    launch_rviz = LaunchConfiguration('launch_rviz')

    is_slam = PythonExpression(['"', mode, '" == "slam"'])
    is_nav2 = PythonExpression(['"', mode, '" == "nav2"'])

    # ── 1. Robot State Publisher ──────────────────────────────────────
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': ParameterValue(
                Command(['cat ', urdf_file]), value_type=str),
            'use_sim_time': False,
        }]
    )

    # ── 1.5 Joint State Publisher ─────────────────────────────────────
    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        output='screen',
    )

    # ── 2. ESP32 Bridge ──────────────────────────────────────────────
    esp32_bridge = Node(
        package='amr_base',
        executable='esp32_bridge',
        name='esp32_bridge',
        output='screen',
        parameters=[{
            'esp32_port':     '/dev/esp32',
            'esp32_baud':     115200,
            'wheel_diameter': 0.065,
            'wheelbase':      0.200,
            'encoder_ppr':    506,
            'encoder_x2':     True,
            'max_linear':     0.5,
            'max_angular':    2.0,
        }]
    )

    # ── 3. YDLiDAR ───────────────────────────────────────────────────
    ydlidar = Node(
        package='ydlidar_ros2_driver',
        executable='ydlidar_ros2_driver_node',
        name='ydlidar_ros2_driver_node',
        output='screen',
        parameters=[{
            'port':              '/dev/lidar',
            'frame_id':          'laser_frame',
            'baudrate':          115200,
            'lidar_type':        1,
            'device_type':       0,
            'isSingleChannel':   True,
            'support_motor_dtr': True,
            'intensity':         False,
            'sample_rate':       4,
            'fixed_resolution':  True,
            'auto_reconnect':    True,
            'angle_max':         180.0,
            'angle_min':        -180.0,
            'range_max':         8.0,
            'range_min':         0.1,
            'frequency':         10.0,
            'reversion':         False,
            'inverted':          False,
            'invalid_range_is_inf': False,
            'ignore_array':      '',
        }]
    )

    # ── 3.5 Scan QoS Bridge ──────────────────────────────────────────
    scan_bridge = Node(
        package='amr_base',
        executable='scan_qos_bridge',
        name='scan_qos_bridge',
        output='screen',
    )

    # ══════════════════════════════════════════════════════════════════
    #  SLAM MODE — slam_toolbox (สร้างแผนที่)
    # ══════════════════════════════════════════════════════════════════
    slam_toolbox = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[{
            'use_sim_time': False,
            'odom_frame': 'odom',
            'map_frame': 'map',
            'base_frame': 'base_link',
            'scan_topic': '/scan_reliable',
            'mode': 'mapping',
            'resolution': 0.05,
            'max_laser_range': 8.0,
            'minimum_travel_distance': 0.3,
            'minimum_travel_heading': 0.3,
            'map_update_interval': 3.0,
            'transform_timeout': 0.5,
            'tf_buffer_duration': 30.0,
            'stack_size_to_use': 40000000,
        }],
        condition=IfCondition(is_slam),
    )

    # Lifecycle manager สำหรับ SLAM mode (activate slam_toolbox)
    slam_lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_slam',
        output='screen',
        parameters=[{
            'use_sim_time': False,
            'autostart': True,
            'bond_timeout': 0.0,  # slam_toolbox ไม่ support bond — ปิดเลย
            'node_names': ['slam_toolbox'],
        }],
        condition=IfCondition(is_slam),
    )

    # ══════════════════════════════════════════════════════════════════
    #  NAV2 MODE — slam_toolbox (localization) + navigation nodes
    # ══════════════════════════════════════════════════════════════════
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[nav2_params, {'yaml_filename': map_file}],
        condition=IfCondition(is_nav2),
    )

    # slam_toolbox localization mode (แทน AMCL)
    slam_toolbox_loc = Node(
        package='slam_toolbox',
        executable='localization_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[{
            'use_sim_time': False,
            'odom_frame': 'odom',
            'map_frame': 'map',
            'base_frame': 'base_link',
            'scan_topic': '/scan_reliable',
            'mode': 'localization',
            'map_file_name': map_file,
            'map_start_at_dock': True,
            'resolution': 0.05,
            'max_laser_range': 8.0,
            'transform_timeout': 0.5,
            'tf_buffer_duration': 30.0,
            'stack_size_to_use': 40000000,
        }],
        condition=IfCondition(is_nav2),
    )

    controller = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[nav2_params],
        condition=IfCondition(is_nav2),
    )

    planner = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[nav2_params],
        condition=IfCondition(is_nav2),
    )

    behavior = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[nav2_params],
        condition=IfCondition(is_nav2),
    )

    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[nav2_params],
        condition=IfCondition(is_nav2),
    )

    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'use_sim_time': False,
            'autostart': True,
            'bond_timeout': 0.0,
            'node_names': [
                'map_server',
                'slam_toolbox',
                'controller_server',
                'planner_server',
                'behavior_server',
                'bt_navigator',
            ]
        }],
        condition=IfCondition(is_nav2),
    )

    # ── RViz (optional บน Pi5) ────────────────────────────────────────
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', os.path.join(pkg, 'rviz', 'slam.rviz')],
        output='screen',
        condition=IfCondition(launch_rviz),
    )

    return LaunchDescription([
        mode_arg,
        map_arg,
        launch_rviz_arg,
        # ── Always ──
        robot_state_publisher,
        joint_state_publisher,
        esp32_bridge,
        ydlidar,
        scan_bridge,
        # ── SLAM mode ──
        slam_toolbox,
        slam_lifecycle_manager,
        # ── Nav2 mode ──
        map_server,
        slam_toolbox_loc,
        controller,
        planner,
        behavior,
        bt_navigator,
        lifecycle_manager,
        # ── Optional ──
        rviz,
    ])
