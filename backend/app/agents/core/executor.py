"""统一 Agent 执行器。

职责：
- 调用 Agent.invoke
- 记录开始/结束时间、输入、输出、状态
- 写入 agent_runs 表（持久化 tracing）
- 错误捕获与标记

设计为可独立实例化，便于未来注入不同 DB session 或 tracing sink。

与现有 Planner/Reviewer 的关系：
- 现有 Reviewer 在节点内部已写 agent_runs（record_agent_run 节点）
- 接入 Executor 时调用方传 persist=False，避免重复写入
- Day 5 Orchestrator 接入后，统一由 Executor 负责 tracing，Reviewer 节点可移除写入逻辑
- Day 6 扩展 AgentRun 模型字段（status / duration_ms），届时调整 _record 实现
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from app.agents.core.agent import BaseAgent
from app.db.base import SessionLocal
from app.models.agent_run import AgentRun


class AgentExecutor:
    """统一 Agent 执行器。

    用法：
        agent = PlannerAgent()
        result = AgentExecutor(agent).run({"available_minutes": 30, ...})

    失败时重新抛出异常，调用方可感知；tracing 仍记录到 agent_runs。
    """

    def __init__(self, agent: BaseAgent):
        self.agent = agent

    def run(
        self,
        input_state: dict,
        persist: bool = True,
        db: Any = None,
    ) -> dict:
        """执行 Agent 并记录 tracing。

        Args:
            input_state: Agent 输入状态
            persist: 是否写入 agent_runs 表。若具体 Agent 内部已写
                     （如 Reviewer 的 record_agent_run 节点），应传 False
                     避免重复写入
            db: 可选 DB session（由 API 层注入，复用请求事务）；
                为 None 时 executor 自建 session

        Returns:
            执行后的完整状态（含 agent_run_id 与 _trace 元信息）。
        """
        run_id = str(uuid.uuid4())
        start_ms = time.perf_counter()
        status = "success"
        output_state: dict = {}

        # 注入 tracing 字段（不污染调用方原始 state）
        enriched_input = {
            **input_state,
            "agent_name": self.agent.name,
            "trace_id": run_id,
        }

        try:
            output_state = self.agent.invoke(enriched_input) or {}
        except Exception as e:
            status = "failed"
            output_state = {"error": str(e)}
            raise  # 重新抛出，调用方可感知失败
        finally:
            elapsed_ms = int((time.perf_counter() - start_ms) * 1000)
            if persist:
                self._record(
                    run_id=run_id,
                    input_state=enriched_input,
                    output_state=output_state,
                    status=status,
                    elapsed_ms=elapsed_ms,
                    db=db,
                )

        # tracing 元信息挂到输出，供下游/前端展示（Day 6 Dashboard 用）
        output_state["agent_run_id"] = run_id
        output_state["_trace"] = {
            "agent": self.agent.name,
            "status": status,
            "duration_ms": elapsed_ms,
        }
        return output_state

    def _record(
        self,
        run_id: str,
        input_state: dict,
        output_state: dict,
        status: str,
        elapsed_ms: int,
        db: Any = None,
    ) -> None:
        """写入 agent_runs 表。

        Day 6 起 status / duration_ms / trace_id 为独立字段，
        output_result 仅存 Agent 业务输出，不再混入 _trace 元信息。
        """
        own_db = db is None
        session = db or SessionLocal()
        try:
            session.add(
                AgentRun(
                    id=run_id,
                    agent_name=self.agent.name,
                    input_context=json.dumps(
                        input_state, ensure_ascii=False, default=str
                    ),
                    output_result=json.dumps(
                        output_state, ensure_ascii=False, default=str
                    ),
                    status=status,
                    duration_ms=elapsed_ms,
                    trace_id=run_id,  # run_id 即 trace_id（同一次调用链）
                )
            )
            session.commit()
        finally:
            if own_db:
                session.close()
