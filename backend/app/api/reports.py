"""日报 / 周报 API（Batch 4）。

端点：
- GET  /api/reports/daily          即时构建日报（不落库、不推送）
- GET  /api/reports/weekly         即时构建周报
- GET  /api/reports/history        归档历史（可按 kind 过滤）
- GET  /api/reports/followups      待跟进投递（next_action 到期 / 停滞超期）
- GET  /api/reports/schedule       调度配置与已注册 job
- POST /api/reports/daily/send     生成并推送日报（force=true 可重推）
- POST /api/reports/weekly/send    生成并推送周报

计算全部走 services/report（纯规则），推送复用 reminder 通道。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.response import ok
from app.db.base import get_db
from app.schemas.report import (
    FollowupOut,
    JobInfoOut,
    ReportLogOut,
    ReportOut,
    ScheduleOut,
    SendResultOut,
)
from app.services.reminder.scheduler import jobs_info
from app.services.report.engine import (
    REPORT_DAILY,
    REPORT_WEEKLY,
    due_followups,
)
from app.services.report.service import (
    REPORT_KINDS,
    list_reports,
    preview,
    send_report,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _check_kind(kind: str) -> str:
    if kind not in REPORT_KINDS:
        raise HTTPException(status_code=400, detail=f"kind 必须为 {REPORT_KINDS} 之一")
    return kind


@router.get("/daily")
def get_daily():
    """即时构建日报（含推荐岗位 / 简历动作 / 面试题 / 任务 / 投递 / 今日优先）。"""
    return ok(ReportOut.model_validate(preview(REPORT_DAILY)).model_dump())


@router.get("/weekly")
def get_weekly():
    """即时构建周报（投递统计 / 能力差距 / 项目进度 / 面试汇总 / 下周任务 / 博士积累）。"""
    return ok(ReportOut.model_validate(preview(REPORT_WEEKLY)).model_dump())


@router.get("/history")
def get_history(
    kind: str | None = Query(default=None, description="daily | weekly，缺省全部"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """归档报告历史（生成时间降序）。"""
    if kind:
        _check_kind(kind)
    rows = list_reports(kind=kind, limit=limit)
    return ok([ReportLogOut.model_validate(r).model_dump() for r in rows])


@router.get("/followups")
def get_followups(db: Session = Depends(get_db)):
    """待跟进投递：``next_action`` 到期，或 applied/screening 停滞超过阈值。"""
    due = due_followups(db, stale_days=settings.report_followup_stale_days)
    return ok({
        "stale_days": settings.report_followup_stale_days,
        "count": len(due),
        "items": [FollowupOut.model_validate(d).model_dump() for d in due],
    })


@router.get("/schedule")
def get_schedule():
    """报告调度配置 + 调度器当前注册的 job（含下次运行时间）。"""
    payload = ScheduleOut(
        enabled=settings.report_enabled,
        daily_time=settings.report_daily_time,
        weekly_day=settings.report_weekly_day,
        weekly_time=settings.report_weekly_time,
        followup_time=settings.report_followup_time,
        followup_stale_days=settings.report_followup_stale_days,
        channel=settings.reminder_channel,
        jobs=[JobInfoOut.model_validate(j) for j in jobs_info()],
    )
    return ok(payload.model_dump())


@router.post("/{kind}/send", include_in_schema=False)
def send(kind: str, force: bool = Query(default=False, description="已发送是否强制重推")):
    """DEPRECATED（2026-09-24 收敛）：零前端消费，保数据不删路由。

    生成并推送一份报告（幂等：同 period_key 已发送则跳过，除非 force）。
    """
    _check_kind(kind)
    result = send_report(kind, force=force)
    payload = SendResultOut.model_validate(result)
    msg = "已推送" if payload.sent else (payload.reason or "未推送")
    return ok(payload.model_dump(), msg)
