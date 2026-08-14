"""SkillAssessment Pydantic 响应模型。

Reviewer Agent 评估结果，对前端展示评估依据。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SkillAssessmentOut(BaseModel):
    """技能评估响应。"""

    model_config = ConfigDict(from_attributes=True)

    # 字段可空：技能未注册 / 未生成评估时，API 层兜底返回空评估而非 500
    id: int | None = None
    skill_id: int | None = None
    task_id: int | None = None
    old_level: int | None = None
    new_level: int | None = None
    confidence: float | None = None
    reason: str = ""
    evidence_score: int | None = None
    created_at: datetime | None = None
