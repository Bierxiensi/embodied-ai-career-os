"""Reviewer LLM 评估测试。"""
from app.agents.reviewer.nodes import evaluate_evidence


def test_evaluate_evidence_rule_fallback():
    """Mock LLM 时走 rule fallback，应返回合法分数。"""
    state = {
        "task": {
            "title": "ROS2 publisher", "skill_name": "ROS2", "status": "done",
            "acceptance": ["创建publisher", "topic echo验证"],
        },
        "learning_log": {
            "content": "完成了publisher节点，理解了QoS配置，学到了通信模型",
            "artifact_url": "https://github.com/xxx",
        },
    }
    result = evaluate_evidence(state)
    assert "evidence_score" in result
    assert 0 <= result["evidence_score"] <= 100


def test_evaluate_evidence_insufficient():
    """日志过短，得分应低。"""
    state = {
        "task": {
            "title": "task", "skill_name": "skill", "status": "todo",
            "acceptance": [],
        },
        "learning_log": {"content": "done", "artifact_url": ""},
    }
    result = evaluate_evidence(state)
    assert result["evidence_score"] < 50
