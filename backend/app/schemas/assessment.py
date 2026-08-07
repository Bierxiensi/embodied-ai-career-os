"""SkillAssessment Pydantic 响应模型。

Reviewer Agent 评估结果，对前端展示评估依据。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SkillAssessmentOut(BaseModel):
    """技能评估响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    skill_id: int
    task_id: int | None = None
    old_level: int
    new_level: int
    confidence: float
    reason: str
    evidence_score: int
    created_at: datetime
