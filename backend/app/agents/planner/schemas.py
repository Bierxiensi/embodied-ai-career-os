"""Planner Agent 输出 Schema。

TaskOutput 是 Planner → Task DB → Reviewer Agent 的稳定契约，
字段固定，下游组件（Day6 API、未来 Reviewer Agent）依赖此结构。
"""

from typing import TypedDict


class TaskOutput(TypedDict):
    """Planner 生成的学习任务。"""

    title: str               # 任务标题
    skill: str               # 关联技能名称
    objective: str           # 学习目标（一句话描述达成什么）
    duration: int            # 预计时长（分钟）
    difficulty: str          # 难度：beginner / intermediate / advanced
    acceptance: list[str]    # 验收标准清单
    resources: list[str]     # 推荐资源（文档/示例/项目）
    status: str              # 初始状态固定 todo
