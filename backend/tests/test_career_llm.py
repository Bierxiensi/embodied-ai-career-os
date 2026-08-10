"""Career LLM 缺口分析测试。"""
from app.agents.career.nodes import analyze_target


def test_analyze_target_fallback():
    """Mock 环境走 fallback。"""
    result = analyze_target({
        "target_role": "Robot AI Engineer",
        "current_skills": [
            {"name": "ROS2", "level": 1, "target_level": 4, "evidence": []},
        ],
    })
    assert "required_skills" in result
    assert len(result["required_skills"]) > 0
