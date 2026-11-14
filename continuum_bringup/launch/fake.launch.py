import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import GroupAction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    stack_launch = os.path.join(
        get_package_share_directory('continuum_bringup'),
        'launch', 'stack.launch.py')
    return LaunchDescription([
        GroupAction(scoped=True, actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(stack_launch),
                launch_arguments={'enable_real_hardware': 'false'}.items(),
            ),
        ]),
    ])