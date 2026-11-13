#!/usr/bin/env python3

import math
import time

from continuum_msgs.msg import ArmTarget
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy


class DualJoystickMapper(Node):
    def __init__(self):
        super().__init__('dual_joystick_mapper')

        self.declare_parameter('stale_timeout_sec', 0.5)
        self.declare_parameter('x_axis', 0)
        self.declare_parameter('y_axis', 1)
        self.declare_parameter('z_axis', 2)
        self.declare_parameter('knob_axis', 3)
        self.declare_parameter('enable_button', 0)
        self.declare_parameter('stage_1_topic', 'stage_1/joy')
        self.declare_parameter('stage_2_topic', 'stage_2/joy')
        self.declare_parameter('arm_target_topic', 'arm_target')
        self.declare_parameter('dashboard', False)

        self.stale_timeout_sec = float(
            self.get_parameter('stale_timeout_sec').value)
        if not math.isfinite(self.stale_timeout_sec) or self.stale_timeout_sec <= 0:
            raise ValueError('stale_timeout_sec must be a finite positive value')

        self.axes = {
            name: int(self.get_parameter(f'{name}_axis').value)
            for name in ('x', 'y', 'z', 'knob')
        }
        self.enable_button = int(
            self.get_parameter('enable_button').value)
        if any(index < 0 for index in self.axes.values()) or self.enable_button < 0:
            raise ValueError('axis and button indices must be non-negative')

        self.stages = {
            name: {'values': [0.0, 0.0, 0.0], 'trigger': False, 'received': None}
            for name in ('stage_1', 'stage_2')
        }
        self.mode = 0

        self.sub_stage_1 = self.create_subscription(
            Joy, str(self.get_parameter('stage_1_topic').value),
            lambda msg: self._joy_callback('stage_1', msg), 10)
        self.sub_stage_2 = self.create_subscription(
            Joy, str(self.get_parameter('stage_2_topic').value),
            lambda msg: self._joy_callback('stage_2', msg), 10)
        self.arm_target_pub = self.create_publisher(
            ArmTarget, str(self.get_parameter('arm_target_topic').value), 10)
        self.publish_timer = self.create_timer(0.1, self.publish_arm_target)
        self.dashboard_timer = None
        if bool(self.get_parameter('dashboard').value):
            self.dashboard_timer = self.create_timer(1.0, self.print_dashboard)

    def _joy_callback(self, stage_name, msg):
        required_axes = max(self.axes.values())
        if len(msg.axes) <= required_axes or len(msg.buttons) <= self.enable_button:
            self.get_logger().warning(
                f'{stage_name} joystick message is missing configured axes/buttons')
            self.stages[stage_name]['trigger'] = False
            self.stages[stage_name]['received'] = None
            return

        selected_axes = [msg.axes[self.axes[key]] for key in ('x', 'y', 'z')]
        if not all(math.isfinite(value) for value in selected_axes):
            self.get_logger().warning(
                f'{stage_name} joystick message contains non-finite axes')
            self.stages[stage_name]['trigger'] = False
            self.stages[stage_name]['received'] = None
            return

        state = self.stages[stage_name]
        state['values'] = selected_axes
        state['trigger'] = bool(msg.buttons[self.enable_button])
        state['received'] = time.monotonic()

    def publish_arm_target(self):
        now = time.monotonic()
        fresh = {
            name: state['received'] is not None
            and now - state['received'] <= self.stale_timeout_sec
            for name, state in self.stages.items()
        }
        target = ArmTarget()
        for stage_name in ('stage_1', 'stage_2'):
            values = self.stages[stage_name]['values'] if fresh[stage_name] else [0.0] * 3
            setattr(target, f'{stage_name}_x_angle', values[0])
            setattr(target, f'{stage_name}_y_angle', values[1])
        target.gripper = 0.0
        target.mode = self.mode
        target.enabled = any(
            fresh[name] and state['trigger']
            for name, state in self.stages.items())
        self.arm_target_pub.publish(target)

    def print_dashboard(self):
        now = time.monotonic()
        labels = []
        for name, state in self.stages.items():
            active = (state['received'] is not None
                      and now - state['received'] <= self.stale_timeout_sec)
            x, y, z = state['values'] if active else (0.0, 0.0, 0.0)
            labels.append(
                f'{name}: X={x:+.2f} Y={y:+.2f} Z={z:+.2f} '
                f'enable={active and state["trigger"]}')
        self.get_logger().info(' | '.join(labels))


def main(args=None):
    rclpy.init(args=args)
    node = DualJoystickMapper()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
