# ROS 2 Jazzy stack migration plan

## Objective and execution constraints

Refactor the supplied projects into one maintainable ROS 2 Jazzy stack in
`/home/ubuntu/colcon_ws/src/continuum_stack`, and update its existing
`.devcontainer`. This document is for the implementation agent; do not treat
the plan itself as an implementation.

Work in dependency order below. Preserve existing behavior and public names
unless a change is explicitly called out. Do not command, enable, calibrate, or
reconfigure real motors, CAN interfaces, or joysticks during implementation or
automated tests. Hardware commissioning requires an operator and a separate
explicit decision. Do not claim functional safety or invent motor limits,
homing procedures, or an emergency-stop mechanism.

## Current state and important findings

- The top-level `continuum_stack` Git repository tracks only its README. Its
  `.devcontainer`, `.vscode`, and the two nested Git repositories are currently
  untracked. The nested repositories contain the real source. The joystick
  repository also records an **uninitialized** `src/carmy_motor_controller`
  submodule. Check all worktrees and preserve user changes before moving files.
- `colcon list` currently discovers `joystick_mapper`, `arm_controller`, and
  `carmy_motor_controller`. The first two import
  `carmy_motor_controller.msg.ArmTarget`, but no `ArmTarget.msg` exists. Their
  manifests do not declare their message dependency.
- The mapper publishes `/arm_target` at 10 Hz from `/stage_1/joy` and
  `/stage_2/joy`; either trigger enables it. The arm controller waits for a
  target and four initial feedback samples, then publishes one motor command
  per 12.5 ms tick in round-robin order. Its gain is a placeholder, not a
  validated calibration. The driver uses `/motion_control` and
  `/motor_feedback`, IDs 1–4, type 5 and `can0`.
- The motor node opens CAN and enables motors at startup, then its timer sends
  commands even before receiving an input. Simply stopping the arm controller's
  publications does **not** stop the driver from holding its last target.
  Existing joystick and feedback handling can also retain stale state.
- The motor CMake file asks for C++14 while source uses C++17 features; verify
  and fix Jazzy-compatible rosidl typesupport linkage. The mapper's launch
  file silently omits joystick drivers when devices are absent. Legacy helper
  scripts have conflicting Humble/Jazzy container setups; the CAN scripts
  include host-wide actions and must not be run as automated setup.
- The current devcontainer is based on `ros:jazzy`; `joy` and CAN utilities
  are installed only by legacy scripts or other images, not by this image.

## Target structure and public contracts

Create these sibling packages under
`/home/ubuntu/colcon_ws/src/continuum_stack/`:

1. `continuum_msgs` (`ament_cmake`): generate `ArmTarget.msg`,
  `MotorFeedback.msg`, and `MotorMotionControl.msg` with
   `float64 stage_1_x_angle`, `stage_1_y_angle`, `stage_2_x_angle`,
   `stage_2_y_angle`, `float64 gripper`, `uint8 mode`, and `bool enabled`.
  `ArmTarget` is inferred from the existing Python consumers, not recovered
  from an original definition. Document normalized joystick values and
  placeholder semantics; do not assert calibrated radians. No `.srv` or
  `.action` definitions currently exist; place future interfaces here.
2. `continuum_carmy_motor_controller` (`ament_cmake`): existing C++ driver.
  Keep both existing motor message definitions byte-for-byte in
  `continuum_msgs`; the package-qualified ROS type changes as a result.
  Preserve executable `rs_motor_ros2_node` and default motion/feedback topic
  names.
3. `continuum_joystick_mapper` (`ament_python`): existing mapper executable
  and joystick launch assets; use `continuum_msgs/msg/ArmTarget`.
4. `continuum_arm_controller` (`ament_python`): existing controller
  executable; consume `continuum_msgs/msg/ArmTarget` and motor messages.
5. `continuum_bringup` (a small installable ROS package): launch and parameter
   files for the assembled stack and hardware-free testing.

Putting all generated messages in `continuum_msgs` decouples interface types
from the motor driver. Moving the motor messages changes their package-qualified
ROS type names but not their definitions or fields; document the downstream
client update. `/arm_target` uses `continuum_msgs/msg/ArmTarget` (the
previously imported type did not exist). Keep topic defaults compatible, while
making names/remappings usable for namespaces.

