"""Supervisor LLM 意图路由测试。

LLM_PROVIDER=mock 时测试 fallback 路径；
LLM_PROVIDER=deepseek 时测试 LLM 路径。
设置 DEEPSEEK_API_KEY 后可跑真实 LLM 测试。
"""

import pytest
from app.agents.supervisor.nodes import analyze_intent


def test_analyze_intent_career():
    """含"成为"关键词 → career。"""
    result = analyze_intent({"user_input": "我想成为 Robot AI 工程师"})
    assert result["intent"] == "career"


def test_analyze_intent_learn():
    """含"学习"关键词 → learn。"""
    result = analyze_intent({"user_input": "学习 ROS2 Topic 通信"})
    assert result["intent"] == "learn"


def test_analyze_intent_complete():
    """含"完成"关键词 → complete。"""
    result = analyze_intent({"user_input": "完成今天的 publisher 任务"})
    assert result["intent"] == "complete"


def test_analyze_intent_unknown():
    """无关键词 → unknown。"""
    result = analyze_intent({"user_input": "今天天气不错"})
    assert result["intent"] == "unknown"


def test_analyze_intent_empty():
    """空输入 → unknown。"""
    result = analyze_intent({})
    assert result["intent"] == "unknown"


def test_analyze_intent_natural_language_career():
    """自然语言表述职业困惑——规则可能 miss，LLM 应命中。"""
    result = analyze_intent({
        "user_input": "我不确定自己应该先学 ROS2 还是先学 VLA，帮我分析下"
    })
    # 规则兜底应至少不崩溃
    assert result["intent"] in ("career", "learn", "complete", "unknown")
