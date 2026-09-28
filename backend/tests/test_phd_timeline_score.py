# backend/tests/test_phd_timeline_score.py
"""X4：时间窗口分必须区分「黄金窗口 / 太近 / 太远 / 未公布」（2026-09-24 裁决）。"""

from datetime import date

from app.agents.phd.agent import _timeline_score

TODAY = date(2026, 9, 24)


def test_none_deadline_is_neutral_not_high():
    # 旧实现 None→70，导致不录截止日的机会排名虚高（X4 病灶）
    assert _timeline_score(None, TODAY) == 55


def test_expired_is_low():
    assert _timeline_score(date(2026, 9, 23), TODAY) == 20


def test_too_soon_is_penalized():
    # 30 天内截止：来不及准备
    assert _timeline_score(date(2026, 10, 10), TODAY) == 50


def test_golden_window_is_highest():
    # 30-270 天：有准备期且不遥远（覆盖 26 秋-27 春申请季）
    assert _timeline_score(date(2026, 12, 31), TODAY) == 95
    assert _timeline_score(date(2027, 6, 20), TODAY) == 95


def test_far_future_decays():
    assert _timeline_score(date(2027, 12, 31), TODAY) == 75
    assert _timeline_score(date(2029, 1, 1), TODAY) == 55
