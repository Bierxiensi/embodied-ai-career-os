"""工具桥接测试。"""
from app.services.tools.prompts import generate_tool_prompt
from app.services.tools.context import generate_context_pack


def test_generate_trae_prompt():
    """Trae prompt 应包含架构先行要求。"""

    class FakeTask:
        title = "ROS2 publisher 实战"
        objective = "掌握 Topic 通信"
        skill_name = "ROS2"
        acceptance = ["创建publisher", "topic echo验证"]
        resources = ["ROS2 Tutorial"]
        duration = 40

    prompt = generate_tool_prompt(FakeTask(), "trae")
    assert "ROS2 publisher" in prompt
    assert "先解释整体架构" in prompt
    assert "验收标准" in prompt


def test_generate_chatgpt_prompt():
    """ChatGPT prompt 不含代码要求，强调方案讨论。"""

    class FakeTask:
        title = "ROS2 架构设计"
        objective = "理解 ROS2 通信模型"
        skill_name = "ROS2"
        acceptance = []
        resources = []
        duration = 30

    prompt = generate_tool_prompt(FakeTask(), "chatgpt")
    assert "先不要写代码" in prompt
    assert "架构决策" in prompt


def test_generate_workbuddy_prompt():
    """WorkBuddy prompt 应关注项目已有代码。"""

    class FakeTask:
        title = "分析现有 Agent"
        objective = "理解 Agent 架构"
        skill_name = "Agent Application"
        acceptance = []
        resources = []
        duration = 20

    prompt = generate_tool_prompt(FakeTask(), "workbuddy")
    assert "现有代码" in prompt


def test_generate_context_pack():
    """上下文恢复包生成不应崩溃。"""
    pack = generate_context_pack()
    assert "Session Context" in pack
    assert "## 目标岗位" in pack
    assert "## 技能状态" in pack
