import math

import rclpy
from continuum_arm_controller.arm_controller_node import (
    ArmControllerNode, MOTOR_TARGETS)
from continuum_msgs.msg import ArmTarget, MotorFeedback
import pytest


class CapturingPublisher:
    def __init__(self):
        self.messages = []

    def publish(self, message):
        self.messages.append(message)


@pytest.fixture(scope='module', autouse=True)
def rclpy_context():
    rclpy.init()
    yield
    rclpy.shutdown()


@pytest.fixture
def controller():
    node = ArmControllerNode()
    node.motor_pub = CapturingPublisher()
    yield node
    node.destroy_node()


def connected_feedback(motor_id, position=0.0):
    return MotorFeedback(
        motor_id=motor_id,
        connected=True,
        position=position,
        velocity=0.0,
        torque=0.0,
        temperature=25.0,
    )


def enabled_target():
    return ArmTarget(
        stage_1_x_angle=0.2,
        stage_1_y_angle=-0.3,
        stage_2_x_angle=0.4,
        stage_2_y_angle=-0.5,
        gripper=0.0,
        mode=0,
        enabled=True,
    )


def test_waits_until_all_four_motors_have_connected_feedback(controller):
    controller.handle_arm_target(enabled_target())
    for motor_id, _, _ in MOTOR_TARGETS[:3]:
        controller.handle_motor_feedback(connected_feedback(motor_id))

    controller.publish_motor_commands()

    assert controller.motor_pub.messages == []


def test_maps_gain_offsets_and_round_robins_all_motor_ids(controller):
    offsets = {motor_id: 10.0 + motor_id for motor_id, _, _ in MOTOR_TARGETS}
    for motor_id, _, _ in MOTOR_TARGETS:
        controller.handle_motor_feedback(
            connected_feedback(motor_id, offsets[motor_id]))
    controller.handle_arm_target(enabled_target())

    for _ in range(4):
        controller.publish_motor_commands()

    commands = controller.motor_pub.messages
    assert [command.motor_id for command in commands] == [3, 2, 1, 4]
    for command, (_, field_name, motor_name) in zip(commands, MOTOR_TARGETS):
        target_value = getattr(controller.target, field_name)
        motor_id = command.motor_id
        assert command.position == pytest.approx(
            target_value * controller.gain + offsets[motor_id])
        assert controller.homing_offsets[motor_name] == offsets[motor_id]


@pytest.mark.parametrize('enabled', [False, True])
def test_disabled_or_disconnected_input_does_not_publish(controller, enabled):
    for motor_id, _, _ in MOTOR_TARGETS:
        controller.handle_motor_feedback(connected_feedback(motor_id))
    target = enabled_target()
    target.enabled = enabled
    controller.handle_arm_target(target)
    if enabled:
        controller.handle_motor_feedback(MotorFeedback(
            motor_id=3, connected=False, position=0.0, velocity=0.0,
            torque=0.0, temperature=0.0))

    controller.publish_motor_commands()

    assert controller.motor_pub.messages == []


def test_non_finite_target_is_rejected(controller):
    target = enabled_target()
    target.stage_1_x_angle = math.nan
    controller.handle_arm_target(target)
    controller.publish_motor_commands()

    assert controller.target is None
    assert controller.motor_pub.messages == []