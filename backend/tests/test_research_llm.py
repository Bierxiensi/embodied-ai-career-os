"""Research LLM 研究计划测试。"""
from app.agents.research.nodes import match_template_node


def test_match_template_fallback():
    """Mock 环境走 fallback。"""
    result = match_template_node({"normalized_topic": "ACT"})
    assert "template" in result
    assert "paper" in result["template"]
