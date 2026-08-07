"""Career LangGraph StateGraph 组装。

图结构（单链路，与 Planner/Reviewer/Supervisor 风格一致）：
    START → analyze_target → compute_gaps → prioritize → recommend → END

Day 3 为规则路由。Week 2 接入 LLM 后，analyze_target 可能动态
扩展必需技能清单，图结构无需改动。
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.career.nodes import (
    analyze_target,
    compute_gaps,
    prioritize,
    recommend,
)
from app.agents.career.state import CareerState


def build_career_graph():
    """构建并编译 Career StateGraph。

    Returns:
        编译后的 CompiledGraph，可通过 .invoke(state) 执行。
    """

    graph = StateGraph(CareerState)

    # 注册节点
    graph.add_node("analyze_target", analyze_target)
    graph.add_node("compute_gaps", compute_gaps)
    graph.add_node("prioritize", prioritize)
    graph.add_node("recommend", recommend)

    # 顺序连线
    graph.add_edge(START, "analyze_target")
    graph.add_edge("analyze_target", "compute_gaps")
    graph.add_edge("compute_gaps", "prioritize")
    graph.add_edge("prioritize", "recommend")
    graph.add_edge("recommend", END)

    return graph.compile()
