# Continuum Stack

ROS 2 Jazzy workspace for the Continuum arm. The packages in this repository
are the canonical source. See [docs/refactoring.md](docs/refactoring.md) for
the original project repositories and [docs/next_steps.md](docs/next_steps.md)
for the student handover, known issues, and verification limits.

## Packages

| Package | Purpose |
| --- | --- |
| `continuum_msgs` | Shared `ArmTarget`, `MotorFeedback`, and `MotorMotionControl` messages; home for future services/actions. |
| `continuum_carmy_motor_controller` | RobStride SocketCAN driver. |
| `continuum_joystick_mapper` | Maps two `sensor_msgs/msg/Joy` inputs to arm targets. |
| `continuum_arm_controller` | Converts enabled, fresh arm targets into round-robin motor commands. |
| `continuum_bringup` | Namespaced stack launch, configuration, and fake motor backend. |

All three ROS messages are generated from `continuum_msgs`. Clients using the
previous package-qualified message types must update imports and manifest
dependencies to `continuum_msgs`.

See [docs/refactoring.md](docs/refactoring.md) for the source-to-package map,
provenance, and a fuller list of interface and runtime changes.

## Topics

By default, `stack.launch.py` places nodes and relative topics under
`/continuum_stack`. Pass `namespace:=...` to select another namespace.

| Relative topic | Type | Direction |
| --- | --- | --- |
| `stage_1/joy`, `stage_2/joy` | `sensor_msgs/msg/Joy` | Mapper input |
| `arm_target` | `continuum_msgs/msg/ArmTarget` | Mapper to controller |
| `motor_feedback` | `continuum_msgs/msg/MotorFeedback` | Driver/fake backend to controller |
| `motion_control` | `continuum_msgs/msg/MotorMotionControl` | Controller to driver/fake backend |

`/arm_target` uses `continuum_msgs/msg/ArmTarget`; the previously referenced
`carmy_motor_controller/msg/ArmTarget` did not exist. Its four stage values
currently carry normalized joystick axes, not calibrated radians.
`gripper` and `mode` retain placeholder values. The controller's default gain
and first-connected-feedback offset are uncalibrated; first feedback is not a
verified home position.

## Build

Rebuild the devcontainer after changing its Dockerfile. From a fresh container:

```bash
source /opt/ros/jazzy/setup.bash
cd /home/ubuntu/colcon_ws
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
colcon list
colcon build --symlink-install
source install/setup.bash
```

The package sources live directly under `src/continuum_stack/`. The build
creates `continuum_arm_controller`, `continuum_bringup`,
`continuum_carmy_motor_controller`, `continuum_msgs`, and
`continuum_joystick_mapper` exactly once.

Inspect the generated interfaces with:

```bash
ros2 interface show continuum_msgs/msg/ArmTarget
ros2 interface show continuum_msgs/msg/MotorMotionControl
ros2 interface show continuum_msgs/msg/MotorFeedback
```

## Hardware-Free Bringup

The fake launch starts the mapper, arm controller, and synthetic motor
feedback/command backend. It does not start the CAN driver, enable motors, or
start physical joystick nodes by default:

```bash
ros2 launch continuum_bringup fake.launch.py
```

The fake launch forces `enable_real_hardware:=false`, even if it is supplied
as `true`. `--show-args` displays the shared stack argument's `true` default,
not the fake wrapper's override.

Publish synthetic joystick messages in a second terminal to exercise the ROS
path. Button 0 is the enable input; either stage enables the target:

```bash
ros2 topic pub --once /continuum_stack/stage_1/joy sensor_msgs/msg/Joy \
	"{axes: [0.2, -0.3, 0.0, 0.0], buttons: [1]}"
```

The fake backend reports four connected motors at zero position and logs
received commands. It does not simulate motor dynamics, CAN behavior, physical
limits, or stopping behavior. With joystick nodes enabled, set their device
indices explicitly:

```bash
ros2 launch continuum_bringup fake.launch.py use_joysticks:=true \
	stage_1_device:=0 stage_2_device:=1
```

Device availability and permissions are host/container responsibilities; a
missing device is reported by `joy_node`, not treated as a healthy input.

## Hardware Operation

The stack launch starts the real driver by default:

```bash
ros2 launch continuum_bringup stack.launch.py
```

This command can open `can0` and enable configured motors immediately at
startup. Do not use it as an
automated test. Hardware commissioning requires a separate operator decision,
supervision, validated robot configuration, mechanical restraint, and an
independent emergency stop. Host CAN setup is an operator-only task; this
workspace never configures host links or runs legacy setup scripts.
The real SocketCAN driver remains implemented, but has not been tested on
hardware after this refactor. See the commissioning checklist in
[docs/next_steps.md](docs/next_steps.md#real-can-handover).

The mapper disables a stale joystick's trigger and substitutes zero for its
axes. If the other joystick remains fresh and enabled, the combined target can
still be enabled and the stale stage can be commanded toward its offset. This
behavior requires review before hardware operation. The controller gates on
disabled or stale targets and disconnected or stale feedback. The driver stops
repeating expired commands, but blocking CAN reads can delay expiry handling.
Stopping command frames does not establish that a physical motor has stopped.
No physical travel/torque limits or functional safety claims are made here.

## Configuration and Namespaces

Defaults are in `continuum_bringup/config/stack.yaml`. The mapper exposes
joystick axis/button indices and input/output topics. The controller exposes
the gain, `kp`, `kd`, command period, and target/feedback timeouts. The driver
exposes CAN interface, motor IDs/types, and command timeout. Gains, offsets,
and the motor protocol require hardware validation before operation.

For example, launch under another namespace:

```bash
ros2 launch continuum_bringup fake.launch.py namespace:=lab_arm
```

Relative topics then resolve under `/lab_arm`. ROS remappings can override
individual topic names when integrating with another graph.

## Devcontainer and Troubleshooting

The devcontainer is based on ROS 2 Jazzy and selects Cyclone DDS through
`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`; its Dockerfile installs the matching
ROS package. The current devcontainer configuration requests privileged mode,
host networking, all GPUs, and a `/dev` bind mount. These requirements may not
work on every host and grant broad device access; review them before use.
Rebuild the container after Dockerfile changes, then follow the build commands
above. The image rebuild has not been verified in this environment.

Use the same build options consistently in a workspace: switching an existing
build between a normal install and `--symlink-install` can leave incompatible
generated artifacts. To avoid disturbing an existing build, use fresh
`--build-base` and `--install-base` directories instead.

If `rosdep install` reports an uninitialized database, initialize/update
rosdep in the container and retry. If packages do not appear in `colcon list`,
check that the package directory contains its `package.xml` and that no
`COLCON_IGNORE` file is hiding it. If launch cannot find an executable, rebuild
and source `install/setup.bash` in the same terminal.

Software tests and the fake backend do not verify SocketCAN hardware, motor
communications, calibration, physical limits, or safe stopping behavior. No
real hardware tests are run automatically.
