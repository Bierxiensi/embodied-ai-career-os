"""Orchestrator 执行器封装。

封装 AgentExecutor，提供按 agent name 执行的便捷接口。
职责：
- 从 AgentRegistry 查找 Agent
- 调用 AgentExecutor 执行（含 tracing + agent_runs 持久化）
- 支持 DB session 注入（复用 API 请求事务）

与 core/AgentExecutor 的关系：
- core/AgentExecutor 是通用执行器，需要传入 Agent 实例
- OrchestratorExecutor 是 orchestrator 专用封装，按 name 查找，
  并集中处理 tracing 持久化策略（Day 5 统一 persist=True）

Day 6 扩展后，tracing 信息会更丰富（status/duration 字段独立）。
"""

from __future__ import annotations

from typing import Any

from app.agents.core.executor import AgentExecutor
from app.agents.core.registry import AgentRegistry


class OrchestratorExecutor:
    """Orchestrator 专用执行器。

    按 agent name 查找并执行，封装 tracing 持久化策略。
    """

    def __init__(self, db: Any = None) -> None:
        """初始化执行器。

        Args:
            db: 可选 DB session。传入时复用请求事务（如 Reviewer 的 db 注入）；
                为 None 时每个 Agent 执行时自建 session
        """
        self._db = db

    def run(
        self,
        agent_name: str,
        input_state: dict,
        persist: bool = True,
    ) -> dict:
        """按 agent name 执行 Agent。

        Args:
            agent_name: Agent 名称（如 "planner"）
            input_state: Agent 输入状态
            persist: 是否写入 agent_runs 表。默认 True。
                     Reviewer 内部已写 agent_runs，调用方可传 False 避免重复

        Returns:
            Agent 执行结果（含 _trace 元信息）

        Raises:
            ValueError: agent 未注册
            Exception: Agent 执行失败（原样抛出，由 workflow 失败隔离捕获）
        """
        agent = AgentRegistry.get(agent_name)
        if agent is None:
            raise ValueError(f"agent '{agent_name}' not registered")

        # Reviewer 内部节点已写 agent_runs，避免重复写入
        # Day 6 统一 tracing 后可移除此特判
        if agent_name == "reviewer":
            persist = False

        executor = AgentExecutor(agent)
        return executor.run(input_state, persist=persist, db=self._db)
