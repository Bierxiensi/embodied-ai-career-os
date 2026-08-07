"""Agent 抽象基类。

统一 Planner / Reviewer / Career / Research 等 Agent 的契约。
具体 Agent 继承 BaseAgent 并实现 name / state_class / build_graph。

设计说明：
- name：Agent 唯一标识（用于 Registry 查找、agent_runs 记录）
- state_class：State TypedDict 类，用于构建 StateGraph
- build_graph：构建并编译 LangGraph，返回 CompiledGraph
- invoke：执行入口（默认实现：build_graph().invoke(state)）

子类可覆盖 invoke 加入前置/后置处理（如 Reviewer 需注入 db session）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

# State 类型约束：必须是 dict（兼容 TypedDict）
S = TypeVar("S", bound=dict)


class BaseAgent(ABC, Generic[S]):
    """Agent 抽象基类。

    所有具体 Agent 继承此类并实现三个抽象成员：
        @property
        def name(self) -> str: ...
        @property
        def state_class(self) -> type: ...
        def build_graph(self) -> Any: ...

    invoke 默认实现足够多数场景使用；需要前置/后置处理时覆盖。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent 唯一名称，如 'planner' / 'reviewer' / 'career'。"""
        raise NotImplementedError

    @property
    @abstractmethod
    def state_class(self) -> type:
        """State TypedDict 类，用于构建 StateGraph。

        返回类型标注为 type 而非具体 TypedDict，避免运行时类型检查复杂度。
        """
        raise NotImplementedError

    @abstractmethod
    def build_graph(self) -> Any:
        """构建并编译 LangGraph，返回 CompiledGraph。

        Returns:
            CompiledGraph，可通过 .invoke(state) 执行。
        """
        raise NotImplementedError

    def invoke(self, state: S) -> S:
        """执行 Agent。

        默认实现：每次构建图并执行。
        子类可覆盖以加入前置/后置处理（如 DB session 注入、结果缓存）。

        Args:
            state: Agent 输入状态

        Returns:
            执行后的完整状态（LangGraph 合并后的 state）。
        """
        graph = self.build_graph()
        return graph.invoke(state)
