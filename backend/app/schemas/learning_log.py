"""LearningLog Pydantic 请求/响应模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LearningLogCreate(BaseModel):
    """创建学习日志请求。

    Day7：由"完成并复盘"表单提交，content 必填，artifact_url 可选。
    """

    task_id: int | None = None
    content: str = Field(min_length=1, max_length=2000)
    duration_minutes: int | None = Field(default=None, ge=1, le=480)
    artifact_url: str | None = Field(default=None, max_length=500)


class LearningLogOut(BaseModel):
    """学习日志响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int | None = None
    content: str
    duration_minutes: int | None = None
    artifact_url: str | None = None
    created_at: datetime
