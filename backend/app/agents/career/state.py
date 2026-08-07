"""Career Agent 状态定义。

LangGraph StateGraph 在各节点间传递的状态。
total=False 允许各节点局部更新（LangGraph 合并语义）。

流转：analyze_target → compute_gaps → prioritize → recommend
"""

from __future__ import annotations

from typing import TypedDict


class SkillStatus(TypedDict):
    """技能当前状态（输入项）。"""

    name: str           # 技能名称
    level: int          # 当前等级 0-5
    target: int         # 目标等级 0-5


class SkillGapItem(TypedDict):
    """排序后的缺口项（compute_gaps 节点产出）。"""

    name: str
    level: int
    target: int
    gap: int            # target - level，正值表示缺口
    required: bool      # 是否为岗位必需技能


class CareerState(TypedDict, total=False):
    """Career 状态机。

    字段分组：
    - 输入：target_role / current_skills
    - 中间态：required_skills / gaps
    - 输出：priority / recommendation
    """

    # ===== 输入 =====
    target_role: str               # 目标岗位，如 Robot AI Engineer
    current_skills: list[SkillStatus]   # 当前技能状态

    # ===== 中间态 =====
    required_skills: list[str]     # 岗位必需技能清单
    gaps: list[SkillGapItem]       # 排序后的缺口列表

    # ===== 输出 =====
    priority: list[str]            # 优先学习技能名（高 → 低）
    recommendation: dict           # 推荐路线（含 steps / rationale）
