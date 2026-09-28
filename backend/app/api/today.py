"""GET /api/today —— 今日单聚合端点（spec §4.4，FreeLingo 式）。

前端一次取齐：今日施工单 + 近 24h 学习日志（`learning_logs_24h`）+ 容量预检。
防御边界如实：日志区与容量区不依赖 payload 的具体形态（缺字段自兜底、不抛）；
today 主 payload（/api/plan/today 语义）失败**按设计向外抛**，由全局异常处理
返回错误响应 —— 本端点不做「各分区独立兜底、不让整端点 500」。
计划 2 追加 review 区（SM-2 到期队列，`due_count` + 至多 10 张 `due_cards`）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.plan import build_today_payload
from app.core.capacity import assert_plan_capacity, daily_study_minutes
from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.learning_log import LearningLog
from app.models.mastery import ReviewCard
from app.schemas.learning_log import LearningLogOut
from app.schemas.mastery import ReviewCardOut

router = APIRouter(prefix="/today", tags=["today"])


def _planned_minutes(payload: dict) -> int:
    """今日计划分钟：口径 =「今天的任务总时长 vs 今日可学预算」。

    优先取当日任务 `tasks[].duration` 求和（任务列表非空时）。只有**无任务**
    才回退 `day.est_minutes` —— plan_30d 的 est_minutes 是整日课程估计
    （180–420 分钟），拿它做容量预检会永远 ok=False，徽章成了永久噪音；
    两者皆缺回退 0。

    容量预检绝不因字段缺失抛错（spec §2.4 前置预检不能把端点打挂）。
    """
    tasks = payload.get("tasks") or []
    if tasks:
        total = 0
        for t in tasks:
            try:
                total += int(t.get("duration") or 0)
            except (TypeError, ValueError, AttributeError):
                continue
        return max(0, total)
    try:
        est = (payload.get("day") or {}).get("est_minutes")
        if est is not None:
            return max(0, int(est))
    except (TypeError, ValueError):
        pass
    return 0


@router.get("")
def get_today(day: int | None = None, db: Session = Depends(get_db)) -> ApiResponse[dict]:
    """今日聚合：today（施工单/风险/ROI 原样透传）+ 近 24h 日志 + 容量预检。"""
    payload = build_today_payload(day=day, db=db)  # 失败自然抛出（同 /api/plan/today 语义）

    # `learning_logs_24h` = 滚动 24h 窗口，不是「本地日历日的今日」（命名如实，
    # 见 STYLE.md 口径登记）：created_at 是 naive UTC，若按 utcnow().date() 切日历天，
    # 本地时区晚间写入的日志会被切掉（naive-UTC 与本地日错位的陷阱），
    # 且跨午夜的「今天」会突然清空。滚动窗口对任意时区语义一致；
    # limit(20) 仅是返回条数的安全上限。
    cutoff = datetime.utcnow() - timedelta(hours=24)
    logs = (
        db.query(LearningLog)
        .filter(LearningLog.created_at >= cutoff)
        .order_by(LearningLog.created_at.desc())
        .limit(20)
        .all()
    )
    logs_out = [LearningLogOut.model_validate(x) for x in logs]

    capacity = assert_plan_capacity(
        planned_minutes=_planned_minutes(payload),
        available_minutes=daily_study_minutes(),
    )

    # review 区：SM-2 到期队列（active 且 due_at 已过），按到期时间升序取前 10 展示，
    # due_count 是全量到期数（展示截断 ≠ 队列长度）。due_at 比较用 aware UTC ——
    # SQLite 存取会把 aware/naive 都规整成同口径字符串，两侧一致即可比。
    now = datetime.now(timezone.utc)
    due_q = db.query(ReviewCard).filter(
        ReviewCard.card_status == "active", ReviewCard.due_at <= now
    )
    due_cards = due_q.order_by(ReviewCard.due_at).limit(10).all()
    review = {
        "due_count": due_q.count(),
        "due_cards": [ReviewCardOut.model_validate(c) for c in due_cards],
    }

    return ok(
        {
            "today": payload,
            "learning_logs_24h": logs_out,
            "capacity": capacity,
            "review": review,
        }
    )
