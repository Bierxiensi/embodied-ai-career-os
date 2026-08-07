"""Research Agent 适配类。

将 Research LangGraph 适配到 BaseAgent 框架，
使其可被 AgentRegistry 统一注册、被 Supervisor 调度。

职责：
- 论文/资料研究入口
- 按主题生成研究计划（paper / code / experiment / verification）

Phase 2 不做 RAG，先用模板覆盖核心主题，未命中主题走 fallback。
"""

from __future__ import annotations

from typing import Any

from app.agents.core.agent import BaseAgent
from app.agents.research.graph import build_research_graph
from app.agents.research.state import ResearchState


class ResearchAgent(BaseAgent):
    """Research Agent 适配类。

    业务逻辑全部在 research/nodes.py + templates.py，本类仅做框架适配。
    """

    # 模块级预编译：图无状态，编译一次全局复用
    _graph: Any = None

    def __init__(self) -> None:
        if ResearchAgent._graph is None:
            ResearchAgent._graph = build_research_graph()

    @property
    def name(self) -> str:
        return "research"

    @property
    def state_class(self) -> type:
        return ResearchState

    def build_graph(self) -> Any:
        """返回预编译的 CompiledGraph。"""
        return ResearchAgent._graph
