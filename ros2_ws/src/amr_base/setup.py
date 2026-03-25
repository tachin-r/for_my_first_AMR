from setuptools import setup
import os
from glob import glob

package_name = 'amr_base'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'urdf'),   glob('urdf/*.xml')),
        (os.path.join('share', package_name, 'rviz'),   glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='AMR',
    description='ESP32 serial bridge for AMR differential drive robot',
    entry_points={
        'console_scripts': [
            'esp32_bridge = amr_base.esp32_bridge:main',
            'scan_qos_bridge = amr_base.scan_qos_bridge:main',
        ],
    },
)