## Implementation sequence

### 1. Preserve sources and establish a single owner

- Record `git status --short` in the top-level and both nested repositories;
  inspect their tracked files, Git metadata, and the joystick submodule state.
  Never reset, overwrite, or delete user changes. Preserve source provenance,
  copyright notices, licenses, and upstream references; do not invent a
  license or maintainer identity if the project does not establish one.
- Copy/refactor the three existing packages into `packages/`, including their
  executable entry points, resource markers, and necessary source. Do not
  initialize the old submodule: it would introduce a second motor package.
  Retain a recoverable copy of both original repositories and their `.git`
  metadata outside the colcon `src` discovery tree, without overwriting an
  existing path. If preserving them requires moving user-modified data or
  ownership is unclear, stop and ask the user before doing so.
- Ensure the new packages, `.devcontainer`, and documentation can actually be
  tracked by the top-level repository, rather than relying on changes hidden
  inside untracked nested Git repositories. Avoid Git submodules or embedded
  repositories for the migrated packages. Do not commit unless asked.
- Confirm `colcon list` discovers exactly one instance of each target package
  even on a fresh checkout. Do not rely on an untracked `COLCON_IGNORE` marker
  or a local-only submodule state.

### 2. Interfaces, builds, and package metadata

- Implement `continuum_msgs`, including `rosidl_default_generators`,
  `rosidl_default_runtime`, and interface-package membership. Generate and
  install all three messages; update C++ and Python consumers.
- Correct package manifests for actual build, runtime, launch, and test
  dependencies, including `rclpy`, `sensor_msgs`, the relevant custom
  interfaces, `joy`, `launch`, `launch_ros`, and testing dependencies where
  used. Remove misleading unused dependencies where justified. Make package
  names, versions, resources, and Python setup/install metadata consistent.
- Set the motor package to at least C++17, depend on `continuum_msgs`, and
  install its library/executable and headers correctly. Preserve the two
  existing motor `.msg` definitions byte-for-byte.
- Verify packages build in dependency order using a clean Jazzy environment;
  do not rely on a previously built overlay or undeclared system packages.

### 3. Controller and driver integration

- Preserve the existing axis mapping, trigger OR behavior, gains, motor IDs,
  initial-feedback gating, and round-robin behavior as defaults where safe.
  Expose configuration through validated ROS parameters/YAML: joystick
  device selection, axis/button mappings, motor IDs/types, CAN interface,
  gains and rates. Defaults must match existing behavior unless the safety
  gating below explicitly changes it. Document gains and offset latching as
  uncalibrated; do not call first feedback a verified home.
- Refactor dependencies at hardware boundaries so automated tests can use a
  fake motor transport; keep real SocketCAN protocol behavior intact.
  Report socket, transport, configuration, and feedback errors explicitly.
  Avoid changing the motor wire protocol without evidence and tests.
- Make hardware operation an explicit opt-in: the default bringup must not
  open CAN, enable motors, or issue commands. Launching the real driver
  requires a clearly named explicit hardware argument. Avoid sending a
  zero/default command before a valid command has been received. Define and
  implement a bounded, configurable stale-command policy at the driver
  boundary as well as joystick/arm-target freshness handling: a disconnected
  joystick, disabled target, stale target, lost feedback, or invalid input
  must not indefinitely repeat an old motion command. On expiry, stop sending
  stale commands and report the condition; do not silently claim the physical
  motor is stopped. Where appropriate send an explicit disable only if its
  semantics are established from the driver/protocol, and document remaining
  hardware-dependent behavior. Include recovery/re-enable behavior in tests
  and documentation. Do not choose physical travel/torque limits without
  validated robot specifications.
- Validate joystick message lengths, unknown IDs, finite numeric values, and
  relevant parameter ranges; log actionable errors without high-frequency
  spam. Only latch offsets from valid connected feedback, and make stale or
  disconnected feedback observable. Clearly document any safety-motivated
  changes from existing behavior.

### 4. Launch, configuration, and devcontainer

