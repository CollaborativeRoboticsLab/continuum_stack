from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory('continuum_bringup'), 'config', 'stack.yaml')
    namespace = LaunchConfiguration('namespace')
    enable_real_hardware = LaunchConfiguration('enable_real_hardware')
    use_joysticks = LaunchConfiguration('use_joysticks')
    stage_1_device = LaunchConfiguration('stage_1_device')
    stage_2_device = LaunchConfiguration('stage_2_device')

    return LaunchDescription([
        DeclareLaunchArgument(
            'namespace', default_value='continuum_stack',
            description='ROS namespace for all stack nodes and relative topics.'),
        DeclareLaunchArgument(
            'enable_real_hardware', default_value='true',
            description='Start the real CAN driver and enable motors at startup; '
                        'requires operator supervision.'),
        DeclareLaunchArgument(
            'use_joysticks', default_value='false',
            description='Start joy_node instances for the configured device IDs.'),
        DeclareLaunchArgument('stage_1_device', default_value='0'),
        DeclareLaunchArgument('stage_2_device', default_value='1'),
        Node(
            package='continuum_joystick_mapper',
            executable='joystick_mapper_node',
            name='dual_joystick_mapper',
            namespace=namespace,
            output='screen',
            parameters=[config],
        ),
        Node(
            package='continuum_arm_controller',
            executable='arm_controller_node',
            name='arm_controller_node',
            namespace=namespace,
            output='screen',
            parameters=[config],
        ),
        Node(
            package='continuum_bringup',
            executable='fake_motor_node',
            name='fake_motor_node',
            namespace=namespace,
            output='screen',
            parameters=[config],
            condition=UnlessCondition(enable_real_hardware),
        ),
        Node(
            package='continuum_carmy_motor_controller',
            executable='rs_motor_ros2_node',
            name='motor_controller_node',
            namespace=namespace,
            output='screen',
            parameters=[config, {'hardware_enabled': True}],
            condition=IfCondition(enable_real_hardware),
        ),
        Node(
            package='joy',
            executable='joy_node',
            name='joy_stage_1',
            namespace=namespace,
            output='screen',
            parameters=[{'device_id': stage_1_device}],
            remappings=[('joy', 'stage_1/joy')],
            condition=IfCondition(use_joysticks),
        ),
        Node(
            package='joy',
            executable='joy_node',
            name='joy_stage_2',
            namespace=namespace,
            output='screen',
            parameters=[{'device_id': stage_2_device}],
            remappings=[('joy', 'stage_2/joy')],
            condition=IfCondition(use_joysticks),
        ),
    ])