"""Paper Knowledge Agent 适配类。

将 Knowledge LangGraph 适配到 BaseAgent 框架，
使其可被 AgentRegistry 统一注册、被 Supervisor 调度。

职责：
- 论文知识问答入口
- 基于 RAG 检索回答用户关于论文的问题（Day 3 规则组答）

Week 2+ 接 LLM 后，仅 answer_node 内部替换为 LLM，本类不变。
"""

from __future__ import annotations

from typing import Any

from app.agents.core.agent import BaseAgent
from app.agents.core.state import AgentState
from app.agents.knowledge.graph import build_knowledge_graph
from app.agents.knowledge.state import KnowledgeState


# 扩展通用 state，兼容 AgentState 的 agent_name / trace_id 字段
class _KnowledgeAgentState(AgentState, KnowledgeState, total=False):
    """Knowledge Agent 完整状态（合并通用字段 + 业务字段）。"""

    db: Any  # API 层注入的 db session


class PaperKnowledgeAgent(BaseAgent):
    """Paper Knowledge Agent 适配类。

    业务逻辑全部在 knowledge/nodes.py，本类仅做框架适配。
    """

    # 模块级预编译：图无状态，编译一次全局复用
    _graph: Any = None

    def __init__(self) -> None:
        if PaperKnowledgeAgent._graph is None:
            PaperKnowledgeAgent._graph = build_knowledge_graph()

    @property
    def name(self) -> str:
        return "knowledge"

    @property
    def state_class(self) -> type:
        return _KnowledgeAgentState

    def build_graph(self) -> Any:
        """返回预编译的 CompiledGraph。"""
        return PaperKnowledgeAgent._graph
