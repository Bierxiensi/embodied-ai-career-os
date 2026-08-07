"""Agent 核心框架。

提供 Multi-Agent 系统的基础设施：
- AgentState：通用状态基类（tracing 字段）
- BaseAgent：Agent 抽象基类（name / state_class / build_graph / invoke 契约）
- AgentExecutor：统一执行器（含 tracing + agent_runs 持久化）
- AgentRegistry：Agent 注册中心（按名查找，供 Supervisor 调度）

设计原则：
- 不绑定具体业务逻辑，Planner/Reviewer 等具体 Agent 继承 BaseAgent 实现
- Executor 与 Registry 解耦：Registry 管理实例，Executor 管理执行
- Day 1 阶段不强制现有 Planner/Reviewer 接入，保持业务零改动
"""

from app.agents.core.agent import BaseAgent
from app.agents.core.executor import AgentExecutor
from app.agents.core.registry import AgentRegistry
from app.agents.core.state import AgentState

__all__ = [
    "AgentState",
    "BaseAgent",
    "AgentExecutor",
    "AgentRegistry",
]
