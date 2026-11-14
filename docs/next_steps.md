# Student Handover

## Starting Point

This repository consolidates the joystick and motor-driver projects into five
ROS 2 Jazzy packages. The map from the original sources and public API changes
is in [refactoring.md](refactoring.md); build and hardware-free launch commands
are in the [README](../README.md). Cyclone DDS is the intended middleware:
`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` and the devcontainer Dockerfile declares
`ros-jazzy-rmw-cyclonedds-cpp`.

`stack.launch.py` starts the real CAN driver by default and can enable motors
immediately. `fake.launch.py` selects the synthetic motor backend instead.
The motor message fields match the original definitions, but their ROS type
names are now in `continuum_msgs/msg`, so old clients need updating. The arm
target message was inferred from the original consumers; joystick values,
controller gain, and feedback-based offsets are not calibrated.

The migrated code has not been commissioned on real motors, and functional
equivalence with the original hardware setup is not established. The fake
backend does not simulate dynamics, limits, CAN, or stopping. The old source
repositories are linked in [refactoring.md](refactoring.md); verify with the
owners whether local historical checkouts and Git metadata were archived.

## Real CAN Handover

The real SocketCAN implementation remains in
[`motor_cfg.cpp`](../continuum_carmy_motor_controller/src/motor_cfg.cpp) and
[`motor_cfg.h`](../continuum_carmy_motor_controller/include/continuum_carmy_motor_controller/motor_cfg.h).
It opens and binds a Linux raw CAN socket, filters motor feedback, sends the
upstream-style RobStride frames, and decodes status frames. The ROS wrapper is
[`main.cpp`](../continuum_carmy_motor_controller/src/main.cpp). It is not a
fake or a replacement for the CAN driver, but the refactored driver has not
been verified on a CAN bus or real motors.

The real-hardware launch is `ros2 launch continuum_bringup stack.launch.py`;
its `enable_real_hardware` argument defaults to `true`.
It starts the driver and enables the configured motors on startup, even before
the controller receives a joystick target. Add `use_joysticks:=true` and device
IDs only when the operator intends to use physical joysticks. The driver
defaults to `can0`, IDs 1-4 and motor type 5 in
[`stack.yaml`](../continuum_bringup/config/stack.yaml); verify these against
the actual robot rather than assuming they are correct.

Before a student operates hardware, an authorized operator should:

- Confirm the CAN adapter and host interface are configured for that hardware;
	ensure the selected interface is visible inside the container. Host setup is
	a separate operator task, not part of automated tests or launch.
- Verify motor IDs, types, wiring, calibration, offsets, physical travel and
	torque limits against the actual robot, and check joystick device permissions.
- Arrange mechanical restraint, an independent emergency stop and a clear
	observation area. Review the input-loss and blocking-read issues below first.
- Only after authorization, supervise an incremental feedback/command check
	and observe timeout and recovery behavior. Do not infer physical stopping
	from a command timeout or a stopped stream of CAN frames.

The ROS type namespace, startup behavior, command freshness, and feedback
freshness differ from upstream. Record actual test results and configuration;
upstream validation of a different hardware setup does not validate this build.

## Priorities

1. **Agree on input-loss behavior.** The mapper currently substitutes zero
	for a stale or malformed joystick while the other fresh trigger can keep
	the target enabled. That can command the failed stage toward its offset.
	Agree on a policy with the robot team, implement it, and test loss,
	malformed input, disable, and recovery for both joysticks. Do not assume
	zero is safe.
2. **Make the driver testable without CAN.** Introduce an injectable transport
	and controlled clock; test startup with hardware disabled, no commands
	before a valid input, per-motor expiry, invalid input, errors, and recovery.
	Current synchronous CAN reads can block command handling and delay expiry;
	measure and bound this behavior. Report read and write failures explicitly.
3. **Validate feedback and offsets.** The driver now tracks the age of valid
	status frames instead of interpreting all-zero feedback as disconnected.
	Add hardware-free tests for valid, unrelated, malformed, timed-out, and
	recovered frames and transport errors. Decide how stale feedback and
	reconnection affect latched offsets; test controller gating and recovery.
4. **Automate end-to-end bringup.** Add an installed-launch integration test
	using synthetic `Joy` messages and fake feedback. Observe enabled targets
	and round-robin commands for all four IDs, stale input and recovery, and
	confirm the fake launch does not instantiate the real driver. Keep the test isolated
	from real devices and CAN.
5. **Make development reproducible.** Rebuild the devcontainer on a supported
	host and verify Cyclone DDS, non-root user, workspace permissions, rosdep,
	clean build, installed launch, and tests. The current configuration requests
	privileged mode, host networking, all GPUs, and `/dev`; design a portable
	default and a separately documented, opt-in hardware configuration. Review
	the legacy joystick launch, which uses absolute remappings and silently
	skips absent devices.
6. **Resolve project ownership.** Confirm package maintainers, licenses, and
	original source backups with the project owners. Preserve notices and
	history; do not infer missing license or maintainer details. Review tracked
	generated logs and ignore rules without discarding existing user data.

## Verification Workflow

Start in a fresh Jazzy environment, install declared dependencies with rosdep,
and source the intended overlay before checking the graph. Use consistent
colcon build options, or choose fresh build/install directories if an old
cache conflicts. Run `colcon list`, `colcon build`, `colcon test`,
`colcon test-result --verbose`, and inspect all three `continuum_msgs/msg`
interfaces. Follow the README for the fake bringup and synthetic input.

Passing software tests is not a hardware safety assessment. Never run the
legacy CAN setup scripts automatically or enable hardware during tests. A
separate, explicit operator-supervised commissioning decision is required to
verify device access, motor IDs and types, CAN protocol, calibration, offsets,
limits and timeout behavior with mechanical restraint and an independent
emergency stop. No physical stopping guarantee is established.
