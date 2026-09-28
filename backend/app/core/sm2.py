"""简化 SM-2 间隔重复调度（2026-09-24 决策 D6）。

纯函数、不碰时钟：调用方拿 interval_days 自己算 due_at。
FSRS-6 为后置增强（spec §4.1），先用 SM-2 跑通闭环。
card_status：连续 2 次 good/easy → fixed（默认不再排入）；again → 打回 active。
"""

from __future__ import annotations

from typing import TypedDict

EF_FLOOR = 1.3
EF_CEIL = 2.5
FIXED_STREAK = 2


class CardState(TypedDict):
    interval_days: float
    ef: float
    lapse_count: int
    good_streak: int
    card_status: str


def initial_card() -> CardState:
    return {
        "interval_days": 1.0,
        "ef": 2.5,
        "lapse_count": 0,
        "good_streak": 0,
        "card_status": "active",
    }


def _clamp_ef(ef: float) -> float:
    return max(EF_FLOOR, min(EF_CEIL, ef))


def schedule(state: CardState, rating: str) -> CardState:
    """按 4 档评分推进一张卡。rating ∈ again/hard/good/easy，非法值抛 ValueError。"""
    if rating not in ("again", "hard", "good", "easy"):
        raise ValueError(f"invalid rating: {rating}")

    interval = float(state["interval_days"])
    ef = float(state["ef"])
    lapses = int(state["lapse_count"])
    streak = int(state["good_streak"])
    status = state["card_status"]

    if rating == "again":
        interval, lapses, streak, status = 0.0, lapses + 1, 0, "active"
        ef = _clamp_ef(ef - 0.2)
    elif rating == "hard":
        interval = interval * 1.2
        ef = _clamp_ef(ef - 0.15)
        streak = 0
    elif rating == "good":
        # 毕业阶梯 1 → 3 → ×ef。首档判据需带 streak：新卡 interval 恰为 1.0，
        # 仅凭 interval<1 会把首次 good 直接推到 3（brief 测试 test_good_graduates_intervals 约束）。
        if streak == 0 and interval <= 1.0:
            interval = 1.0
        elif interval < 3:
            interval = 3.0
        else:
            interval = interval * ef
        streak += 1
        status = "fixed" if streak >= FIXED_STREAK else "active"
    else:  # easy
        if interval < 1:
            interval = 1.0
        interval = interval * ef * 1.3
        ef = _clamp_ef(ef + 0.15)
        streak += 1
        status = "fixed" if streak >= FIXED_STREAK else "active"

    return {
        "interval_days": round(interval, 4),
        "ef": round(ef, 4),
        "lapse_count": lapses,
        "good_streak": streak,
        "card_status": status,
    }
