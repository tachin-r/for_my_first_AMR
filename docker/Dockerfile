# ================================================================
# Dockerfile — AMR ROS2 Stack for Raspberry Pi 5
# Base: ros:humble-ros-base (ARM64 compatible)
# Includes: ydlidar_ros2_driver + amr_base package
# ================================================================

FROM ros:jazzy-ros-base AS base

# ---- System dependencies ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-serial \
    python3-colcon-common-extensions \
    git \
    cmake \
    build-essential \
    udev \
    && rm -rf /var/lib/apt/lists/*

# ---- Python dependencies ----
RUN pip3 install --no-cache-dir pyserial

# ---- Workspace setup ----
WORKDIR /amr_ws

# ---- Clone YDLiDAR ROS2 driver ----
RUN mkdir -p src && \
    cd src && \
    git clone --depth 1 -b humble https://github.com/YDLIDAR/ydlidar_ros2_driver.git

# ---- Copy amr_base package ----
COPY ros2_ws/src/amr_base /amr_ws/src/amr_base

# ---- Build ----
SHELL ["/bin/bash", "-c"]
RUN source /opt/ros/jazzy/setup.bash && \
    colcon build \
      --symlink-install \
      --cmake-args -DCMAKE_BUILD_TYPE=Release \
    && rm -rf build/ydlidar_ros2_driver/CMakeFiles \
               build/amr_base

# ----------------------------------------------------------------
# Runtime stage (ลด image size)
# ----------------------------------------------------------------
FROM ros:jazzy-ros-base AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-serial \
    && rm -rf /var/lib/apt/lists/*

COPY --from=base /amr_ws/install /amr_ws/install

# Source setup ใน entrypoint
RUN echo 'source /opt/ros/jazzy/setup.bash'      >> /root/.bashrc && \
    echo 'source /amr_ws/install/setup.bash'       >> /root/.bashrc

# Entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["ros2", "launch", "amr_base", "amr_launch.py"]
