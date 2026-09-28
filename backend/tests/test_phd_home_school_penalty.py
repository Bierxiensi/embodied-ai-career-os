# backend/tests/test_phd_home_school_penalty.py
"""北航本校降权（2026-09-24 裁决：保留但降权，申请季前最终裁决）。"""

from datetime import date

from app.agents.phd.agent import HOME_SCHOOL_PENALTY, PhDMatchEngine, _is_home_school

KW = dict(
    direction_interest=80,
    tier="985",
    city="北京",
    min_publication="none",
    target_in_service=True,
    advisor_in_service=True,
    application_deadline=date(2027, 3, 1),
    today=date(2026, 9, 24),
)


def test_home_school_flag_lowers_overall():
    base = PhDMatchEngine.compute(**KW)
    home = PhDMatchEngine.compute(**KW, is_home_school=True)
    assert home.overall == int(round(base.overall * HOME_SCHOOL_PENALTY))
    assert home.overall < base.overall


def test_default_flag_keeps_score():
    assert PhDMatchEngine.compute(**KW).overall == PhDMatchEngine.compute(
        **{**KW, "is_home_school": False}
    ).overall


def test_is_home_school_helper():
    assert _is_home_school("北京航空航天大学（本校）", "北航·本校导师（自动化/AI/机器人，待确认）")
    assert not _is_home_school("中国石油大学（北京）", "中石大·导师")
    assert not _is_home_school("北京科技大学", "北科大导师")
