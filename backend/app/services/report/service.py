"""报告编排服务（Batch 4）。

职责：**build → 落库（ReportLog）→ 推送（复用 reminder 通道）→ 标记 sent**。

幂等策略（避免调度器随 dev server 热重载重复推送）：

- 同一 ``(kind, period_key)`` 已 ``sent=True`` → 默认跳过，``force=True`` 可强制重推；
- 已落库但 ``sent=False``（上次推送失败）→ 重试推送并更新记录。

通道构造统一走 ``reminder.channels.build_channel``，与提醒引擎共用一份逻辑。
"""

from __future__ import annotations

import logging
from datetime import date, datetime

from app.core.config import settings
from app.db.base import SessionLocal
from app.models.report_log import ReportLog
from app.services.reminder.channels import build_channel
from app.services.report.engine import (
    REPORT_DAILY,
    REPORT_WEEKLY,
    ReportData,
    build_daily,
    build_weekly,
    due_followups,
    render,
)

logger = logging.getLogger(__name__)

REPORT_KINDS = (REPORT_DAILY, REPORT_WEEKLY)


# ─────────────────────────── 构建 / 预览 ───────────────────────────

def _build(db, kind: str, today: date | None = None) -> ReportData:
    if kind == REPORT_WEEKLY:
        return build_weekly(db, today)
    return build_daily(db, today, stale_days=settings.report_followup_stale_days)


def preview(kind: str, today: date | None = None) -> dict:
    """即时构建报告（不落库、不推送），供前端预览。"""
    db = SessionLocal()
    try:
        return _build(db, kind, today).to_dict()
    finally:
        db.close()


# ─────────────────────────── 落库 ───────────────────────────

def _persist(db, data: ReportData) -> ReportLog:
    """按 ``(kind, period_key)`` upsert 归档记录。"""
    title, body = render(data)
    sections = [{"key": s.key, "title": s.title, "lines": s.lines} for s in data.sections]

    row = (
        db.query(ReportLog)
        .filter(ReportLog.kind == data.kind, ReportLog.period_key == data.period_key)
        .first()
    )
    if row is None:
        row = ReportLog(
            kind=data.kind,
            period_key=data.period_key,
            title=title,
            body=body,
            sections=sections,
            metrics=data.metrics,
            sent=False,
        )
        db.add(row)
    else:
        row.title = title
        row.body = body
        row.sections = sections
        row.metrics = data.metrics
        row.generated_at = data.generated_at

    db.commit()
    db.refresh(row)
    return row


def _row_to_dict(row: ReportLog) -> dict:
    return {
        "id": row.id,
        "kind": row.kind,
        "period_key": row.period_key,
        "title": row.title,
        "body": row.body,
        "sections": row.sections,
        "metrics": row.metrics,
        "sent": bool(row.sent),
        "sent_at": row.sent_at.isoformat() if row.sent_at else None,
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
    }


def list_reports(kind: str | None = None, limit: int = 20) -> list[dict]:
    """归档历史（按生成时间降序）。"""
    db = SessionLocal()
    try:
        q = db.query(ReportLog)
        if kind:
            q = q.filter(ReportLog.kind == kind)
        rows = (
            q.order_by(ReportLog.generated_at.desc(), ReportLog.id.desc())
            .limit(limit)
            .all()
        )
        return [_row_to_dict(r) for r in rows]
    finally:
        db.close()


# ─────────────────────────── 推送 ───────────────────────────

def send_report(
    kind: str,
    force: bool = False,
    today: date | None = None,
) -> dict:
    """构建并推送一份报告。

    返回 ``{kind, period_key, sent, skipped, reason, title}``。
    """
    if kind not in REPORT_KINDS:
        raise ValueError(f"kind 必须为 {REPORT_KINDS} 之一，收到：{kind}")

    db = SessionLocal()
    try:
        data = _build(db, kind, today)
        row = _persist(db, data)

        if row.sent and not force:
            return {
                "kind": kind,
                "period_key": data.period_key,
                "sent": False,
                "skipped": True,
                "reason": "本期报告已发送（force=true 可重推）",
                "title": row.title,
            }

        sent = bool(build_channel().send(row.title, row.body))
        if sent:
            row.sent = True
            row.sent_at = datetime.utcnow()
            db.commit()

        return {
            "kind": kind,
            "period_key": data.period_key,
            "sent": sent,
            "skipped": False,
            "reason": None if sent else "通道推送失败，已落库待重试",
            "title": row.title,
        }
    finally:
        db.close()


def send_daily_report(today: date | None = None) -> bool:
    """调度器入口：日报（每日 08:30）。"""
    if not settings.report_enabled:
        logger.info("report_enabled=false，跳过日报")
        return False
    return bool(send_report(REPORT_DAILY, today=today).get("sent"))


def send_weekly_report(today: date | None = None) -> bool:
    """调度器入口：周报（每周一 09:00）。"""
    if not settings.report_enabled:
        logger.info("report_enabled=false，跳过周报")
        return False
    return bool(send_report(REPORT_WEEKLY, today=today).get("sent"))


def remind_followups(today: date | None = None) -> bool:
    """调度器入口：投递跟进提醒（每日 10:00）。

    触发条件见 ``engine.due_followups``：``next_action`` 到期，或
    applied/screening 状态停滞超过 ``report_followup_stale_days`` 天。
    无待跟进时返回 False（不发空提醒）。
    """
    if not settings.report_enabled:
        return False

    db = SessionLocal()
    try:
        due = due_followups(db, today, settings.report_followup_stale_days)
        if not due:
            logger.info("无待跟进投递，跳过提醒")
            return False

        lines = [
            f"· {d['company']}（{d['role']}）—— {d['reason']}"
            for d in due
        ]
        title = f"⏰ 投递跟进提醒（{len(due)} 家）"
        body = (
            "以下投递需要跟进：\n"
            + "\n".join(lines)
            + "\n\n建议：优先处理已到期的 HR 沟通与面试邀约，再补投新岗位。"
        )
        return bool(build_channel().send(title, body))
    finally:
        db.close()
