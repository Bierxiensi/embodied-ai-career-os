"""APScheduler 生命周期管理。

FastAPI lifespan 中调用 start_scheduler()，shutdown 时自动停止。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_scheduler = None


def start_scheduler() -> None:
    """启动 APScheduler，注册三段时间点 job。"""
    global _scheduler

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.warning(
            "APScheduler not installed. Install with: pip install apscheduler. "
            "Reminder scheduler disabled."
        )
        return

    from app.core.config import settings
    from app.services.reminder.engine import ReminderEngine

    engine = ReminderEngine()

    morning_h, morning_m = _parse_time(settings.reminder_morning_time)
    evening_h, evening_m = _parse_time(settings.reminder_evening_time)

    _scheduler = BackgroundScheduler(timezone=settings.reminder_timezone)
    _scheduler.add_job(
        engine.send_morning,
        "cron", hour=morning_h, minute=morning_m,
        id="reminder_morning",
    )
    _scheduler.add_job(
        engine.send_evening,
        "cron", hour=evening_h, minute=evening_m,
        id="reminder_evening",
    )
    _scheduler.add_job(
        engine.send_comeback,
        "cron", hour=10, minute=0,
        id="reminder_comeback",
    )
    # ---- V2: GitHub 同步 Job ----
    from app.services.github.sync import sync_new_commits
    _scheduler.add_job(
        lambda: sync_new_commits(),
        "interval",
        minutes=settings.github_poll_interval_minutes,
        id="github_sync",
    )
    # ---------------------------
    _scheduler.start()
    logger.info(
        "Reminder scheduler started (morning=%s, evening=%s)",
        settings.reminder_morning_time, settings.reminder_evening_time,
    )


def _parse_time(time_str: str) -> tuple[int, int]:
    """解析 'HH:MM' 字符串为 (hour, minute)。"""
    parts = time_str.strip().split(":")
    return int(parts[0]), int(parts[1])