- Install launch and config assets through their respective packages. Provide a
  top-level launch with a hardware-free default and clearly separated,
  explicit real-hardware mode. In the hardware-free mode, offer a fake motor
  backend or mock nodes that exercise the actual mapper/controller ROS
  interfaces without CAN or physical joysticks. Real joystick nodes must have
  configurable device selection; missing devices must be reported rather
  than silently producing a misleading healthy stack.
- Keep the existing Jazzy devcontainer as the canonical development path.
  Install declared ROS dependencies, in particular `ros-jazzy-joy`, launch,
  message generation, C++/Python test tooling, and required build tools; add
  `can-utils`, `iproute2`, and any actually required hardware utilities.
  Prefer package manifests and `rosdep` for the dependency graph; pin to
  Jazzy and do not install dependencies at every container startup. Make
  rosdep initialization/update and dependency installation reproducible,
  reporting failures instead of suppressing them. Do not assume Docker is
  available in the execution environment.
- Preserve the workspace mount and non-root user behavior; make sure package
  discovery and shell sourcing work in a freshly rebuilt container. Review
  hard-coded GPU/group/device settings and provide a documented, portable
  development default with opt-in hardware access as needed. Host CAN
  configuration remains an explicit operator task; never automatically run
  the legacy `SetupCan.bash`, kill system processes, or modify host links.
- Retire or clearly mark obsolete legacy Docker/Compose/scripts and the
  standalone diagnostic mapper; ensure they cannot be mistaken for the
  canonical build/launch path. Keep historical sources recoverable.

### 5. Documentation and verification

- Replace the top-level README with the package map, interface/topic table,
  dependency and devcontainer rebuild instructions, clean build/source
  commands, hardware-free launch and synthetic Joy examples, parameter and
  namespace/remapping guidance, and troubleshooting. Document the
  `/arm_target` type change, joystick device access, SocketCAN host setup as
  operator-only, hardware opt-in, uncalibrated values, stale-command behavior,
  and the limits of software-only testing. Remove references to nonexistent
  packages and outdated Humble/legacy container commands.
- Add automated tests for message generation/imports and launch installation;
  mapper axis/trigger mapping, malformed input, and stale joystick handling;
  controller four-feedback gating, connected/disconnected feedback, offsets,
  disabled/stale input, mapping/gain, and all four round-robin IDs; and driver
  fake-transport startup, no pre-command output, valid commands, timeout,
  errors, and recovery. Include a ROS integration test that publishes synthetic
  `sensor_msgs/msg/Joy`, supplies fake feedback, and observes arm targets and
  motor commands without real hardware. Test the default launch does not
  instantiate or enable the real motor driver.
- From a clean workspace/overlay, verify at minimum:

  ```bash
  source /opt/ros/jazzy/setup.bash
  cd /home/ubuntu/colcon_ws
  colcon list
  rosdep check --from-paths src --ignore-src --rosdistro jazzy
  colcon build --symlink-install
  source install/setup.bash
  ros2 interface show continuum_msgs/msg/ArmTarget
  ros2 interface show continuum_msgs/msg/MotorMotionControl
  ros2 interface show continuum_msgs/msg/MotorFeedback
  colcon test
  colcon test-result --verbose
  ```

  Additionally run the installed hardware-free bringup and integration smoke
  test and verify launch assets/executables are discoverable from the install
  space. Rebuild the devcontainer and repeat dependency/build/test checks if
  container tooling is available. If unavailable, explicitly report that the
  image rebuild is unverified; do not claim it succeeded.
- Run no hardware tests automatically. If hardware is available and the user
  explicitly authorizes commissioning, document a separate operator-supervised
  checklist, including mechanical restraint, verified IDs/configuration,
  independent emergency stop, and safe observation of timeout behavior.
  Otherwise report real hardware, physical limits, and CAN behavior as
  unverified.

## Completion criteria

The top-level repository contains one trackable copy of every package and the
canonical devcontainer; clean discovery, rosdep, build, interface inspection,
automated tests, and hardware-free launch pass; existing motor message types
remain compatible; default launch cannot activate hardware; and all remaining
hardware or container validation gaps are reported explicitly.