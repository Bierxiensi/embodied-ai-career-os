"""Research LangGraph StateGraph 组装。

图结构（单链路，与其他 Agent 风格一致）：
    START → parse_topic → match_template → decompose_tasks → build_plan → END

Day 4 不联网，全部基于本地模板。
Week 4-6 接入 RAG 后，match_template 节点可替换为向量检索，图结构不变。
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.research.nodes import (
    build_plan,
    decompose_tasks,
    match_template_node,
    parse_topic,
)
from app.agents.research.state import ResearchState


def build_research_graph():
    """构建并编译 Research StateGraph。

    Returns:
        编译后的 CompiledGraph，可通过 .invoke(state) 执行。
    """

    graph = StateGraph(ResearchState)

    # 注册节点
    graph.add_node("parse_topic", parse_topic)
    graph.add_node("match_template", match_template_node)
    graph.add_node("decompose_tasks", decompose_tasks)
    graph.add_node("build_plan", build_plan)

    # 顺序连线
    graph.add_edge(START, "parse_topic")
    graph.add_edge("parse_topic", "match_template")
    graph.add_edge("match_template", "decompose_tasks")
    graph.add_edge("decompose_tasks", "build_plan")
    graph.add_edge("build_plan", END)

    return graph.compile()
