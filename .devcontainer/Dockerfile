FROM ros:jazzy

ARG USERNAME=ubuntu
ARG USER_UID=1000

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
        ros-jazzy-rosidl-default-generators \
        ros-jazzy-rosidl-default-runtime \
        ros-jazzy-xacro \
        sudo \
    && rm -rf /var/lib/apt/lists/* \
    && if ! id -u "${USERNAME}" >/dev/null 2>&1; then \
        useradd --create-home --uid "${USER_UID}" --shell /bin/bash "${USERNAME}"; \
    fi \
    && echo "${USERNAME} ALL=(root) NOPASSWD:ALL" > "/etc/sudoers.d/${USERNAME}" \
    && chmod 0440 "/etc/sudoers.d/${USERNAME}" \
    && if [ -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then \
        rosdep update; \
    else \
        rosdep init && rosdep update; \
    fi

USER ${USERNAME}

RUN printf '%s\n' \
    'if [ -f "$HOME/colcon_ws/install/setup.bash" ]; then' \
    '    source "$HOME/colcon_ws/install/setup.bash"' \
    'else' \
    '    source /opt/ros/jazzy/setup.bash' \
    'fi' >> "$HOME/.bashrc"

WORKDIR /home/ubuntu/colcon_ws
