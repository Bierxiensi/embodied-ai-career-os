"""Reviewer LangGraph StateGraph 组装。

图结构（单链路，与 Planner 风格一致）：
    START → collect_context → evaluate_evidence → create_assessment
          → apply_skill_update → record_agent_run → END

db session 通过 state 注入。图只产出契约提案（state["review"]），不写
SkillAssessment / skill 等级（spec §4.3 只读铁律）——落库由 API 层经
apply_review_proposal 完成；record_agent_run 的 commit 只提交
Task/LearningLog/AgentRun 等 tracing 与事实写入。
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
