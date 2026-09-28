# backend/tests/test_sm2.py
"""简化 SM-2（spec §4.1 / 决策 D6）：4 档评分、EF clamp、连续 2 次好→fixed。"""

from app.core.sm2 import initial_card, schedule


def test_initial():
    s = initial_card()
    assert s == {"interval_days": 1.0, "ef": 2.5, "lapse_count": 0, "good_streak": 0, "card_status": "active"}


def test_again_resets_and_drops_ef():
    s = schedule(initial_card(), "again")
    assert s["interval_days"] == 0.0
    assert s["lapse_count"] == 1
    assert s["good_streak"] == 0
    assert s["ef"] == 2.3  # 2.5 - 0.2
    assert s["card_status"] == "active"


def test_hard_short_step_drops_ef():
    s = schedule(initial_card(), "hard")
    assert s["interval_days"] == 1.2  # 1.0 * 1.2
    assert s["ef"] == 2.35  # 2.5 - 0.15
    assert s["good_streak"] == 0


def test_good_graduates_intervals():
    s = initial_card()
    s = schedule(s, "good")
    assert s["interval_days"] == 1.0  # <1 → 1
    s = schedule(s, "good")
    assert s["interval_days"] == 3.0  # <3 → 3
    s = schedule(s, "good")
    assert s["interval_days"] == 3.0 * 2.5  # ×ef


def test_easy_boosts_ef_clamped():
    s = schedule(schedule(initial_card(), "easy"), "easy")
    assert s["ef"] == 2.5  # clamp 上限


def test_ef_floor():
    s = initial_card()
    for _ in range(10):
        s = schedule(s, "again")
    assert s["ef"] == 1.3  # clamp 下限


def test_two_good_streak_fixes_card():
    s = schedule(initial_card(), "good")
    assert s["card_status"] == "active"
    s = schedule(s, "good")
    assert s["card_status"] == "fixed"
    assert s["good_streak"] == 2


def test_fixed_card_can_lapse_back():
    s = initial_card()
    s = schedule(schedule(s, "good"), "good")  # fixed
    s = schedule(s, "again")
    assert s["card_status"] == "active"
    assert s["good_streak"] == 0
