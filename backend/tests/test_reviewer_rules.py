"""Reviewer Agent rules 纯函数单元测试。

验证 Evidence Score 评分与等级决策逻辑的确定性。
"""

from __future__ import annotations

import sys
import os

# 确保可导入 app 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.reviewer.rules import (
    SCORE_ARTIFACT,
    SCORE_LOG_SUFFICIENT,
    SCORE_REFLECTION,
    SCORE_TASK_DONE,
    THRESHOLD_EVIDENCE,
    THRESHOLD_LEVEL_UP,
    build_evidence_entry,
    decide_level,
    score_evidence,
)


def test_score_full_evidence():
    """全部证据齐全 → 100 分。"""
    task = {"status": "done"}
    log = {
        "content": "成功运行 Example，总结了环境搭建步骤，反思了改进点。",
        "artifact_url": "https://github.com/user/repo",
    }
    assert score_evidence(task, log) == 100


def test_score_only_task_done():
    """仅任务完成 → 30 分。"""
    task = {"status": "done"}
    log = {"content": "短", "artifact_url": ""}
    assert score_evidence(task, log) == SCORE_TASK_DONE


def test_score_task_not_done():
    """任务未完成 → 0 分（任务完成是前置条件）。"""
    task = {"status": "todo"}
    log = {"content": "成功运行 Example，总结了环境搭建步骤，反思了改进点。", "artifact_url": "https://github.com/user/repo"}
    assert score_evidence(task, log) == SCORE_LOG_SUFFICIENT + SCORE_ARTIFACT + SCORE_REFLECTION


def test_score_log_too_short():
    """日志 < 20 字 → 不给日志分。"""
    task = {"status": "done"}
    log = {"content": "短", "artifact_url": ""}
    assert score_evidence(task, log) == SCORE_TASK_DONE


def test_score_no_reflection_keyword():
    """日志无反思关键词 → 不给反思分。"""
    task = {"status": "done"}
    log = {"content": "今天学了 Isaac Sim 基础环境搭建的流程步骤", "artifact_url": ""}
    # 30 (task) + 20 (log>=20字) + 0 (无关键词) + 0 (无artifact)
    assert score_evidence(task, log) == SCORE_TASK_DONE + SCORE_LOG_SUFFICIENT


def test_decide_level_upgrade():
    """得分 >= 80 且未达 target → 升级。"""
    new_level, conf, reason, append = decide_level(100, 0, 4)
    assert new_level == 1
    assert conf == 1.0
    assert "0 → 1" in reason
    assert append is True


def test_decide_level_at_target():
    """得分 >= 80 但已达 target → 不升级，仍追加 evidence。"""
    new_level, conf, reason, append = decide_level(100, 4, 4)
    assert new_level == 4
    assert "已达目标" in reason
    assert append is True


def test_decide_level_partial_evidence():
    """50-79 分 → 不升级，追加 evidence。"""
    new_level, conf, reason, append = decide_level(60, 1, 4)
    assert new_level == 1
    assert "维持等级" in reason
    assert append is True


def test_decide_level_insufficient():
    """< 50 分 → 不升级，不追加 evidence。"""
    new_level, conf, reason, append = decide_level(30, 1, 4)
    assert new_level == 1
    assert reason == "insufficient evidence"
    assert append is False


def test_build_evidence_with_artifact():
    """evidence 条目含 artifact。"""
    task = {"title": "Isaac Sim 基础环境搭建"}
    log = {"artifact_url": "https://github.com/user/repo"}
    entry = build_evidence_entry(task, log)
    assert "Isaac Sim 基础环境搭建" in entry
    assert "https://github.com/user/repo" in entry


def test_build_evidence_without_artifact():
    """无 artifact 时 evidence 条目仅含标题。"""
    task = {"title": "ROS2 Topic 通信"}
    log = {"artifact_url": ""}
    entry = build_evidence_entry(task, log)
    assert entry == "ROS2 Topic 通信"


def run_all():
    """运行全部测试并输出结果。"""
    tests = [
        ("test_score_full_evidence", test_score_full_evidence),
        ("test_score_only_task_done", test_score_only_task_done),
        ("test_score_task_not_done", test_score_task_not_done),
        ("test_score_log_too_short", test_score_log_too_short),
        ("test_score_no_reflection_keyword", test_score_no_reflection_keyword),
        ("test_decide_level_upgrade", test_decide_level_upgrade),
        ("test_decide_level_at_target", test_decide_level_at_target),
        ("test_decide_level_partial_evidence", test_decide_level_partial_evidence),
        ("test_decide_level_insufficient", test_decide_level_insufficient),
        ("test_build_evidence_with_artifact", test_build_evidence_with_artifact),
        ("test_build_evidence_without_artifact", test_build_evidence_without_artifact),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {name}: {e}")
            failed += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {name}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n  Reviewer rules 单测: {passed}/{len(tests)} 通过")
    return failed


if __name__ == "__main__":
    sys.exit(run_all())
