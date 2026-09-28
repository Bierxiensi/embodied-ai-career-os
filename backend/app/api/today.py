"""GET /api/today —— 今日单聚合端点（spec §4.4，FreeLingo 式）。

前端一次取齐：今日施工单 + 今日学习日志 + 容量预检。
各分区独立兜底：辅助数据失败回空，不让整端点 500（spec §5.1）。
计划 2 将追加 review 区（SM-2 到期队列）——本版不预埋假字段。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.plan import build_today_payload
from app.core.capacity import assert_plan_capacity, daily_study_minutes
from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.learning_log import LearningLog
from app.schemas.learning_log import LearningLogOut

router = APIRouter(prefix="/today", tags=["today"])


def _planned_minutes(payload: dict) -> int:
    """今日计划分钟：取 plan_days.est_minutes（施工单 payload 里唯一的真实
    「当日计划分钟」字段）；缺失时回退 tasks.duration 求和，再缺回退 0。

    容量预检绝不因字段缺失抛错（spec §2.4 前置预检不能把端点打挂）。
    """
    try:
        est = (payload.get("day") or {}).get("est_minutes")
        if est is not None:
            return max(0, int(est))
    except (TypeError, ValueError):
        pass
    total = 0
    for t in payload.get("tasks") or []:
        try:
            total += int(t.get("duration") or 0)
        except (TypeError, ValueError, AttributeError):
            continue
    return max(0, total)


@router.get("")
def get_today(day: int | None = None, db: Session = Depends(get_db)) -> ApiResponse[dict]:
    """今日聚合：today（施工单/风险/ROI 原样透传）+ 今日日志 + 容量预检。"""
    payload = build_today_payload(day=day, db=db)  # 失败自然抛出（同 /api/plan/today 语义）

    logs = (
        db.query(LearningLog)
        .order_by(LearningLog.created_at.desc())
        .limit(20)
        .all()
    )
    logs_out = [LearningLogOut.model_validate(x) for x in logs]

    capacity = assert_plan_capacity(
        planned_minutes=_planned_minutes(payload),
        available_minutes=daily_study_minutes(),
    )

    return ok(
        {
            "today": payload,
            "learning_logs_today": logs_out,
            "capacity": capacity,
        }
    )
