"""Supervisor LangGraph StateGraph 组装。

图结构（单链路，与 Planner/Reviewer 风格一致）：
    START → analyze_intent → select_agents → create_plan → END

Day 2 为规则路由，无条件分支。Week 2 接入 LLM 后，
analyze_intent 可能产出不确定意图，届时可加 conditional edge
做 fallback 路由，图结构仍可扩展。
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.supervisor.nodes import (
    analyze_intent,
    create_plan,
    select_agents,
)
from app.agents.supervisor.state import SupervisorState


def build_supervisor_graph():
    """构建并编译 Supervisor StateGraph。

    Returns:
        编译后的 CompiledGraph，可通过 .invoke(state) 执行。
    """

    graph = StateGraph(SupervisorState)

    # 注册节点
    graph.add_node("analyze_intent", analyze_intent)
    graph.add_node("select_agents", select_agents)
    graph.add_node("create_plan", create_plan)

    # 顺序连线
    graph.add_edge(START, "analyze_intent")
    graph.add_edge("analyze_intent", "select_agents")
    graph.add_edge("select_agents", "create_plan")
    graph.add_edge("create_plan", END)

    return graph.compile()
