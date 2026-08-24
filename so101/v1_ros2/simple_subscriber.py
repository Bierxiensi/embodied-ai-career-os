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

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class SimpleSubscriber(Node):
    """订阅 /chatter topic 并打印消息。"""

    def __init__(self):
        super().__init__("listener")
        self.subscription = self.create_subscription(
            String, "chatter", self.listener_callback, 10
        )

    def listener_callback(self, msg):
        self.get_logger().info(f"I heard: '{msg.data}'")


def main(args=None):
    rclpy.init(args=args)
    node = SimpleSubscriber()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
          rclpy.shutdown()


if __name__ == "__main__":
    main()
