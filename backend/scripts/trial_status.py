"""试用期信号仪表（spec 2026-09-29-trial-protocol-design §3）。

只读：仅 SELECT，零写入 dev 库。五项输出：
  连续活跃天数 / quiz 覆盖率(M2 口径) / 覆盖率历史读数(读错题集每周五自查表) /
  错题条数 / 到期卡数+最近自查日期

用法：cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/trial_status.py
"""

from __future__ import annotations

import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# 直跑（python scripts/trial_status.py）时 sys.path[0]=backend/scripts，
# 需补 backend 根才能 import app（镜像 scripts/clean_demo_learning_logs.py 先例）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# backend/scripts/ → parents[1]=backend, parents[2]=仓库根
_TRIAL_MD = Path(__file__).resolve().parents[2] / "docs" / "试用错题集.md"

_DATE_RE = re.compile(r"^\[?(\d{4}-\d{2}-\d{2})\]?$")
_ENTRY_RE = re.compile(r"^- \[\d{4}-\d{2}-\d{2}\]")
_FENCE_RE = re.compile(r"^```")


def to_local_date(dt: datetime) -> date:
    """naive 视为 UTC（normalizeUtc 口径），转本地日；aware 先归一到 UTC 再转本地。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().date()


def active_streak(dates: set[date], today: date) -> int:
    """从 today 严格往回数连续天数；today 不在集合中即 0（spec §3 字面口径）。"""
    n = 0
    cur = today
    while cur in dates:
        n += 1
        cur = cur.fromordinal(cur.toordinal() - 1)
    return n


def local_coverage(numerator: int, denominator: int) -> str:
    """M2 口径展示；分母 0 输出「暂无题目」不许除零。"""
    if denominator <= 0:
        return "暂无题目"
    return f"{numerator}/{denominator} ({numerator / denominator * 100:.1f}%)"


def _lines_outside_fences(text: str):
    """跳过 ``` 围栏内所有行（示例不参与解析）。"""
    in_fence = False
    for line in text.splitlines():
        if _FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield line


def parse_friday_readings(md_text: str) -> list[tuple[date, float]]:
    """解析每周五自查表的覆盖率列；表为空/无 % 列返回 []。"""
    rows: list[tuple[date, float]] = []
    for line in _lines_outside_fences(md_text):
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        m = _DATE_RE.match(cells[0])
        pct = re.fullmatch(r"(\d+(?:\.\d+)?)%", cells[1])
        if m and pct:
            rows.append((date.fromisoformat(m.group(1)), float(pct.group(1))))
    return rows


def count_entries(md_text: str) -> int:
    """有效问题条目数：围栏外、行首 `- [YYYY-MM-DD] `。"""
    return sum(1 for line in _lines_outside_fences(md_text) if _ENTRY_RE.match(line))


def _read_trial_md() -> str:
    """读错题集；文件不存在返回空串（输出侧按空处理，不抛）。"""
    try:
        return _TRIAL_MD.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _streak_dates(db) -> set[date]:
    """三源活跃日（本地日）：learning_log / review_log / verified_at。"""
    from app.models.learning_log import LearningLog
    from app.models.mastery import ReviewLog, UnitItem

    dates: set[date] = set()
    for (ts,) in db.query(LearningLog.created_at).all():
        if ts is not None:
            dates.add(to_local_date(ts))
    for (ts,) in db.query(ReviewLog.reviewed_at).all():
        if ts is not None:
            dates.add(to_local_date(ts))
    for (ts,) in db.query(UnitItem.verified_at).all():
        if ts is not None:
            dates.add(to_local_date(ts))
    return dates


def main() -> int:
    from app.db.base import SessionLocal
    from app.models.mastery import ReviewCard, UnitItem

    db = SessionLocal()
    try:
        # 1) 连续活跃天数
        streak = active_streak(_streak_dates(db), date.today())

        # 2) quiz 覆盖率（M2 口径）
        denom = db.query(UnitItem).filter(UnitItem.kind == "quiz_q").count()
        num = (
            db.query(UnitItem)
            .filter(UnitItem.kind == "quiz_q", UnitItem.is_verified.is_(True))
            .count()
        )

        # 3/4/5 覆盖率历史 + 错题条数 + 最近自查（错题集）
        md = _read_trial_md()
        readings = parse_friday_readings(md)
        entries = count_entries(md)

        # 历史读数展示
        if readings:
            pcts = [f"{d.isoformat()}={p}%" for d, p in readings]
            delta = (
                f"（最近差值 {readings[-1][1] - readings[-2][1]:+.1f}）"
                if len(readings) >= 2
                else "（仅 1 次读数）"
            )
            hist = " ".join(pcts) + " " + delta
        else:
            hist = "暂无历史读数"

        # 5) 到期卡数（镜像 today.py review 区查询）
        now = datetime.now(timezone.utc)
        due = (
            db.query(ReviewCard)
            .filter(ReviewCard.card_status == "active", ReviewCard.due_at <= now)
            .count()
        )
        last_check = readings[-1][0].isoformat() if readings else "无"

        print("===== trial_status =====")
        print(f"连续活跃天数: {streak}")
        print(f"quiz 覆盖率: {local_coverage(num, denom)}")
        print(f"覆盖率历史读数: {hist}")
        print(f"错题条数: {entries}")
        print(f"到期卡数: {due} · 最近自查: {last_check}")
        print("========================")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
