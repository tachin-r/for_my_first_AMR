#!/usr/bin/env python3
"""
amr_launch.py — ROS2 Launch File for AMR
ใช้: ros2 launch amr_base amr_launch.py
ใช้ override: ros2 launch amr_base amr_launch.py esp32_port:=/dev/ttyUSB0 lidar_port:=/dev/ttyUSB1
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():

    # ================================================================
    #  Launch Arguments ( override จาก command line ได้)
    # ================================================================
    esp32_port_arg = DeclareLaunchArgument(
        'esp32_port', default_value='/dev/esp32',
        description='Serial port for ESP32 (default: /dev/esp32, override: /dev/ttyUSB0)'
    )
    lidar_port_arg = DeclareLaunchArgument(
        'lidar_port', default_value='/dev/lidar',
        description='Serial port for LiDAR (default: /dev/lidar, override: /dev/ttyUSB1)'
    )

    esp32_port = LaunchConfiguration('esp32_port')
    lidar_port = LaunchConfiguration('lidar_port')

    # ================================================================
    #  ESP32 Serial Bridge Node
    # ================================================================
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
            'odom_frame':    'odom',
            'base_frame':    'base_link',
            'cmd_vel_topic': '/cmd_vel',
            'odom_topic':    '/odom',
        }]
    )

    # ================================================================
    #  YDLiDAR X3 Pro Driver Node
    #  Params confirmed from hardware: Model S2PRO, FW 3.1, HW 3
    # ================================================================
    ydlidar_node = Node(
        package='ydlidar_ros2_driver',
        executable='ydlidar_ros2_driver_node',
        name='ydlidar_ros2_driver_node',
        output='screen',
        parameters=[{
            'port':              lidar_port,
            'frame_id':          'laser_frame',
            'ignore_array':      '',
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
        }]
    )

    return LaunchDescription([
        esp32_port_arg,
        lidar_port_arg,
        esp32_bridge_node,
        ydlidar_node,
    ])
