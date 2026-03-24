#!/bin/bash
# Docker entrypoint — source ROS2 then run CMD
set -e
source /opt/ros/humble/setup.bash
source /amr_ws/install/setup.bash
exec "$@"
