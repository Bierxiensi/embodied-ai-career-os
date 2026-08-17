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

# TODO: 你来实现
# 提示：
# 1. import rclpy 和 Node
# 2. import std_msgs.msg.Float64MultiArray
# 3. 创建 JointPublisher 类继承 Node
# 4. 在 __init__ 中创建 publisher 和 timer
# 5. 实现 timer_callback 发送预设关节角度序列


class JointPublisher:
    """发布 SO101 关节角度到 /joint_commands topic。"""

    def __init__(self):
        # TODO: 你来实现
        # 提示：
        # 1. super().__init__("joint_publisher")
        # 2. self.publisher_ = self.create_publisher(Float64MultiArray, "joint_commands", 10)
        # 3. self.timer = self.create_timer(1.0, self.timer_callback)
        # 4. self.step = 0
        raise NotImplementedError("请实现 JointPublisher.__init__")

    def timer_callback(self):
        """按预设序列发送关节角度（Home → Reach out → Reach up → Retract）。"""
        # TODO: 你来实现
        # 提示：
        # 1. 定义 4 组目标姿态（弧度）
        #    poses = [
        #        [0.0, 0.0, 0.0, 0.0],               # Home
        #        [0.524, -0.524, 0.524, 1.047],       # Reach out (30°, -30°, 30°, 60°)
        #        [0.0, -0.785, 1.571, 0.0],           # Reach up (0°, -45°, 90°, 0°)
        #        [-0.524, 0.524, -0.524, -1.047],     # Retract (-30°, 30°, -30°, -60°)
        #    ]
        # 2. 取当前姿态：pose = poses[self.step % len(poses)]
        # 3. 创建 Float64MultiArray 消息
        # 4. 发布并打印日志
        # 5. self.step += 1
        raise NotImplementedError("请实现 timer_callback")


def main(args=None):
    # TODO: 你来实现
    # 提示：和 simple_publisher.py 的 main 类似
    raise NotImplementedError("请实现 main")


if __name__ == "__main__":
    main()
