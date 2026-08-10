"""提醒引擎 —— 读数据 → 选模板 → 调通道 → 发推送。"""

from __future__ import annotations

from datetime import datetime

from app.core.config import settings
from app.db.base import SessionLocal
from app.services.reminder.channels import CHANNELS
from app.services.reminder.templates import (
    comeback_template,
    evening_template,
    morning_template,
)


class ReminderEngine:
    """提醒引擎。每个推送场景一个方法，独立可测。"""

    def __init__(self):
        channel_cls = CHANNELS.get(settings.reminder_channel)
        if channel_cls is None:
            channel_cls = CHANNELS["terminal"]
        if settings.reminder_channel == "serverchan":
            self._channel = channel_cls(settings.reminder_channel_key)
        else:
            self._channel = channel_cls()

    def send_morning(self) -> bool:
        """早间推送：今日最新 todo 任务。"""
        db = SessionLocal()
        try:
            from app.models.task import Task

            task = db.query(Task).filter(
                Task.status.in_(["todo", "doing"])
            ).order_by(Task.created_at.desc()).first()

            if task is None:
                return self._channel.send(
                    "☀️ 今日学习",
                    "暂无待办任务。打开 Dashboard 让 Planner 生成一个吧！"
                )

            skill_name = task.skill_name or "Unknown"
            title, body = morning_template(
                task_title=task.title,
                skill_name=skill_name,
                current_level=1,
                target_level=4,
                duration=task.duration or 30,
            )
            return self._channel.send(title, body)
        finally:
            db.close()

    def send_evening(self) -> bool:
        """晚间检查：今天有完成任务吗？"""
        db = SessionLocal()
        try:
            from app.models.task import Task

            task = db.query(Task).filter(
                Task.status.in_(["todo", "doing"])
            ).order_by(Task.created_at.desc()).first()

            if task is None:
                return self._channel.send(
                    "🌙 今日回顾",
                    "今天没有待办任务。明天让 Planner 生成一个吧！"
                )

            skill_name = task.skill_name or "Unknown"
            title, body = evening_template(
                task_title=task.title,
                skill_name=skill_name,
            )
            return self._channel.send(title, body)
        finally:
            db.close()

    def send_comeback(self) -> bool | None:
        """中断恢复检测。>3 天无活动时推送，否则返回 None（不发）。"""
        db = SessionLocal()
        try:
            from app.models.learning_log import LearningLog

            last_log = db.query(LearningLog).order_by(
                LearningLog.created_at.desc()
            ).first()

            if last_log is None:
                return None  # 从未有过活动，不触发

            days = (datetime.utcnow() - last_log.created_at).days
            if days < settings.reminder_inactivity_days:
                return None

            from app.models.task import Task

            last_task = db.query(Task).order_by(Task.created_at.desc()).first()
            task_title = last_task.title if last_task else "学习"
            skill = last_task.skill_name if last_task else "Unknown"

            title, body = comeback_template(
                days_away=days,
                last_task=task_title,
                last_skill=skill,
                suggestion=f"继续 {task_title}（预计 30 分钟）",
            )
            return self._channel.send(title, body)
        finally:
            db.close()
