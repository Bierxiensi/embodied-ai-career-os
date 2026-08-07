"""Reviewer Agent 适配类。

将现有 Reviewer LangGraph 适配到 BaseAgent 框架。

设计要点：
- 复用现有 build_reviewer_graph()，不重写业务逻辑
- 模块级预编译 graph（与 api/reviewer.py 的 _reviewer 一致）
- Reviewer 需要 db session，由调用方通过 state["db"] 注入
  （与现有 api/reviewer.py 调用方式一致，适配层无需特殊处理）
- 现有 api/reviewer.py 仍直接用模块级 _reviewer，本类不影响其行为
"""

from __future__ import annotations

from typing import Any

from app.agents.core.agent import BaseAgent
from app.agents.reviewer.graph import build_reviewer_graph
from app.agents.reviewer.state import ReviewerState


class ReviewerAgent(BaseAgent):
    """Reviewer Agent 适配类。

    负责评估学习证据、更新技能等级、记录评估结果。
    业务逻辑全部在 reviewer/graph.py + nodes.py，本类仅做框架适配。
    """

    # 模块级预编译：图无状态（db 通过 state 注入），编译一次全局复用
    _graph: Any = None

    def __init__(self) -> None:
        if ReviewerAgent._graph is None:
            ReviewerAgent._graph = build_reviewer_graph()

    @property
    def name(self) -> str:
        return "reviewer"

    @property
    def state_class(self) -> type:
        return ReviewerState

    def build_graph(self) -> Any:
        """返回预编译的 CompiledGraph。"""
        return ReviewerAgent._graph
