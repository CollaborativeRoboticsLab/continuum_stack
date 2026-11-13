#!/usr/bin/env python3

import math
import time

import rclpy
from continuum_msgs.msg import ArmTarget, MotorFeedback, MotorMotionControl
from rclpy.node import Node


MOTOR_TARGETS = (
    (3, 'stage_2_x_angle', 'stage_2_x'),
    (2, 'stage_1_y_angle', 'stage_1_y'),
    (1, 'stage_1_x_angle', 'stage_1_x'),
    (4, 'stage_2_y_angle', 'stage_2_y'),
)


class ArmControllerNode(Node):
    def __init__(self):
        super().__init__('arm_controller_node')
        self.declare_parameter('gain', math.pi * 3 * 1.5)
        self.declare_parameter('kp', 10.0)
        self.declare_parameter('kd', 1.0)
        self.declare_parameter('target_timeout_sec', 0.5)
        self.declare_parameter('feedback_timeout_sec', 0.5)
        self.declare_parameter('command_period_sec', 0.0125)
        self.declare_parameter('arm_target_topic', 'arm_target')
        self.declare_parameter('motor_feedback_topic', 'motor_feedback')
        self.declare_parameter('motion_control_topic', 'motion_control')

        self.gain = float(self.get_parameter('gain').value)
        self.kp = float(self.get_parameter('kp').value)
        self.kd = float(self.get_parameter('kd').value)
        self.target_timeout_sec = float(
            self.get_parameter('target_timeout_sec').value)
        self.feedback_timeout_sec = float(
            self.get_parameter('feedback_timeout_sec').value)
        command_period_sec = float(
            self.get_parameter('command_period_sec').value)
        if not all(math.isfinite(value) for value in (
                self.gain, self.kp, self.kd, self.target_timeout_sec,
                self.feedback_timeout_sec, command_period_sec)):
            raise ValueError('controller parameters must be finite')
        if min(self.target_timeout_sec, self.feedback_timeout_sec,
               command_period_sec) <= 0 or self.kp < 0 or self.kd < 0:
            raise ValueError('timeouts/period must be positive and gains non-negative')

        self.target = None
        self.target_received = None
        self.feedback = {motor_id: None for motor_id, _, _ in MOTOR_TARGETS}
        self.homing_offsets = {name: None for _, _, name in MOTOR_TARGETS}
        self.next_motor = 0
        self.last_wait_reason = None

        self.target_sub = self.create_subscription(
            ArmTarget, str(self.get_parameter('arm_target_topic').value),
            self.handle_arm_target, 10)
        self.motor_feedback_sub = self.create_subscription(
            MotorFeedback, str(self.get_parameter('motor_feedback_topic').value),
            self.handle_motor_feedback, 10)
        self.motor_pub = self.create_publisher(
            MotorMotionControl,
            str(self.get_parameter('motion_control_topic').value), 10)
        self.timer = self.create_timer(command_period_sec, self.publish_motor_commands)

    def handle_arm_target(self, msg):
        values = (
            msg.stage_1_x_angle, msg.stage_1_y_angle,
            msg.stage_2_x_angle, msg.stage_2_y_angle, msg.gripper)
        if not all(math.isfinite(value) for value in values):
            self.target = None
            self.target_received = None
            self._warn_once('invalid_target', 'Ignoring non-finite arm target')
            return
        self.target = msg
        self.target_received = time.monotonic()
        self.last_wait_reason = None

    def handle_motor_feedback(self, msg):
        if msg.motor_id not in self.feedback:
            self._warn_once(
                f'unknown_motor_{msg.motor_id}',
                f'Ignoring feedback for unknown motor ID {msg.motor_id}')
            return
        values = (msg.position, msg.velocity, msg.torque, msg.temperature)
        if not all(math.isfinite(value) for value in values):
            self.feedback[msg.motor_id] = None
            self.homing_offsets[MOTOR_TARGETS[
                next(i for i, target in enumerate(MOTOR_TARGETS)
                     if target[0] == msg.motor_id)][2]] = None
            self._warn_once(
                f'invalid_feedback_{msg.motor_id}',
                f'Ignoring non-finite feedback for motor {msg.motor_id}')
            return

        received = time.monotonic()
        self.feedback[msg.motor_id] = (msg, received)
        _, _, motor_name = next(
            target for target in MOTOR_TARGETS if target[0] == msg.motor_id)
        if not msg.connected:
            self.homing_offsets[motor_name] = None
            self._warn_once(
                f'disconnected_{msg.motor_id}',
                f'Motor {msg.motor_id} reports disconnected')
        elif self.homing_offsets[motor_name] is None:
            self.homing_offsets[motor_name] = msg.position

    def publish_motor_commands(self):
        now = time.monotonic()
        reason = None
        if self.target is None or self.target_received is None:
            reason = 'waiting for a valid arm target'
        elif now - self.target_received > self.target_timeout_sec:
            reason = 'arm target is stale'
        elif not self.target.enabled:
            reason = 'arm target is disabled'
        else:
            for motor_id, _, motor_name in MOTOR_TARGETS:
                sample = self.feedback[motor_id]
                if sample is None:
                    reason = f'waiting for connected feedback from motor {motor_id}'
                    break
                msg, received = sample
                if not msg.connected:
                    reason = f'motor {motor_id} is disconnected'
                    break
                if now - received > self.feedback_timeout_sec:
                    reason = f'feedback from motor {motor_id} is stale'
                    break
                if self.homing_offsets[motor_name] is None:
                    reason = f'waiting for a valid offset from motor {motor_id}'
                    break

        if reason is not None:
            self._warn_once(reason, reason.capitalize())
            return

        self.last_wait_reason = None
        motor_id, field_name, motor_name = MOTOR_TARGETS[self.next_motor]
        position = (
            getattr(self.target, field_name) * self.gain
            + self.homing_offsets[motor_name])
        command = MotorMotionControl(
            motor_id=motor_id,
            position=position,
            velocity=0.0,
            kp=self.kp,
            kd=self.kd,
            torque=0.0)
        self.motor_pub.publish(command)
        self.next_motor = (self.next_motor + 1) % len(MOTOR_TARGETS)

    def _warn_once(self, reason, message):
        if self.last_wait_reason != reason:
            self.get_logger().warning(message)
            self.last_wait_reason = reason


def main(args=None):
    rclpy.init(args=args)
    node = ArmControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
