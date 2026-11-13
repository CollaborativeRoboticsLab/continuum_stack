#!/usr/bin/env python3

import math

import rclpy
from continuum_msgs.msg import MotorFeedback, MotorMotionControl
from rclpy.node import Node


class FakeMotorNode(Node):
    def __init__(self):
        super().__init__('fake_motor_node')
        self.declare_parameter('motor_ids', [1, 2, 3, 4])
        self.declare_parameter('feedback_rate_hz', 20.0)
        self.declare_parameter('motor_feedback_topic', 'motor_feedback')
        self.declare_parameter('motion_control_topic', 'motion_control')

        motor_ids = [int(value) for value in
                     self.get_parameter('motor_ids').value]
        rate = float(self.get_parameter('feedback_rate_hz').value)
        if not motor_ids or len(set(motor_ids)) != len(motor_ids):
            raise ValueError('motor_ids must be a non-empty unique list')
        if any(motor_id < 1 or motor_id > 255 for motor_id in motor_ids):
            raise ValueError('motor_ids must be in the range 1..255')
        if not math.isfinite(rate) or rate <= 0.0:
            raise ValueError('feedback_rate_hz must be finite and positive')

        self.motor_ids = motor_ids
        self.feedback_pub = self.create_publisher(
            MotorFeedback,
            str(self.get_parameter('motor_feedback_topic').value), 10)
        self.command_sub = self.create_subscription(
            MotorMotionControl,
            str(self.get_parameter('motion_control_topic').value),
            self.handle_command, 10)
        self.feedback_timer = self.create_timer(1.0 / rate, self.publish_feedback)

    def handle_command(self, command):
        if command.motor_id not in self.motor_ids:
            self.get_logger().warning(
                f'Ignoring command for unconfigured motor {command.motor_id}')
            return
        values = (command.position, command.velocity, command.kp,
                  command.kd, command.torque)
        if not all(math.isfinite(value) for value in values):
            self.get_logger().warning(
                f'Ignoring non-finite command for motor {command.motor_id}')
            return
        self.get_logger().info(
            f'Received synthetic command for motor {command.motor_id}: '
            f'position={command.position:.4f}')

    def publish_feedback(self):
        for motor_id in self.motor_ids:
            self.feedback_pub.publish(MotorFeedback(
                motor_id=motor_id,
                connected=True,
                position=0.0,
                velocity=0.0,
                torque=0.0,
                temperature=0.0,
            ))


def main(args=None):
    rclpy.init(args=args)
    node = FakeMotorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()