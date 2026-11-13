from setuptools import find_packages, setup

package_name = 'continuum_joystick_mapper'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/joystick_launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='TODO: Set project maintainer',
    maintainer_email='maintainer@example.invalid',
    description='Maps raw joystick input into arm-level goal commands for the arm controller.',
    license='TODO: Confirm project license',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'joystick_mapper_node = joystick_mapper.joystick_mapper_node:main'
        ],
    },
)
