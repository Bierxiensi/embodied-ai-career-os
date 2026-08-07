"""Supervisor Agent。

Multi-Agent 系统入口：理解用户意图，决定调度哪些下游 Agent。

Day 2 阶段为规则路由（不接 LLM），后续 Week 2 接入 LLM 后替换
analyze_intent 节点即可，图结构不变。

路由规则：
    学习类意图   → ["research", "planner"]
    完成任务类   → ["reviewer"]
    职业规划类   → ["career"]
    未知/默认    → ["planner"]
"""

from app.agents.supervisor.agent import SupervisorAgent
from app.agents.supervisor.graph import build_supervisor_graph
from app.agents.supervisor.state import SupervisorState

__all__ = [
    "SupervisorState",
    "SupervisorAgent",
    "build_supervisor_graph",
]
