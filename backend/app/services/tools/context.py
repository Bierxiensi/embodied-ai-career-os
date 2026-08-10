"""上下文恢复包生成 —— Markdown 格式，可喂给 WorkBuddy / Obsidian / ChatGPT。"""

from __future__ import annotations

from datetime import datetime

from app.db.base import SessionLocal


def generate_context_pack() -> str:
    """生成当前学习上下文包。

    返回 Markdown 字符串，包含：目标岗位、技能状态、最近任务、最近日志。
    """
    db = SessionLocal()
    try:
        from app.models.career import Career
        from app.models.skill import Skill
        from app.models.task import Task
        from app.models.learning_log import LearningLog

        career = db.query(Career).first()
        role = career.target_role if career else "Robot AI Engineer"

        skills = db.query(Skill).order_by(Skill.level - Skill.target_level).all()
        skill_lines = "\n".join(
            f"- {s.name}: Lv{s.level}→Lv{s.target_level}"
            for s in (skills or [])[:8]
        )

        tasks = db.query(Task).order_by(Task.created_at.desc()).limit(3).all()
        task_lines = "\n".join(
            f"- [{t.status}] {t.title} ({t.skill_name}, {t.duration}min)"
            for t in tasks
        )

        logs = db.query(LearningLog).order_by(LearningLog.created_at.desc()).limit(3).all()
        log_lines = "\n".join(
            f"- {log.created_at.strftime('%m-%d %H:%M') if log.created_at else '?'}: "
            f"{log.content[:100]}..."
            for log in logs
        )

        return f"""# Session Context · {datetime.utcnow().strftime('%Y-%m-%d')}

## 目标岗位
{role}

## 技能状态
{skill_lines or '（暂无数据）'}

## 最近任务
{task_lines or '（暂无数据）'}

## 最近学习日志
{log_lines or '（暂无数据）'}

---
由 Embodied AI Career OS 自动生成
"""
    finally:
        db.close()
