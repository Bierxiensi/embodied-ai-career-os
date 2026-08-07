"""Reviewer LangGraph StateGraph 组装。

图结构（单链路，与 Planner 风格一致）：
    START → collect_context → evaluate_evidence → create_assessment
          → apply_skill_update → record_agent_run → END

db session 通过 state 注入，节点内完成 DB 读写。
record_agent_run 负责最终 commit，保证 SkillAssessment + Skill + AgentRun 原子性。
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.reviewer.nodes import (
    apply_skill_update,
    collect_context,
    create_assessment,
    evaluate_evidence,
    record_agent_run,
)
from app.agents.reviewer.state import ReviewerState


def build_reviewer_graph():
    """构建并编译 Reviewer StateGraph。

    Returns:
        编译后的 CompiledGraph，可通过 .invoke(state) 执行。
    """

    graph = StateGraph(ReviewerState)

    # 注册节点
    graph.add_node("collect_context", collect_context)
    graph.add_node("evaluate_evidence", evaluate_evidence)
    graph.add_node("create_assessment", create_assessment)
    graph.add_node("apply_skill_update", apply_skill_update)
    graph.add_node("record_agent_run", record_agent_run)

    # 顺序连线
    graph.add_edge(START, "collect_context")
    graph.add_edge("collect_context", "evaluate_evidence")
    graph.add_edge("evaluate_evidence", "create_assessment")
    graph.add_edge("create_assessment", "apply_skill_update")
    graph.add_edge("apply_skill_update", "record_agent_run")
    graph.add_edge("record_agent_run", END)

    return graph.compile()
