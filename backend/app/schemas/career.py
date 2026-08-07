"""Career Pydantic 请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CareerOut(BaseModel):
    """Career 响应模型。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    target_role: str
    salary_target: int | None = None
    timeframe: str | None = None
    notes: str | None = None


class CareerUpdate(BaseModel):
    """Career 更新请求。全字段可选，支持部分更新。"""

    target_role: str | None = None
    salary_target: int | None = None
    timeframe: str | None = None
    notes: str | None = None
