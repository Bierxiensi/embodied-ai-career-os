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

# TODO: 你来实现
# 提示：
# 1. import rclpy 和 Node
# 2. import std_msgs.msg.Float64MultiArray
# 3. 创建 JointSubscriber 类继承 Node
# 4. 在 __init__ 中创建 subscription
# 5. 实现 joint_callback 处理关节命令


class JointSubscriber:
    """订阅 /joint_commands 并打印关节角度。"""

    def __init__(self):
        # TODO: 你来实现
        # 提示：
        # 1. super().__init__("joint_subscriber")
        # 2. self.subscription = self.create_subscription(
        #        Float64MultiArray,
        #        "joint_commands",
        #        self.joint_callback,
        #        10,
        #    )
        raise NotImplementedError("请实现 JointSubscriber.__init__")

    def joint_callback(self, msg):
        """收到关节命令时的回调。"""
        # TODO: 你来实现
        # 提示：
        # 1. 打印日志：收到关节命令
        # 2. 转换为度数：degrees = [math.degrees(rad) for rad in msg.data]
        # 3. 逐关节打印：关节 0: 30.0° | 关节 1: -30.0° | ...
        raise NotImplementedError("请实现 joint_callback")


def main(args=None):
    # TODO: 你来实现
    # 提示：和 simple_subscriber.py 的 main 类似
    raise NotImplementedError("请实现 main")


if __name__ == "__main__":
    main()
