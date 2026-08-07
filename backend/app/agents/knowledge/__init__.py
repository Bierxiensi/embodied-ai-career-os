"""Paper Knowledge Agent 包。

基于 Day 2 RAG 检索实现论文问答：
    question → retrieve（RAG）→ answer（规则组答，Day 3）

模块组成：
    - state：KnowledgeState / Citation / KnowledgeAnswer 数据契约
    - nodes：retrieve_node / answer_node
    - graph：LangGraph 编排
    - agent：PaperKnowledgeAgent 适配 BaseAgent
"""

from app.agents.knowledge.agent import PaperKnowledgeAgent
from app.agents.knowledge.graph import build_knowledge_graph
from app.agents.knowledge.state import Citation, KnowledgeAnswer, KnowledgeState

__all__ = [
    "PaperKnowledgeAgent",
    "build_knowledge_graph",
    "KnowledgeState",
    "KnowledgeAnswer",
    "Citation",
]
