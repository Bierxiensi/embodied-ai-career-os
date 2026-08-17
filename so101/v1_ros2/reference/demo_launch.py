"""ROS2 Launch 文件：同时启动 joint_publisher 和 joint_subscriber。

运行前提：
  1. 已安装 ROS2 Humble
  2. 已 source ROS2 环境

运行方式：
  python3 demo_launch.py

预期输出：
  [INFO] [joint_publisher]: 发送关节角度: [0.0, 0.0, 0.0, 0.0] rad
  [INFO] [joint_subscriber]: 收到关节命令: [0.0, 0.0, 0.0, 0.0] rad
    关节 0: 0.0° | 关节 1: 0.0° | 关节 2: 0.0° | 关节 3: 0.0°
  ...
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """生成 Launch 描述：启动 Publisher 和 Subscriber 两个节点。"""
    return LaunchDescription([
        # 启动 joint_publisher 节点
        Node(
            package="so101_v1",
            executable="joint_publisher",
            name="joint_publisher",
            output="screen",
        ),
        # 启动 joint_subscriber 节点
        Node(
            package="so101_v1",
            executable="joint_subscriber",
            name="joint_subscriber",
            output="screen",
        ),
    ])
