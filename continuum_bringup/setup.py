from glob import glob
from setuptools import find_packages, setup

package_name = 'continuum_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='TODO: Set project maintainer',
    maintainer_email='maintainer@example.invalid',
    description='Hardware-free and operator-enabled stack bringup.',
    license='TODO: Confirm project license',
    entry_points={
        'console_scripts': [
            'fake_motor_node = continuum_bringup.fake_motor_node:main',
        ],
    },
)