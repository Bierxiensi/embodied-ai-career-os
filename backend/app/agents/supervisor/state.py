"""Supervisor Agent 状态定义。

LangGraph StateGraph 在各节点间传递的状态。
total=False 允许各节点局部更新（LangGraph 合并语义）。
"""

from __future__ import annotations

from typing import TypedDict


class SupervisorState(TypedDict, total=False):
    """Supervisor 状态机。

    流转：analyze_intent → select_agents → create_plan

    字段分组：
    - 输入：user_input
    - 中间态：intent（learn / complete / career / unknown）
    - 输出：required_agents / execution_plan / result
    """

    # ===== 输入 =====
    user_input: str          # 用户原始输入文本

    # ===== 中间态 =====
    intent: str              # 识别出的意图类别

    # ===== 输出 =====
    required_agents: list[str]   # 需要调度的下游 Agent 名称列表
    execution_plan: dict         # 执行计划（步骤序列）
    result: dict                 # 最终结果（执行后填充，Day 2 仅占位）
