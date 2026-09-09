"""目标岗位画像配置。

求职看板的核心输入：把"我要找工作"拆成 3 条可执行的赛道。
每条赛道声明硬性要求技能，系统据此计算机匹配度与缺口。

按自己的投递策略直接改这个文件即可，无需改代码逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TargetRole:
    """一个目标岗位画像。"""

    key: str                      # 标识：agent / embodied / robot-software
    name: str                     # 岗位名称
    priority: str                 # 主攻 / 折中 / 保底
    salary_range: str             # 期望薪资区间
    note: str                     # 策略说明
    required_skills: list[str] = field(default_factory=list)   # 硬性要求技能
    required_level: int = 4       # 每项技能的要求等级（0-5）


# 三条赛道：
# 1. embodied —— 主攻，天花板最高，但必须有真机证据
# 2. robot-software —— 折中，ROS2 + AI 的复合岗，能承上启下
# 3. agent —— 保底，用现有 Agent 工程能力快速拿面试、保现金流
TARGET_ROLES: list[TargetRole] = [
    TargetRole(
        key="embodied",
        name="具身智能 / VLA 算法工程师",
        priority="主攻",
        salary_range="36-45K",
        note="天花板最高，但必须拿出 SO101 真机闭环证据（ROS2 控制 + ACT/SmolVLA + 成功率数据）",
        required_skills=["ROS2", "VLA", "Robot Learning", "PyTorch", "Isaac", "Sim2Real"],
        required_level=4,
    ),
    TargetRole(
        key="robot-software",
        name="机器人软件工程师（ROS2 + AI）",
        priority="折中",
        salary_range="30-38K",
        note="ROS2 + Python/AI 复合岗，能承接现有工程能力，是具身岗的跳板",
        required_skills=["ROS2", "MoveIt2", "Linux", "Python", "C++"],
        required_level=4,
    ),
    TargetRole(
        key="agent",
        name="Agent 应用 / LLM 算法工程师",
        priority="保底",
        salary_range="30-40K",
        note="最快拿到面试的盘：现有 Agent/RAG 工程经验即可开打，用于保底与练手谈薪",
        required_skills=["Python", "Agent Application", "PyTorch", "Deep Learning"],
        required_level=4,
    ),
]

# 求职项目标识（seed 脚本与 API 共用，保证幂等匹配）
JOB_HUNT_PROJECT_NAME = "求职冲刺 · 2026 Q4"

# offer 目标日期兜底值（Career.timeframe 无法解析时使用）
DEFAULT_OFFER_DEADLINE = "2026-10-31"
