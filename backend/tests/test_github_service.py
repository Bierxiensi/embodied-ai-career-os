"""GitHub Service 单元测试。"""
import pytest
from app.services.github.analyzer import analyze_commit


def test_analyze_commit_mock():
    """Mock LLM 时返回 None（fallback）。"""
    result = analyze_commit({
        "sha": "abc123",
        "message": "feat: add ROS2 publisher",
        "files": [{"filename": "ros2_ws/src/publisher.py", "additions": 45, "deletions": 0}],
        "additions": 45,
        "deletions": 0,
    })
    # Mock LLM 返回 JSON parse 失败 → None
    assert result is None


def test_analyze_commit_empty_files():
    result = analyze_commit({
        "sha": "abc",
        "message": "chore: update deps",
        "files": [],
        "additions": 1,
        "deletions": 1,
    })
    assert result is None
