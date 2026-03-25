#!/usr/bin/env python3
"""
nav2_launch.py — Nav2 Autonomous Navigation Launch
====================================================
รัน: ros2 launch amr_base nav2_launch.py map:=~/maps/my_room.yaml

Pi5 ต้อง install nav2 ก่อน:
  sudo apt install -y ros-jazzy-nav2-bringup
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg      = get_package_share_directory('amr_base')
    nav2_pkg = get_package_share_directory('nav2_bringup')

    urdf_file   = os.path.join(pkg, 'urdf', 'amr.urdf.xml')
    nav2_params = os.path.join(pkg, 'config', 'nav2_params.yaml')
    rviz_config = os.path.join(pkg, 'rviz', 'slam.rviz')

    # ── Launch Arguments ──────────────────────────────────────────────
    map_arg = DeclareLaunchArgument(
        'map',
        default_value=os.path.expanduser('~/maps/my_room.yaml'),
        description='Path to map YAML file')
    launch_rviz_arg = DeclareLaunchArgument(
        'launch_rviz', default_value='false',
        description='เปิด RViz บน Pi5 ไหม (false = ประหยัด CPU)')

    map_file    = LaunchConfiguration('map')
    launch_rviz = LaunchConfiguration('launch_rviz')

    # ── 1. robot_state_publisher ──────────────────────────────────────
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

    # ── 2. ESP32 Bridge ───────────────────────────────────────────────
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

    # ── 3.5 Scan QoS Bridge ───────────────────────────────────────────
    scan_bridge = Node(
        package='amr_base',
        executable='scan_qos_bridge',
        name='scan_qos_bridge',
        output='screen',
    )

    # ── 4. Nav2 Bringup (map_server + amcl + planner + controller) ───
    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_pkg, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map':          map_file,
            'params_file':  nav2_params,
            'use_sim_time': 'false',
            'slam':         'False',    # ใช้ map ที่มีอยู่ ไม่ SLAM
        }.items(),
    )

    # ── 5. RViz (optional บน Pi5) ─────────────────────────────────────
    from launch.conditions import IfCondition
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        output='screen',
        condition=IfCondition(launch_rviz),
    )

    return LaunchDescription([
        map_arg,
        launch_rviz_arg,
        robot_state_publisher,
        esp32_bridge,
        ydlidar,
        scan_bridge,
        nav2_bringup,
        rviz,
    ])
