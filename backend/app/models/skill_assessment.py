"""技能评估记录模型。

Day7 新增：Reviewer Agent 产出的中间结果，记录每次技能等级变更的依据。
不直接由 Agent 写 Skill 表，而是先产出 SkillAssessment，再由 apply 节点应用。

价值：
- 可追溯：为什么 ROS2 从 1 升到 2？（关联 task_id + reason）
- 可复核：未来接入 Human Feedback，用户可确认/驳回
- 面试展示：Agent 决策链路完整可见
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SkillAssessment(Base):
    """技能评估记录。一次 Reviewer 评估对应一条记录。"""

    __tablename__ = "skill_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联技能（外键）
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )

    # 关联任务（外键，触发本次评估的任务）
    task_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )

    # 评估前等级
    old_level: Mapped[int] = mapped_column(Integer, nullable=False)

    # 评估后等级（可能与 old_level 相同，表示证据不足未升级）
    new_level: Mapped[int] = mapped_column(Integer, nullable=False)

    # 置信度 0-1（基于 evidence score / 100）
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # 评估理由（人类可读，如"完成Isaac环境搭建并运行Example"）
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    # 证据得分（0-100，Reviewer rules 产出）
    evidence_score: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
