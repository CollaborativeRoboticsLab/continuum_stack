import time

from continuum_joystick_mapper.joystick_mapper_node import DualJoystickMapper
import pytest
import rclpy
from sensor_msgs.msg import Joy


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
def mapper():
    node = DualJoystickMapper()
    node.arm_target_pub = CapturingPublisher()
    yield node
    node.destroy_node()


def joy(axes=None, buttons=None):
    message = Joy()
    message.axes = axes if axes is not None else [0.0, 0.0, 0.0, 0.0]
    message.buttons = buttons if buttons is not None else [0]
    return message


def test_maps_axes_and_or_enables_from_either_stage(mapper):
    mapper._joy_callback('stage_1', joy([0.25, -0.5, 0.75, 0.0], [0]))
    mapper._joy_callback('stage_2', joy([-0.2, 0.4, 0.6, 0.0], [1]))

    mapper.publish_arm_target()
    target = mapper.arm_target_pub.messages[-1]

    assert target.stage_1_x_angle == pytest.approx(0.25)
    assert target.stage_1_y_angle == pytest.approx(-0.5)
    assert target.stage_2_x_angle == pytest.approx(-0.2)
    assert target.stage_2_y_angle == pytest.approx(0.4)
    assert target.enabled


def test_malformed_joy_disables_that_stage(mapper):
    mapper._joy_callback('stage_1', joy([0.1], [1]))
    mapper.publish_arm_target()

    assert not mapper.arm_target_pub.messages[-1].enabled
    assert mapper.stages['stage_1']['received'] is None


def test_stale_joy_is_not_forwarded_as_enabled(mapper):
    mapper._joy_callback('stage_1', joy(buttons=[1]))
    mapper.stages['stage_1']['received'] = time.monotonic() - 1.0
    mapper.publish_arm_target()

    target = mapper.arm_target_pub.messages[-1]
    assert not target.enabled
    assert target.stage_1_x_angle == 0.0
    assert target.stage_1_y_angle == 0.0
