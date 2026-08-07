"""Supervisor Agent 适配类。

将 Supervisor LangGraph 适配到 BaseAgent 框架，
使其可被 AgentRegistry 统一注册。

作为 Multi-Agent 系统入口，Supervisor 本身也是一个 Agent：
- 接收 user_input
- 输出 required_agents + execution_plan
- Day 5 Orchestrator 可通过 AgentRegistry.get("supervisor") 调度入口
"""

from __future__ import annotations

from typing import Any

from app.agents.core.agent import BaseAgent
from app.agents.supervisor.graph import build_supervisor_graph
from app.agents.supervisor.state import SupervisorState


class SupervisorAgent(BaseAgent):
    """Supervisor Agent 适配类。

    负责意图识别与下游 Agent 调度规划。
    业务逻辑全部在 supervisor/nodes.py，本类仅做框架适配。
    """

    # 模块级预编译：图无状态，编译一次全局复用
    _graph: Any = None

    def __init__(self) -> None:
        if SupervisorAgent._graph is None:
            SupervisorAgent._graph = build_supervisor_graph()

    @property
    def name(self) -> str:
        return "supervisor"

    @property
    def state_class(self) -> type:
        return SupervisorState

    def build_graph(self) -> Any:
        """返回预编译的 CompiledGraph。"""
        return SupervisorAgent._graph
