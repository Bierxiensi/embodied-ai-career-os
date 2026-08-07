"""Planner Agent 适配类。

将现有 Planner LangGraph 适配到 BaseAgent 框架，使其可被
AgentRegistry 统一注册、被 Supervisor/Orchestrator 统一调度。

设计要点：
- 复用现有 build_planner_graph()，不重写业务逻辑
- 模块级预编译 graph（与 api/planner.py 的 _planner 一致，编译一次复用）
- 现有 api/planner.py 仍直接用模块级 _planner，本适配类不影响其行为
- Day 5 Orchestrator 接入后，可通过 AgentRegistry.get("planner") 调度
"""

from __future__ import annotations

from typing import Any

from app.agents.core.agent import BaseAgent
from app.agents.planner.graph import build_planner_graph
from app.agents.planner.state import PlannerState


class PlannerAgent(BaseAgent):
    """Planner Agent 适配类。

    负责将技能缺口转化为具体学习任务。
    业务逻辑全部在 planner/graph.py + nodes.py，本类仅做框架适配。
    """

    # 模块级预编译：图无状态，编译一次全局复用，避免每次 invoke 重建
    _graph: Any = None

    def __init__(self) -> None:
        if PlannerAgent._graph is None:
            PlannerAgent._graph = build_planner_graph()

    @property
    def name(self) -> str:
        return "planner"

    @property
    def state_class(self) -> type:
        return PlannerState

    def build_graph(self) -> Any:
        """返回预编译的 CompiledGraph。

        Day 1 框架约定每次调用 build_graph() 返回可 invoke 的图；
        此处返回预编译实例以复用（图本身无状态）。
        """
        return PlannerAgent._graph
