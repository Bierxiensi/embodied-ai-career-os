"""V2 学习闭环端到端测试。

场景：用户说"学 ROS2" → 系统生成任务 → 用户完成 → 系统评估 → 技能可能升级
全程使用 mock LLM（规则 fallback），验证各环节不崩溃。
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_full_learning_loop():
    """全链路：意图分析 → 任务生成 → 复盘评估。"""
    # 1. Supervisor: 意图分析
    resp = client.post("/api/agent/run", json={"user_input": "学习 ROS2"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    # 2. Planner: 生成任务
    resp = client.post("/api/planner/generate", json={
        "available_minutes": 45,
        "skills": [
            {"name": "ROS2", "level": 1, "target": 4},
            {"name": "Python", "level": 4, "target": 5},
            {"name": "VLA", "level": 0, "target": 4},
        ],
        "generator": "rule",
        "persist": True,
    })
    assert resp.status_code == 200
    task_data = resp.json()["data"]
    task_id = task_data["task_id"]
    assert task_id is not None

    # 3. Reviewer: 完成复盘
    resp = client.post("/api/reviewer/review", json={
        "task_id": task_id,
        "content": "完成了 ROS2 publisher 节点，topic 通信正常。学会了 QoS 配置。改进了代码结构。",
        "duration_minutes": 40,
        "artifact_url": "https://github.com/prideandprejudice/embodied-ai-career-os/commit/test",
    })
    assert resp.status_code == 200
    review_data = resp.json()["data"]
    assert "assessment" in review_data
    assert "updated_skill" in review_data

    # 4. 验证 reviewer 返回的 task 状态为 done
    reviewed_task = review_data.get("task", {})
    assert reviewed_task.get("status") == "done"


def test_reminder_engine_does_not_crash():
    """提醒引擎三个推送场景均不崩溃。"""
    from app.services.reminder.engine import ReminderEngine
    engine = ReminderEngine()
    assert engine.send_morning() is True
    assert engine.send_evening() is True
    # comeback 可能返回 None 或 True
    result = engine.send_comeback()
    assert result is None or result is True


def test_context_pack_generation():
    """上下文恢复包生成不崩溃。"""
    from app.services.tools.context import generate_context_pack
    pack = generate_context_pack()
    assert isinstance(pack, str)
    assert len(pack) > 50


def test_github_suggestions_api():
    """GitHub suggestions API 可访问。"""
    resp = client.get("/api/github/suggestions")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_tools_api():
    """工具桥接 API 可访问。"""
    resp = client.get("/api/tools/context")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
