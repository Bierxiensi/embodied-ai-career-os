"""JobPosting / JobMatch Pydantic 请求与响应模型。

匹配结果（JobMatch）通过 match_* 可选字段内联进 JobPostingOut，
前端一次请求即可拿到"岗位 + 匹配"，无需额外 N+1 拉取。
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class JobPostingCreate(BaseModel):
    """录入 JD：公司 / 岗位 / 文本为必填，其余可选。

    required_skills 不传时由后端 JDParser 从 jd_text 自动解析；
    track / tier 不传时回落默认（llm / 卡位）。
    """

    company: str
    title: str
    jd_text: str | None = None
    track: str = "llm"
    tier: int = 2
    city: str | None = None
    salary_range: str | None = None
    source: str | None = None
    url: str | None = None
    posted_at: date | None = None
    education: str | None = None
    min_years: int | None = None
    paper_required: bool = False
    required_skills: list[str] | None = None
    status: str = "open"


class JobPostingPatch(BaseModel):
    """部分更新（改梯队 / 状态 / 薪资等）。"""

    company: str | None = None
    title: str | None = None
    jd_text: str | None = None
    track: str | None = None
    tier: int | None = None
    city: str | None = None
    salary_range: str | None = None
    source: str | None = None
    url: str | None = None
    posted_at: date | None = None
    education: str | None = None
    min_years: int | None = None
    paper_required: bool | None = None
    required_skills: list[str] | None = None
    status: str | None = None


class JobMatchOut(BaseModel):
    """匹配结果明细。"""

    match_score: int
    grade: str
    dimension_scores: dict | None = None
    gaps: list | None = None
    matched_track: str | None = None
    updated_at: datetime | None = None


class JobPostingOut(BaseModel):
    """岗位出参（内联匹配结果）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    title: str
    city: str | None = None
    salary_range: str | None = None
    jd_text: str | None = None
    source: str | None = None
    url: str | None = None
    posted_at: date | None = None
    tier: int
    track: str
    required_skills: list | None = None
    education: str | None = None
    min_years: int | None = None
    paper_required: bool = False
    status: str
    created_at: datetime
    updated_at: datetime

    # 内联匹配（未匹配时为 None）
    match_score: int | None = None
    grade: str | None = None
    dimension_scores: dict | None = None
    gaps: list | None = None
    matched_track: str | None = None
    matched_at: datetime | None = None

    @classmethod
    def from_rows(cls, posting, match) -> "JobPostingOut":
        """由 ORM 行（posting, match?）构造出参。"""
        data = {
            "id": posting.id,
            "company": posting.company,
            "title": posting.title,
            "city": posting.city,
            "salary_range": posting.salary_range,
            "jd_text": posting.jd_text,
            "source": posting.source,
            "url": posting.url,
            "posted_at": posting.posted_at,
            "tier": posting.tier,
            "track": posting.track,
            "required_skills": posting.required_skills,
            "education": posting.education,
            "min_years": posting.min_years,
            "paper_required": posting.paper_required,
            "status": posting.status,
            "created_at": posting.created_at,
            "updated_at": posting.updated_at,
        }
        if match:
            data.update({
                "match_score": match.match_score,
                "grade": match.grade,
                "dimension_scores": match.dimension_scores,
                "gaps": match.gaps,
                "matched_track": match.matched_track,
                "matched_at": match.updated_at,
            })
        return cls(**data)
