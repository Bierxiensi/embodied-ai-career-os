"""APScheduler 生命周期管理。

FastAPI lifespan 中调用 start_scheduler()，shutdown 时调用 stop_scheduler()。
S6 修复：start_scheduler 幂等 + 新增 stop_scheduler 关闭调度器，避免重复启动与资源泄漏。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_scheduler = None


def start_scheduler() -> None:
    """启动 APScheduler，注册三段时间点 job。

    S6 修复：幂等。已启动则直接返回，避免 dev server 热重载或重复调用导致
    重复注册 job（APScheduler 默认会因 job id 冲突抛 ConflictingIdError）。
    """
    global _scheduler

    # 幂等：已启动则跳过
    if _scheduler is not None:
        logger.debug("start_scheduler: scheduler already running, skip.")
        return

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


def stop_scheduler() -> None:
    """停止 APScheduler。

    S6 修复：原缺失 stop 函数，进程退出时调度器线程不被显式关闭。
    幂等：未启动或已停止时直接返回。
    """
    global _scheduler
    if _scheduler is None:
        return
    try:
        _scheduler.shutdown(wait=False)
        logger.info("Reminder scheduler stopped.")
    except Exception as e:  # noqa: BLE001
        # shutdown 可能因调度器状态异常抛错（如已在关闭中），不阻断退出流程
        logger.warning("stop_scheduler: %s", e)
    finally:
        _scheduler = None


def _parse_time(time_str: str) -> tuple[int, int]:
    """解析 'HH:MM' 字符串为 (hour, minute)。"""
    parts = time_str.strip().split(":")
    return int(parts[0]), int(parts[1])
