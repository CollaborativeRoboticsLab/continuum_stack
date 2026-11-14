import importlib.util
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext
from launch.conditions import IfCondition, UnlessCondition
from launch_ros.actions import Node


def load_stack_launch():
    launch_path = os.path.join(
        get_package_share_directory('continuum_bringup'),
        'launch', 'stack.launch.py')
    spec = importlib.util.spec_from_file_location('stack_launch', launch_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_launch_selects_fake_backend_without_starting_hardware():
    description = load_stack_launch().generate_launch_description()
    nodes = [entity for entity in description.entities
             if isinstance(entity, Node)]
    motor_node = next(
        node for node in nodes
        if node.node_package == 'continuum_carmy_motor_controller')
    fake_node = next(
        node for node in nodes
        if node.node_package == 'continuum_bringup'
        and node.node_executable == 'fake_motor_node')

    context = LaunchContext()
    context.launch_configurations['enable_real_hardware'] = 'false'

    assert isinstance(motor_node.condition, IfCondition)
    assert isinstance(fake_node.condition, UnlessCondition)
    assert not motor_node.condition.evaluate(context)
    assert fake_node.condition.evaluate(context)