"""LangGraph StateGraph 组装。

图结构（单链路，Day5 保持简单）：
    START → analyze_skill_gap → select_learning_target
          → generate_task → validate_task → END

generate_task 内部按 state.generator 选择 rule/llm（可插拔），
无需在图层面做条件分支，降低复杂度。未来 Supervisor 可在此图外层编排。
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.planner.nodes import (
    analyze_skill_gap,
    generate_task,
    select_learning_target,
    validate_task,
)
from app.agents.planner.state import PlannerState


def build_planner_graph():
    """构建并编译 Planner StateGraph。

    Returns:
        编译后的 CompiledGraph，可通过 .invoke(state) 执行。
    """

    graph = StateGraph(PlannerState)

    # 注册节点
    graph.add_node("analyze_skill_gap", analyze_skill_gap)
    graph.add_node("select_learning_target", select_learning_target)
    graph.add_node("generate_task", generate_task)
    graph.add_node("validate_task", validate_task)

    # 顺序连线
    graph.add_edge(START, "analyze_skill_gap")
    graph.add_edge("analyze_skill_gap", "select_learning_target")
    graph.add_edge("select_learning_target", "generate_task")
    graph.add_edge("generate_task", "validate_task")
    graph.add_edge("validate_task", END)

    return graph.compile()
