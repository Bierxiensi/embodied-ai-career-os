"""ROS2 SO101 关节控制 Publisher：发布关节角度到 /joint_commands topic。

运行前提：
  1. 已安装 ROS2 Humble
  2. 已 source ROS2 环境

运行方式：
  python3 joint_publisher.py

消息格式：Float64MultiArray
  data: [joint0_rad, joint1_rad, joint2_rad, joint3_rad]
  （4 个关节，弧度制）

预期输出：
  [INFO] [joint_publisher]: 发送关节角度: [0.0, 0.0, 0.0, 0.0] rad
  [INFO] [joint_publisher]: 发送关节角度: [0.524, -0.524, 0.524, 1.047] rad
  ...
"""

import math

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray


class JointPublisher(Node):
    """发布 SO101 关节角度到 /joint_commands topic。"""

    def __init__(self):
        super().__init__("joint_publisher")
        # Publisher：消息类型 Float64MultiArray，topic /joint_commands
        self.publisher_ = self.create_publisher(
            Float64MultiArray,
            "joint_commands",
            10,
        )
        # 定时器：每 1 秒发布一次
        self.timer = self.create_timer(1.0, self.timer_callback)
        self.step = 0

    def timer_callback(self):
        """按预设序列发送关节角度（Home → Reach out → Reach up → Retract）。"""
        # 定义 4 组目标姿态（弧度）
        poses = [
            [0.0, 0.0, 0.0, 0.0],               # Home
            [0.524, -0.524, 0.524, 1.047],       # Reach out (30°, -30°, 30°, 60°)
            [0.0, -0.785, 1.571, 0.0],           # Reach up (0°, -45°, 90°, 0°)
            [-0.524, 0.524, -0.524, -1.047],     # Retract (-30°, 30°, -30°, -60°)
        ]

        pose = poses[self.step % len(poses)]
        msg = Float64MultiArray()
        msg.data = pose

        self.publisher_.publish(msg)
        self.get_logger().info(
            f"发送关节角度: [{', '.join(f'{x:.3f}' for x in pose)}] rad"
        )

        self.step += 1


def main(args=None):
    rclpy.init(args=args)
    node = JointPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
