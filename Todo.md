# Continuum stack review and remaining work

## Review status

The refactor introduces separate interface, mapper, controller, motor driver,
and bringup packages, with a fake backend and a hardware-default stack launch.
This review covers commit `f9f44a7` and the uncommitted changes present at
review time; the session history did not identify a separate GPT Luna change
set. The observations below are historical; see [the student handover](docs/next_steps.md)
for the current priorities.

- A clean, isolated ROS Jazzy build completed for all five packages. The
  existing tests reported 12 tests, no failures or errors, and one skipped.
- Package discovery found exactly the five expected packages. `rosdep check`
  could not complete because the current user's rosdep database was not
  initialized/updated.
- The installed default launch failed the hardware-free smoke test:
  `fake_motor_node` exited with `ModuleNotFoundError: No module named
  'continuum_bringup'`, so no motor feedback or commands were observed.
- The container image was not rebuilt in this environment. No CAN hardware,
  motors, or physical joysticks were tested.

## Priority 1: bringup, feedback, and command behavior

- [ ] Add a clean-install launch test for the fake backend and a synthetic
  joystick-to-command smoke test. The missing Python package initializer has
  been added and fake feedback has been observed in a standalone smoke test.
- [ ] Extend stale-feedback coverage. The driver now tracks valid status frame
  freshness and distinguishes timeouts from receive errors, with focused
  freshness tests. Add hardware-free tests for valid, timed-out, unrelated,
  malformed, and recovered frames and transport errors.
- [ ] Make driver timing and command expiry verifiable. The driver performs
  synchronous receive operations with a 50 ms timeout, including during
  sends and sequential feedback polling, on its executor thread. Measure and
  bound the effect on command processing and expiry across all motors; avoid
  blocking the watchdog on CAN reads. Test expiry and recovery with a fake
  transport and a controlled clock, including missing or delayed feedback.
  Expiry currently stops repeated frames, not necessarily physical motion.
- [ ] Refactor the real driver behind an injectable CAN transport and surface
  read/write errors rather than treating receive errors as timeouts or merely
  printing write failures. Test disabled startup, no pre-command motion,
  valid and invalid commands, transport failures, timeout, and recovery
  without opening CAN or enabling motors.
- [ ] Decide and test the behavior when only one joystick becomes stale or
  malformed while the other remains enabled. The current
  [mapper](continuum_joystick_mapper/continuum_joystick_mapper/joystick_mapper_node.py)
  substitutes zero for the failed stage while retaining the other stage's
  enable, so the controller can command the failed stage toward its offset.
  Document the approved behavior; do not assume zero is a safe position.
- [ ] Validate the controller's offset and recovery policy after stale
  feedback and reconnection, including whether re-latching an offset is
  appropriate. Add tests for stale target/feedback, non-finite feedback,
  reconnection, and the full disabled-to-enabled transition.

## Priority 2: reproducible development and integration

- [ ] Rebuild and verify the devcontainer on a supported host. The current
  [configuration](.devcontainer/devcontainer.json) requests privileged mode,
  host networking, all GPUs, and `/dev` by default, as described in
  [README.md](README.md). Provide an opt-in hardware configuration and a
  portable default. Check bind mounts on hosts
  without an existing `.bash_history`.
- [ ] Verify the [Dockerfile](.devcontainer/Dockerfile) works on a clean image:
  rosdep initialization is assumed and Cyclone DDS is now explicitly
  installed but has not been verified in a rebuilt image. Confirm non-root UID
  handling, workspace permissions, dependency
  installation, and overlay sourcing after a rebuild.
- [ ] Add an automated installed-launch integration test that publishes
  synthetic joystick messages, observes enabled arm targets and commands for
  all four motors, verifies the fake backend and absence of the real
  driver, and exercises stale input and recovery. The existing
  [launch test](continuum_bringup/test/test_stack_launch.py) checks launch
  conditions only; it does not launch the ROS graph.
- [ ] Update or retire the legacy
  [joystick launch](continuum_joystick_mapper/launch/joystick_launch.py):
  it silently skips missing devices and uses absolute remappings, unlike the
  configurable, namespace-aware stack launch.
- [ ] Verify rosdep from a fresh initialized database, then repeat discovery,
  clean build, interface inspection, tests, and the hardware-free launch in
  the rebuilt container. Investigate the skipped test and lint warnings.

## Priority 3: documentation and project hygiene

- [ ] Confirm the original source checkouts and Git histories remain
  recoverable outside colcon discovery, and document their actual location.
  Resolve the placeholder maintainer and license metadata with the project
  owners; do not invent either.
- [ ] Stop tracking generated colcon logs and ensure the repository ignore
  rules cover generated `log/` files. Preserve any unrelated user changes.
- [ ] Before any real-hardware operation, separately commission with an
  authorized operator: validate CAN communication, IDs/types, calibration,
  offsets, limits and timeout behavior with mechanical restraint and an
  independent emergency stop. The fake backend is not a dynamics or safety
  simulator; no physical stopping guarantee has been established.