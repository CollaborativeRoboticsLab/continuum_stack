# Refactoring Map

This document maps the two source projects to the canonical ROS 2 Jazzy
packages and calls out changes that affect contributors or downstream clients.
It does not replace the original project history or assign individual
authorship.

## Source Projects

The source checkouts identify these upstream repositories:

- [capstone-continuum-arm-joysticks](https://github.com/CollaborativeRoboticsLab/capstone-continuum-arm-joysticks)
- [capstone-continuum-arm-Robstride-EduLite05-ROS2-Control](https://github.com/CollaborativeRoboticsLab/capstone-continuum-arm-Robstride-EduLite05-ROS2-Control)

## What Went Where

| Original source | Canonical destination | Notes |
| --- | --- | --- |
| Joystick repo `src/joystick_mapper/` | `continuum_joystick_mapper/` | Package metadata, Python node, resource marker, launch file, and lint tests were migrated. The executable remains `joystick_mapper_node`; Python module remains `joystick_mapper`. |
| Joystick repo `src/arm_controller/` | `continuum_arm_controller/` | Package metadata, Python node, resource marker, and executable entry point were migrated. The Python module remains `arm_controller`. |
| Motor repo `carmy_motor_controller/` | `continuum_carmy_motor_controller/` | CMake package, driver source, and headers were migrated. The executable remains `rs_motor_ros2_node`. |
| Motor repo `carmy_motor_controller/msg/` | `continuum_msgs/msg/` | `MotorFeedback.msg` and `MotorMotionControl.msg` moved here with their definitions unchanged. |
| No existing source file | `continuum_msgs/msg/ArmTarget.msg` | Adds the missing arm target interface inferred from the Python consumers. |
| No existing source file | `continuum_bringup/` | Adds the assembled launch, shared YAML parameters, and a synthetic motor feedback/command backend for hardware-free exercises. |

The root `README.md` describes the clean build and bringup workflow. The
canonical development container is `.devcontainer/`. Legacy compose files,
host CAN setup scripts, startup scripts, and the standalone diagnostic mapper
remain only in the preserved source checkouts; they are not the canonical path
and were not run as part of this refactor.

## Interface And Name Changes

- ROS package names are now `continuum_msgs`,
	`continuum_carmy_motor_controller`, `continuum_joystick_mapper`,
	`continuum_arm_controller`, and `continuum_bringup`. The mapper and arm
	controller executable names and Python module names remain unchanged.
- Motor messages keep their original definitions: `MotorFeedback.msg` and
	`MotorMotionControl.msg` are byte-for-byte identical to the source files.
	Their generated ROS types now live in `continuum_msgs/msg/`. Downstream ROS
	clients must update package-qualified imports and dependencies from
	`continuum_carmy_motor_controller` to `continuum_msgs`.
- `/arm_target` now uses `continuum_msgs/msg/ArmTarget`. The old Python
	consumers referred to `carmy_motor_controller/msg/ArmTarget`, but that
	message was absent from the source package. The new interface is inferred
	from those consumers, not recovered from an upstream definition. Its four
	stage fields currently represent normalized joystick values, not calibrated
	radians; `gripper` and `mode` remain placeholders.
- The dedicated `continuum_msgs` package currently contains only message
	definitions. No `.srv` or `.action` definitions existed in the supplied
	repositories; add future services and actions here rather than to a driver
	or application package.
- The C++ header include path is now
	`continuum_carmy_motor_controller/motor_cfg.h`, matching the migrated header
	directory. The CMake target uses C++17 and Jazzy's rosidl typesupport target
	linkage.
- The assembled launch defaults to namespace `/continuum_stack`; pass
	`namespace:=...` to change it. Relative topic defaults remain
	`stage_1/joy`, `stage_2/joy`, `arm_target`, `motor_feedback`, and
	`motion_control` within that namespace.

## Runtime Changes

- The driver has an explicit `hardware_enabled` parameter which defaults to
	false. The default bringup starts the fake backend, not the CAN driver; the
	real driver is only selected with `enable_real_hardware:=true`.
- The fake backend publishes connected feedback for IDs 1-4 and logs accepted
	motion messages. It is an interface exercise, not a motor or transport
	simulator.
- Mapper/controller validation and freshness gates reject malformed, disabled,
	disconnected, or stale inputs. The driver expires stale commands and stops
	repeating motion frames until a fresh command arrives. This does not prove a
	physical motor stopped; no physical limits, verified home procedure, or
	functional-safety claim is introduced.
- The existing gain and first-connected-feedback offset are retained as
	defaults, but remain uncalibrated. First feedback is not treated as a
	verified home position.

## Contributor Notes

Please preserve the source projects' copyright and license notices when
changing migrated files. No new license or individual maintainer identity has
been inferred here. For future changes, make edits in the canonical package
directories above and update this map if source ownership, public interfaces,
or package destinations change. Keep the preserved checkouts untouched unless
the original project history itself needs an update.
