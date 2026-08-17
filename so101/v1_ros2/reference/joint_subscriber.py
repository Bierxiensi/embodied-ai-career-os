"""ROS2 SO101 关节控制 Subscriber：订阅 /joint_commands 并打印关节角度。

运行前提：
  1. 已安装 ROS2 Humble
  2. 已 source ROS2 环境

运行方式（新终端）：
  python3 joint_subscriber.py

预期输出（配合 joint_publisher.py）：
  [INFO] [joint_subscriber]: 收到关节命令: [0.0, 0.0, 0.0, 0.0] rad
    关节 0: 0.0° | 关节 1: 0.0° | 关节 2: 0.0° | 关节 3: 0.0°
  [INFO] [joint_subscriber]: 收到关节命令: [0.524, -0.524, 0.524, 1.047] rad
    关节 0: 30.0° | 关节 1: -30.0° | 关节 2: 30.0° | 关节 3: 60.0°
  ...
"""

import math

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray


class JointSubscriber(Node):
    """订阅 /joint_commands 并打印关节角度。"""

    def __init__(self):
        super().__init__("joint_subscriber")
        # Subscriber：消息类型 Float64MultiArray，topic /joint_commands
        self.subscription = self.create_subscription(
            Float64MultiArray,
            "joint_commands",
            self.joint_callback,
            10,
        )

    def joint_callback(self, msg: Float64MultiArray):
        """收到关节命令时的回调。"""
        self.get_logger().info(
            f"收到关节命令: [{', '.join(f'{x:.3f}' for x in msg.data)}] rad"
        )

        # 转换为度数并逐关节打印
        degrees = [math.degrees(rad) for rad in msg.data]
        for i, deg in enumerate(degrees):
            print(f"  关节 {i}: {deg:.1f}°", end=" | ")
        print()  # 换行


def main(args=None):
    rclpy.init(args=args)
    node = JointSubscriber()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
