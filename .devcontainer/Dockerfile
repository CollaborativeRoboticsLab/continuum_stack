FROM ros:jazzy

ARG USERNAME=ubuntu
ARG USER_UID=1000
ARG USER_GID=$USER_UID
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

RUN apt-get update && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        can-utils \
        cmake \
        git \
        iproute2 \
        python3-colcon-common-extensions \
        python3-flake8 \
        python3-pytest \
        python3-rosdep \
        python3-venv \
        python3-vcstool \
        ros-jazzy-ament-copyright \
        ros-jazzy-ament-flake8 \
        ros-jazzy-ament-pep257 \
        ros-jazzy-joy \
        ros-jazzy-launch-testing \
        ros-jazzy-launch-testing-ros \
        ros-jazzy-rmw-cyclonedds-cpp \
        ros-jazzy-rosidl-default-generators \
        ros-jazzy-rosidl-default-runtime \
        ros-jazzy-xacro \
        sudo \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN echo "${USERNAME} ALL=(root) NOPASSWD:ALL" > "/etc/sudoers.d/${USERNAME}" \
    && chmod 0440 "/etc/sudoers.d/${USERNAME}"

USER ${USERNAME}

# Rosdep update
RUN rosdep update

# Source the ROS setup file
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc

WORKDIR /home/$USERNAME/colcon_ws
