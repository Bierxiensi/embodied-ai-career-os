"""ROS2 简单 Subscriber 示例：订阅 /chatter topic 打印消息。

运行前提：已安装 ROS2 Humble（Ubuntu 22.04 或 WSL2）

运行方式（新终端）：
  source /opt/ros/humble/setup.bash
  python3 simple_subscriber.py

预期输出：
  [INFO] [listener]: I heard: 'Hello ROS2: 0'
  [INFO] [listener]: I heard: 'Hello ROS2: 1'
  ...
"""

# TODO: 你来实现
# 提示：
# 1. import rclpy 和 Node
# 2. import std_msgs.msg.String
# 3. 创建 Subscriber 类继承 Node
# 4. 在 __init__ 中创建 subscription
# 5. 实现 listener_callback 处理消息


class SimpleSubscriber:
    """订阅 /chatter topic 并打印消息。"""

    def __init__(self):
        # TODO: 你来实现
        # 提示：
        # 1. super().__init__("listener")
        # 2. self.subscription = self.create_subscription(...)
        # 3. 参数：String, "chatter", self.listener_callback, 10
        raise NotImplementedError("请实现 SimpleSubscriber.__init__")

    def listener_callback(self, msg):
        # TODO: 你来实现
        # 提示：
        # 1. self.get_logger().info(f"I heard: '{msg.data}'")
        raise NotImplementedError("请实现 listener_callback")


def main(args=None):
    # TODO: 你来实现
    # 提示：和 simple_publisher.py 的 main 类似
    raise NotImplementedError("请实现 main")


if __name__ == "__main__":
    main()
