import importlib.util
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext
from launch.actions import (
    DeclareLaunchArgument, GroupAction, IncludeLaunchDescription,
    SetLaunchConfiguration,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.utilities import perform_substitutions
from launch_ros.actions import Node


def load_launch(filename):
    launch_path = os.path.join(
        get_package_share_directory('continuum_bringup'),
        'launch', filename)
    spec = importlib.util.spec_from_file_location('bringup_launch', launch_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def backend_nodes(description):
    nodes = [entity for entity in description.entities
             if isinstance(entity, Node)]
    return (
        next(node for node in nodes
             if node.node_package == 'continuum_carmy_motor_controller'),
        next(node for node in nodes
             if node.node_package == 'continuum_bringup'
             and node.node_executable == 'fake_motor_node'),
    )


def test_default_launch_selects_hardware_without_starting_nodes():
    assert importlib.util.find_spec(
        'continuum_bringup.fake_motor_node') is not None

    description = load_launch('stack.launch.py').generate_launch_description()
    motor_node, fake_node = backend_nodes(description)
    argument = next(entity for entity in description.entities
                    if isinstance(entity, DeclareLaunchArgument)
                    and entity.name == 'enable_real_hardware')
    context = LaunchContext()
    assert perform_substitutions(context, argument.default_value) == 'true'
    argument.execute(context)

    assert isinstance(motor_node.condition, IfCondition)
    assert isinstance(fake_node.condition, UnlessCondition)
    assert motor_node.condition.evaluate(context)
    assert not fake_node.condition.evaluate(context)


def test_fake_launch_overrides_inherited_hardware_setting():
    description = load_launch('fake.launch.py').generate_launch_description()
    group = next(entity for entity in description.entities
                 if isinstance(entity, GroupAction))
    include = next(entity for entity in group.get_sub_entities()
                   if isinstance(entity, IncludeLaunchDescription))
    context = LaunchContext()
    context.launch_configurations['enable_real_hardware'] = 'true'
    actions = include.execute(context)
    for action in actions:
        if isinstance(action, SetLaunchConfiguration):
            action.execute(context)

    stack = load_launch('stack.launch.py').generate_launch_description()
    argument = next(entity for entity in stack.entities
                    if isinstance(entity, DeclareLaunchArgument)
                    and entity.name == 'enable_real_hardware')
    argument.execute(context)
    motor_node, fake_node = backend_nodes(stack)
    assert context.launch_configurations['enable_real_hardware'] == 'false'
    assert not motor_node.condition.evaluate(context)
    assert fake_node.condition.evaluate(context)