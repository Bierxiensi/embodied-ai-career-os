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

# TODO: 你来实现
# 提示：
# 1. import rclpy 和 Node
# 2. import std_msgs.msg.String
# 3. 创建 Publisher 类继承 Node
# 4. 在 __init__ 中创建 publisher 和 timer
# 5. 实现 timer_callback 发布消息
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class SimplePublisher(Node):
    """发布字符串消息到 /chatter topic。"""

    def __init__(self):
        # TODO: 你来实现
        # 提示：
        super().__init__("talker") # 初始化节点
        self.publisher_ = self.create_publisher(String, "chatter", 10) # 创建 publisher
        self.timer = self.create_timer(0.5, self.timer_callback) # 创建定时器
        self.count = 0 # 初始化计数器

    def timer_callback(self):
        # TODO: 你来实现
        # 提示：
        # 1. 创建 String 消息
        # 2. 设置 msg.data = f"Hello ROS2: {self.count}"
        # 3. 发布消息
        # 4. 打印日志
        # 5. self.count += 1
        msg = String()
        msg.data = f"Hello ROS2: {self.count}"
        self.publisher_.publish(msg)
        self.get_logger().info(f"Publishing: '{msg.data}'")
        self.count += 1

def main(args=None):
    # TODO: 你来实现
    # 提示：
    # 1. 初始化 ROS2 节点
    # 2. 创建 SimplePublisher 实例
    # 3. 运行节点
    # 4. 处理 KeyboardInterrupt 异常
    # 5. 清理资源
    rclpy.init(args=args)
    node = SimplePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        # 确保在 Ctrl+C 时关闭 context
        if rclpy.ok():
            # 关闭 context
            rclpy.shutdown()    

if __name__ == "__main__":
    main()
