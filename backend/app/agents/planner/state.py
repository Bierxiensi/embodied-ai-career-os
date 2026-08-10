"""Planner Agent 状态定义。

LangGraph StateGraph 在各节点间传递的状态。
设计为可扩展：后续可加入 energy/deadline 等约束字段而不破坏现有节点。
"""

from typing import TypedDict


class SkillInput(TypedDict):
    """技能输入项（来自前端/数据库的技能状态）。"""

    name: str
    level: int
    target: int


class GapItem(TypedDict):
    """排序后的缺口项（analyze_skill_gap 节点产出）。"""

    name: str
    level: int
    target: int
    gap: int  # target - level


class PlannerState(TypedDict, total=False):
    """Planner 状态机。

    total=False：所有字段可选，便于各节点局部更新（LangGraph 合并语义）。
    分为输入 / 中间态 / 输出三组，便于阅读演进。
    """

    # ===== 输入 =====
    available_minutes: int       # 可用学习时间（分钟）
    target_role: str             # 目标岗位
    skills: list[SkillInput]     # 当前技能状态
    energy_level: str            # 能量水平：low / normal / high（影响难度选择）
    current_focus: str           # 当前聚焦技能（可选，强制指定时跳过自动选择）

    # ===== 中间态 =====
    gaps: list[GapItem]          # 排序后的缺口列表
    selected_skill: str          # 选中的目标技能
    generator: str               # 使用的生成器：rule / llm

    # ===== V2 Project 上下文 =====
    project_id: int | None       # 关联项目 ID
    milestone_id: int | None     # 关联里程碑 ID
    project_context: str         # 项目上下文文本（注入 prompt）

    # ===== 输出 =====
    task: dict                   # 生成的任务（TaskOutput 结构）
    valid: bool                  # 校验结果
