"""提醒消息模板。

每个模板函数接收数据 dict，返回 (title, body) 字符串对。
"""

from __future__ import annotations


def morning_template(task_title: str, skill_name: str,
                     current_level: int, target_level: int,
                     duration: int) -> tuple[str, str]:
    """早间任务推送模板。"""
    bar = "█" * current_level + "░" * (target_level - current_level)
    title = "☀️ 今日学习任务"
    body = (
        f"📌 {task_title}\n"
        f"   技能：{skill_name}\n"
        f"   预计 {duration} 分钟\n\n"
        f"📊 {skill_name} Lv{current_level} {bar} → Lv{target_level}\n"
    )
    return title, body


def evening_template(task_title: str, skill_name: str) -> tuple[str, str]:
    """晚间检查模板。"""
    title = "🌙 今日学习回顾"
    body = (
        f"{task_title}\n\n"
        f"完成了吗？回 \"1\"=完成  \"2\"=部分  \"3\"=没做"
    )
    return title, body


def comeback_template(days_away: int, last_task: str,
                      last_skill: str, suggestion: str) -> tuple[str, str]:
    """中断恢复模板。"""
    title = f"👋 {days_away} 天不见了"
    body = (
        f"离开前：{last_task}\n"
        f"技能：{last_skill}\n\n"
        f"🔁 今天建议：{suggestion}"
    )
    return title, body
