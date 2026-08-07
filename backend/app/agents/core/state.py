"""Agent 通用状态基类。

所有具体 Agent 的 State 应继承 AgentState 并扩展业务字段。
LangGraph 在节点间合并状态，total=False 允许各节点局部更新。

示例：
    class PlannerState(AgentState, total=False):
        available_minutes: int
        skills: list[SkillInput]
        # ... 业务字段
"""

from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """Agent 通用状态基类。

    通用字段（所有 Agent 共享，用于 tracing 与调度）：
    - agent_name：当前 Agent 名称（由 Executor 注入）
    - trace_id：执行追踪 ID（关联一次完整调用链，由 Executor 注入）

    业务字段由子类继承后扩展，不应在此处堆积业务语义。
    """

    agent_name: str
    trace_id: str
