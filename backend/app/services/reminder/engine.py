"""提醒引擎 —— 读数据 → 选模板 → 调通道 → 发推送。

S6 修复（RAG #7/#8）：
- send_morning/send_evening：查 Skill 表取真实 level/target_level，替换硬编码 1/4
- send_morning：加日期过滤，优先推今日创建的待办任务
- send_comeback：加"已提醒"防重复（文件标记），同一断连期只推一次，用户产生新活动后重置
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import func

from app.core.config import settings
from app.db.base import SessionLocal
from app.services.reminder.channels import CHANNELS
from app.services.reminder.templates import (
    comeback_template,
    evening_template,
    morning_template,
)

# comeback 已提醒标记文件（持久化，避免进程重启后重复推）
# 路径与 .github_last_sync 同级，便于备份
_COMEBACK_FLAG_FILE = Path(settings.github_last_sync_file).parent / ".comeback_sent"


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

    # ------------------------------------------------------------------
    # 辅助：按 skill_name 查 Skill 表取真实 level/target_level
    # ------------------------------------------------------------------
    @staticmethod
    def _lookup_skill_levels(db, skill_name: str | None) -> tuple[int, int]:
        """查 Skill 表返回 (current_level, target_level)。未找到则返回 (0, 5)。

        S6 修复：原 send_morning/send_evening 硬编码 current=1/target=4，
        与用户真实技能状态脱节，导致推送内容误导。
        """
        if not skill_name:
            return 0, 5
        from app.models.skill import Skill

        skill = db.query(Skill).filter(Skill.name == skill_name).first()
        if skill is None:
            return 0, 5
        return int(skill.level or 0), int(skill.target_level or 5)

    def send_morning(self) -> bool:
        """早间推送：今日最新 todo 任务。

        S6 修复：加日期过滤，优先推今日创建任务；查真实技能等级。
        """
        db = SessionLocal()
        try:
            from app.models.task import Task

            today = datetime.utcnow().date()
            # 优先今日创建的待办；无则回退到最近的待办
            task = (
                db.query(Task)
                .filter(Task.status.in_(["todo", "doing"]))
                .filter(func.date(Task.created_at) == today)
                .order_by(Task.created_at.desc())
                .first()
            )
            if task is None:
                task = db.query(Task).filter(
                    Task.status.in_(["todo", "doing"])
                ).order_by(Task.created_at.desc()).first()

            if task is None:
                return self._channel.send(
                    "☀️ 今日学习",
                    "暂无待办任务。打开 Dashboard 让 Planner 生成一个吧！"
                )

            skill_name = task.skill_name or "Unknown"
            current_level, target_level = self._lookup_skill_levels(db, skill_name)
            title, body = morning_template(
                task_title=task.title,
                skill_name=skill_name,
                current_level=current_level,
                target_level=target_level,
                duration=task.duration or 30,
            )
            return self._channel.send(title, body)
        finally:
            db.close()

    def send_evening(self) -> bool:
        """晚间检查：今天有完成任务吗？

        S6 修复：查真实技能等级（替换硬编码）。
        """
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
            current_level, target_level = self._lookup_skill_levels(db, skill_name)
            title, body = evening_template(
                task_title=task.title,
                skill_name=skill_name,
            )
            return self._channel.send(title, body)
        finally:
            db.close()

    def send_comeback(self) -> bool | None:
        """中断恢复检测。>N 天无活动时推送，否则返回 None（不发）。

        S6 修复（RAG #8）：加"已提醒"防重复。
        - 推送成功后写标记文件记录推送时间
        - 若用户在推送后产生了新 LearningLog（created_at > 上次推送时间），
          视为"已回来"，清除标记，允许下次断连再推
        - 否则跳过（同一断连期不每天重复推）
        """
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

            # 防重复：若上次推送后用户无新活动，则跳过
            last_sent = _load_comeback_sent()
            if last_sent is not None and last_log.created_at < last_sent:
                # 用户在推送后没有产生新活动 → 已提醒过这次断连，跳过
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
            sent = self._channel.send(title, body)
            # 推送成功才写标记，失败则不写（下次可重试）
            if sent:
                _save_comeback_sent(datetime.utcnow())
            return sent
        finally:
            db.close()


def _load_comeback_sent() -> datetime | None:
    """读取上次 comeback 推送时间。无标记返回 None。"""
    try:
        if not _COMEBACK_FLAG_FILE.exists():
            return None
        data = json.loads(_COMEBACK_FLAG_FILE.read_text(encoding="utf-8"))
        return datetime.fromisoformat(data.get("sent_at"))
    except Exception:
        return None


def _save_comeback_sent(sent_at: datetime) -> None:
    """写入 comeback 推送标记。"""
    try:
        _COMEBACK_FLAG_FILE.write_text(
            json.dumps({"sent_at": sent_at.isoformat()}),
            encoding="utf-8",
        )
    except Exception:
        # 标记写入失败不阻断推送流程（最坏情况是重复推一次）
        pass
