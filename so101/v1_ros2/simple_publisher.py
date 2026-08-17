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


class SimplePublisher:
    """发布字符串消息到 /chatter topic。"""

    def __init__(self):
        # TODO: 你来实现
        # 提示：
        # 1. super().__init__("talker")
        # 2. self.publisher_ = self.create_publisher(...)
        # 3. self.timer = self.create_timer(0.5, self.timer_callback)
        # 4. self.count = 0
        raise NotImplementedError("请实现 SimplePublisher.__init__")

    def timer_callback(self):
        # TODO: 你来实现
        # 提示：
        # 1. 创建 String 消息
        # 2. 设置 msg.data = f"Hello ROS2: {self.count}"
        # 3. 发布消息
        # 4. 打印日志
        # 5. self.count += 1
        raise NotImplementedError("请实现 timer_callback")


def main(args=None):
    # TODO: 你来实现
    # 提示：
    # 1. rclpy.init(args=args)
    # 2. node = SimplePublisher()
    # 3. rclpy.spin(node)
    # 4. KeyboardInterrupt 处理
    # 5. 清理资源
    raise NotImplementedError("请实现 main")


if __name__ == "__main__":
    main()
