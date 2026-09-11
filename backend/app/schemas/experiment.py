"""实验记录（Experiment）Pydantic 模型。

对应 /api/experiments 系列端点。variants / metrics 为结构化 JSON，
前端直接渲染成对比表（不加额外转换层）。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.experiment import EXPERIMENT_KINDS


class ExperimentOut(BaseModel):
    """实验出参。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_day_id: int | None = None
    day_seq: int
    name: str
    kind: str = "finetune"
    skill_name: str | None = None
    variants: list = []
    metrics: list = []
    conclusion: str | None = None
    artifact_ids: list = []
    created_at: datetime
    updated_at: datetime

    @field_validator("variants", "metrics", "artifact_ids", mode="before")
    @classmethod
    def _none_to_list(cls, v):
        """数据库 JSON 字段可能为 None，统一转空列表。"""

        return v or []


class ExperimentCreate(BaseModel):
    """新增实验。day_seq 必填；variants / metrics 为 JSON 结构。"""

    plan_day_id: int | None = None
    day_seq: int = Field(ge=1, le=30)
    name: str = Field(min_length=1, max_length=200)
    kind: str = Field(default="finetune", pattern="^(finetune|benchmark|ablation)$")
    skill_name: str | None = None
    variants: list | None = None
    metrics: list | None = None
    conclusion: str | None = None
    artifact_ids: list | None = None


class ExperimentPatch(BaseModel):
    """部分更新实验（结论 / 指标等）。"""

    name: str | None = None
    kind: str | None = Field(default=None, pattern="^(finetune|benchmark|ablation)$")
    skill_name: str | None = None
    variants: list | None = None
    metrics: list | None = None
    conclusion: str | None = None
    artifact_ids: list | None = None
    plan_day_id: int | None = None
    day_seq: int | None = Field(default=None, ge=1, le=30)
