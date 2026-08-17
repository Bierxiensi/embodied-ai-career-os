"""ROS2 简单 Publisher 示例：发布字符串消息到 /chatter topic。

运行前提：已安装 ROS2 Humble（Ubuntu 22.04 或 WSL2）

运行方式：
  source /opt/ros/humble/setup.bash
  python3 simple_publisher.py

预期输出：
  [INFO] [talker]: Publishing: 'Hello ROS2: 0'
  [INFO] [talker]: Publishing: 'Hello ROS2: 1'
  ...
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class SimplePublisher(Node):
    """发布字符串消息到 /chatter topic。"""

    def __init__(self):
        super().__init__("talker")
        # 创建 Publisher：消息类型 String，topic 名 /chatter，队列深度 10
        self.publisher_ = self.create_publisher(String, "chatter", 10)
        # 创建定时器：每 0.5 秒发布一次
        self.timer = self.create_timer(0.5, self.timer_callback)
        self.count = 0

    def timer_callback(self):
        msg = String()
        msg.data = f"Hello ROS2: {self.count}"
        self.publisher_.publish(msg)
        self.get_logger().info(f"Publishing: '{msg.data}'")
        self.count += 1


def main(args=None):
    rclpy.init(args=args)
    node = SimplePublisher()
    try:
        rclpy.spin(node)  # 阻塞，直到 Ctrl+C
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
