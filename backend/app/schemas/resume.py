"""简历线 Pydantic 请求 / 响应模型（Batch 2）。

版本（ResumeVersion）与事实锚点（ResumeFact）分离：
- 事实锚点库是防虚构的唯一权威来源
- 版本是 md 原文，诊断时拿版本 content_md 去事实库校验
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.resume_fact import FACT_CATEGORIES


# ───────────────────────────── 事实锚点 ─────────────────────────────

class ResumeFactCreate(BaseModel):
    """新增事实锚点。category 取 work/project/paper/edu/metric。"""

    category: str
    title: str
    org: str | None = None
    start: str | None = None
    end: str | None = None
    facts: list[str] = []
    source: str | None = None

    def model_post_init(self, __context) -> None:  # noqa: ANN001
        if self.category not in FACT_CATEGORIES:
            raise ValueError(
                f"category 必须为 {FACT_CATEGORIES} 之一，收到：{self.category}"
            )


class ResumeFactOut(BaseModel):
    """事实锚点出参。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    title: str
    org: str | None = None
    start: str | None = None
    end: str | None = None
    facts: list
    source: str | None = None
    created_at: datetime
    updated_at: datetime


# ───────────────────────────── 简历版本 ─────────────────────────────

class ResumeVersionCreate(BaseModel):
    """新建简历版本。"""

    name: str
    content_md: str | None = None
    target_tier: int = 2  # 默认卡位
    is_primary: bool = False


class ResumeVersionPatch(BaseModel):
    """部分更新版本。"""

    name: str | None = None
    content_md: str | None = None
    target_tier: int | None = None
    is_primary: bool | None = None


class ResumeVersionOut(BaseModel):
    """简历版本出参。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    content_md: str | None = None
    target_tier: int
    is_primary: bool
    created_at: datetime
    updated_at: datetime


# ───────────────────────────── 诊断入参 ─────────────────────────────

class ResumeParseIn(BaseModel):
    """解析入参：简历 md → claims。"""

    content_md: str | None = None


class ResumeDiagnoseIn(BaseModel):
    """诊断入参。

    - version_id：指定版本，取其 content_md（优先）
    - content_md：直接给原文（version_id 为空时生效）
    - posting_id：可选，给定 JD 后额外输出 jd_alignment
    """

    version_id: int | None = None
    content_md: str | None = None
    posting_id: int | None = None


# ───────────────────────────── 诊断出参 ─────────────────────────────

class ResumeClaimOut(BaseModel):
    text: str
    anchored: bool
    anchors: list[dict] = []
    reason: str = ""


class JdAlignmentOut(BaseModel):
    skill: str
    supported: bool
    evidence: str | None = None


class ResumeDiagnosisOut(BaseModel):
    total: int
    anchored_count: int
    unanchored_count: int
    fabrication_risk: int
    claims: list[ResumeClaimOut] = []
    jd_alignment: list[JdAlignmentOut] | None = None
