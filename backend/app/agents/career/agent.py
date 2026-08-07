"""Career Agent 适配类。

将 Career LangGraph 适配到 BaseAgent 框架，
使其可被 AgentRegistry 统一注册、被 Supervisor 调度。

职责：
- 岗位分析（必需技能查表）
- Skill Gap 计算
- 学习方向推荐（优先级排序 + 路线生成）
"""

from __future__ import annotations

from typing import Any

from app.agents.career.graph import build_career_graph
from app.agents.career.state import CareerState
from app.agents.core.agent import BaseAgent


class CareerAgent(BaseAgent):
    """Career Agent 适配类。

    业务逻辑全部在 career/nodes.py + rules.py，本类仅做框架适配。
    """

    # 模块级预编译：图无状态，编译一次全局复用
    _graph: Any = None

    def __init__(self) -> None:
        if CareerAgent._graph is None:
            CareerAgent._graph = build_career_graph()

    @property
    def name(self) -> str:
        return "career"

    @property
    def state_class(self) -> type:
        return CareerState

    def build_graph(self) -> Any:
        """返回预编译的 CompiledGraph。"""
        return CareerAgent._graph
