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

# TODO: 你来实现
# 提示：
# 1. from launch import LaunchDescription
# 2. from launch_ros.actions import Node
# 3. 创建 generate_launch_description 函数
# 4. 返回 LaunchDescription 包含两个 Node


def generate_launch_description():
    """生成 Launch 描述：启动 Publisher 和 Subscriber 两个节点。"""
    # TODO: 你来实现
    # 提示：
    # 1. return LaunchDescription([
    #        Node(
    #            package="so101_v1",
    #            executable="joint_publisher",
    #            name="joint_publisher",
    #            output="screen",
    #        ),
    #        Node(
    #            package="so101_v1",
    #            executable="joint_subscriber",
    #            name="joint_subscriber",
    #            output="screen",
    #        ),
    #    ])
    raise NotImplementedError("请实现 generate_launch_description")


if __name__ == "__main__":
    # 直接运行时，打印提示
    print("请使用 ros2 launch 命令运行：")
    print("  ros2 launch so101_v1 demo_launch.py")
    print()
    print("或者手动在两个终端分别运行：")
    print("  终端1: python3 joint_publisher.py")
    print("  终端2: python3 joint_subscriber.py")
