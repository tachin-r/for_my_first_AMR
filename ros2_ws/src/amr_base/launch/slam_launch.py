#!/usr/bin/env python3
"""
slam_launch.py — SLAM Launch File
รัน: ros2 launch amr_base slam_launch.py
รัน override port: ros2 launch amr_base slam_launch.py esp32_port:=/dev/ttyUSB0 lidar_port:=/dev/ttyUSB1
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg = get_package_share_directory('amr_base')

    # ── Launch Arguments ──────────────────────────────────────────
    esp32_port_arg = DeclareLaunchArgument(
        'esp32_port', default_value='/dev/esp32',
        description='ESP32 serial port')
    lidar_port_arg = DeclareLaunchArgument(
        'lidar_port', default_value='/dev/lidar',
        description='LiDAR serial port')
    launch_rviz_arg = DeclareLaunchArgument(
        'launch_rviz', default_value='false',
        description='เปิด RViz2 ไหม (false = ประหยัด CPU บน Pi5)')

    esp32_port = LaunchConfiguration('esp32_port')
    lidar_port  = LaunchConfiguration('lidar_port')
    launch_rviz = LaunchConfiguration('launch_rviz')

    urdf_file = os.path.join(pkg, 'urdf', 'amr.urdf.xml')
    slam_params = os.path.join(pkg, 'config', 'slam_params.yaml')
    rviz_config = os.path.join(pkg, 'rviz', 'slam.rviz')

    # ── 1. robot_state_publisher (URDF → TF base_link→laser_frame) ──
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': ParameterValue(
                Command(['cat ', urdf_file]), value_type=str
            ),
            'use_sim_time': False,
        }]
    )

    # ── 2. ESP32 Serial Bridge ─────────────────────────────────────
    esp32_bridge_node = Node(
        package='amr_base',
        executable='esp32_bridge',
        name='esp32_bridge',
        output='screen',
        parameters=[{
            'esp32_port':     esp32_port,
            'esp32_baud':     115200,
            'wheel_diameter': 0.065,
            'wheelbase':      0.200,
            'encoder_ppr':    506,
            'encoder_x2':     True,
            'max_linear':     0.5,
            'max_angular':    2.0,
        }]
    )

    # ── 3. YDLiDAR X3 Pro ─────────────────────────────────────────
    ydlidar_node = Node(
        package='ydlidar_ros2_driver',
        executable='ydlidar_ros2_driver_node',
        name='ydlidar_ros2_driver_node',
        output='screen',
        parameters=[{
            'port':              lidar_port,
            'frame_id':          'laser_frame',
            'baudrate':          115200,
            'lidar_type':        1,
            'device_type':       0,
            'isSingleChannel':   True,
            'support_motor_dtr': True,
            'intensity':         False,
            'intensity_bit':     0,
            'sample_rate':       4,
            'fixed_resolution':  True,
            'abnormal_check_count': 4,
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

    # ── 4. SLAM Toolbox ───────────────────────────────────────────
    slam_toolbox = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[slam_params, {'use_sim_time': False}],
    )

    # ── 5. RViz2 (ปิดได้เพื่อประหยัด CPU บน Pi5) ──────────────────
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        output='screen',
        condition=IfCondition(launch_rviz),  # launch_rviz:=true เพื่อเปิด
    )

    return LaunchDescription([
        esp32_port_arg,
        lidar_port_arg,
        launch_rviz_arg,
        robot_state_publisher,
        esp32_bridge_node,
        ydlidar_node,
        slam_toolbox,
        rviz,
    ])
