"""Paper Knowledge LangGraph 组装。

图结构（单链路，与其他 Agent 风格一致）：
    START → retrieve → answer → END

Day 3：retrieve 用 Day 2 RAG 检索，answer 用规则拼接。
Week 2+：answer 节点替换为 LLM 调用，图结构不变。
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.knowledge.nodes import answer_node, retrieve_node
from app.agents.knowledge.state import KnowledgeState


def build_knowledge_graph():
    """构建并编译 Knowledge StateGraph。

    Returns:
        编译后的 CompiledGraph，可通过 .invoke(state) 执行。
    """
    graph = StateGraph(KnowledgeState)

    # 注册节点
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("answer", answer_node)

    # 顺序连线
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", END)

    return graph.compile()
