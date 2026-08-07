"""Skill Pydantic 请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SkillOut(BaseModel):
    """Skill 响应模型。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str | None = None
    level: int = Field(ge=0, le=5)
    target_level: int = Field(ge=0, le=5)
    evidence: list[str] = []

    @field_validator("evidence", mode="before")
    @classmethod
    def _none_to_list(cls, v):
        """数据库 JSON 字段可能为 None，统一转为空列表。"""

        return v or []


class SkillPatch(BaseModel):
    """Skill 部分更新请求。

    Day6 仅开放 level 与 evidence 更新（name/category/target_level 不动，
    避免误改目标架构）。未来 Reviewer Agent 通过此接口回写等级。
    """

    level: int | None = Field(default=None, ge=0, le=5)
    evidence: list[str] | None = None
