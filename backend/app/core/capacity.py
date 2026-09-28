"""容量预检（spec §2.4）：每天 1-2 小时是产品级硬约束，不是软提醒。

2026-09-24 前置裁决口径：每日学习 60-120 分钟可配（DAILY_STUDY_MINUTES，越界钳制）。
"""

from __future__ import annotations

import os
from typing import TypedDict


class CapacityCheck(TypedDict):
    """容量预检结果（GET /api/today 的 capacity 槽位契约）。"""

    ok: bool
    available_minutes: int
    planned_minutes: int
    shortfall_minutes: int
    suggestion: str


def daily_study_minutes() -> int:
    """每日学习分钟预算：env 可配，钳制到 [60, 120]（裁决口径）。"""
    try:
        raw = int(os.getenv("DAILY_STUDY_MINUTES", "90"))
    except ValueError:
        raw = 90
    return max(60, min(120, raw))


def assert_plan_capacity(
    planned_minutes: int, available_minutes: int | None = None
) -> CapacityCheck:
    """容量预检。超限**显式拒绝**并给最短可行周期建议（禁止静默截断）。

    `planned_minutes` 容错：None / 0 均按 0 处理，缺字段不得让端点 500。
    """
    available = available_minutes if available_minutes is not None else daily_study_minutes()
    planned = max(0, int(planned_minutes or 0))
    shortfall = max(0, planned - available)
    ok = shortfall == 0
    suggestion = ""
    if not ok:
        days = -(-planned // available)  # 向上取整
        suggestion = (
            f"计划超出单日容量 {shortfall} 分钟，最短需拆成 {days} 天完成"
            f"（每天 ≤{available} 分钟）"
        )
    return {
        "ok": ok,
        "available_minutes": available,
        "planned_minutes": planned,
        "shortfall_minutes": shortfall,
        "suggestion": suggestion,
    }
