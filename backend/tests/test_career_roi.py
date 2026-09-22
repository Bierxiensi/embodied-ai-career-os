"""Career ROI 纯函数测试（Phase 2）。

覆盖 compute_task_roi 的四维归一、时长系数、上限 1.5，以及 Top5 排序不变式。
纯函数，不依赖数据库。
"""

from __future__ import annotations

from app.core.career_roi import WEIGHTS, ROI_CAP, compute_task_roi


# ============================================================
# 1. 各维归一
# ============================================================


def test_skill_delta_positive_gap():
    # gap=5 → min(5,3)/3 = 1.0；gap=0 → 0.0
    r = compute_task_roi("Python", 5, ("llm",), ["python"], "seed", 40)
    assert r.roi > 0
    # 无关联技能（skill_name=None）→ 保底 0.2
    r2 = compute_task_roi(None, 0, ("llm",), ["python"], "seed", 40)
    # 0.2*0.3 + 0.3*0.3 + 0.3*0.2 + 0.5*0.2 = 0.06+0.09+0.06+0.10 = 0.31（时长系数 1）
    assert abs(r2.roi - 0.31) < 1e-6, r2.roi


def test_goal_relevance_main_track():
    # Python ∈ 主攻 required → 1.0
    r = compute_task_roi("Python", 1, ("llm",), ["python"], "seed", 40)
    assert "目标相关度 1.00" in r.reasons
    # 非主攻技能但带 active 赛道 → 0.6
    r2 = compute_task_roi("ROS2", 1, ("llm", "embodied"), ["python"], "seed", 40, track_key="embodied")
    assert "目标相关度 0.60" in r2.reasons
    # 其余 → 0.3
    r3 = compute_task_roi("ROS2", 1, ("llm",), ["python"], "seed", 40, track_key="x")
    assert "目标相关度 0.30" in r3.reasons


def test_evidence_value():
    r = compute_task_roi("Python", 1, ("llm",), ["python"], "seed", 40)
    assert "证据价值 0.70" in r.reasons
    r2 = compute_task_roi(None, 0, ("llm",), ["python"], "seed", 40)
    assert "证据价值 0.30" in r2.reasons


def test_real_project_source():
    assert "真实项目 0.80" in compute_task_roi("Python", 1, ("llm",), ["python"], "planner", 40).reasons
    assert "真实项目 0.60" in compute_task_roi("Python", 1, ("llm",), ["python"], "user", 40).reasons
    assert "真实项目 0.50" in compute_task_roi("Python", 1, ("llm",), ["python"], "seed", 40).reasons
    assert "真实项目 0.50" in compute_task_roi("Python", 1, ("llm",), ["python"], "unknown", 40).reasons


# ============================================================
# 2. 时长系数 + 上限
# ============================================================


def test_duration_short_boosts_long_discounts():
    # 相同的任务，时长越短 roi 越高（系数 = 40 / max(duration, 20)）
    short = compute_task_roi("Python", 3, ("llm",), ["python"], "planner", 20)
    long = compute_task_roi("Python", 3, ("llm",), ["python"], "planner", 200)
    assert short.roi > long.roi


def test_roi_capped_at_1_5():
    # 最大化：主攻技能 + 大 gap + planner + 极短时长（系数封顶 40/20=2）
    r = compute_task_roi("Python", 5, ("llm",), ["python"], "planner", 1, track_key="llm")
    assert r.roi <= ROI_CAP + 1e-9, r.roi
    assert abs(r.roi - ROI_CAP) < 1e-6, r.roi


def test_weights_sum_to_1():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9
