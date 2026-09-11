"""简历线 API（Batch 2 核心）。

端点：
- GET    /api/resume                  简历版本列表
- POST   /api/resume/versions         新建版本
- GET    /api/resume/versions/{id}    版本详情
- PATCH  /api/resume/versions/{id}    更新版本（含 is_primary 互斥）
- DELETE /api/resume/versions/{id}    删除版本
- POST   /api/resume/parse            简历 md → 结构化 claims
- POST   /api/resume/diagnose         防虚构诊断（可选 posting_id 做 JD 对齐）
- GET    /api/resume/facts            事实锚点库
- POST   /api/resume/facts            新增事实锚点
- DELETE /api/resume/facts/{id}       删除事实锚点
- GET    /api/resume/skill-lines      简历技能行（每行附证据，只收录有真实证据的技能）

防虚构逻辑全部走 agents/resume/engine（纯规则、可解释、不依赖 LLM）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.resume.engine import FactRecord, ResumeEngine
from app.core.response import ok
from app.db.base import get_db
from app.models.job_posting import JobPosting
from app.models.resume_fact import ResumeFact
from app.models.resume_version import ResumeVersion
from app.schemas.resume import (
    JdAlignmentOut,
    ResumeClaimOut,
    ResumeDiagnosisOut,
    ResumeFactCreate,
    ResumeFactOut,
    ResumeParseIn,
    ResumeDiagnoseIn,
    ResumeVersionCreate,
    ResumeVersionOut,
    ResumeVersionPatch,
)
from app.services.packaging.service import collect_skill_lines

router = APIRouter(prefix="/resume", tags=["resume"])


def _fact_records(db: Session) -> list[FactRecord]:
    """把 ResumeFact 行转成引擎用的 FactRecord 列表。"""
    return [
        FactRecord(
            id=r.id,
            category=r.category,
            title=r.title,
            org=r.org,
            facts=list(r.facts or []),
        )
        for r in db.query(ResumeFact).all()
    ]


def _diag_to_out(d) -> dict:
    return ResumeDiagnosisOut(
        total=d.total,
        anchored_count=d.anchored_count,
        unanchored_count=d.unanchored_count,
        fabrication_risk=d.fabrication_risk,
        claims=[
            ResumeClaimOut(text=c.text, anchored=c.anchored, anchors=c.anchors, reason=c.reason)
            for c in d.claims
        ],
        jd_alignment=[
            JdAlignmentOut(skill=i.skill, supported=i.supported, evidence=i.evidence)
            for i in d.jd_alignment
        ]
        if d.jd_alignment
        else None,
    ).model_dump()


# ───────────────────────────── 版本 ─────────────────────────────

@router.get("")
def list_versions(db: Session = Depends(get_db)):
    """简历版本列表（主版本在前）。"""
    rows = (
        db.query(ResumeVersion)
        .order_by(ResumeVersion.is_primary.desc(), ResumeVersion.id)
        .all()
    )
    return ok([ResumeVersionOut.model_validate(r).model_dump() for r in rows])


@router.post("/versions")
def create_version(payload: ResumeVersionCreate, db: Session = Depends(get_db)):
    """新建简历版本。is_primary=True 时互斥其它版本。"""
    if payload.is_primary:
        db.query(ResumeVersion).update({ResumeVersion.is_primary: False})
    v = ResumeVersion(
        name=payload.name,
        content_md=payload.content_md,
        target_tier=payload.target_tier,
        is_primary=payload.is_primary,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return ok(ResumeVersionOut.model_validate(v).model_dump(), "已新建简历版本")


@router.get("/versions/{version_id}")
def get_version(version_id: int, db: Session = Depends(get_db)):
    v = db.query(ResumeVersion).filter(ResumeVersion.id == version_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")
    return ok(ResumeVersionOut.model_validate(v).model_dump())


@router.patch("/versions/{version_id}")
def patch_version(version_id: int, payload: ResumeVersionPatch, db: Session = Depends(get_db)):
    v = db.query(ResumeVersion).filter(ResumeVersion.id == version_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")

    # is_primary 互斥：置 True 时其它全部置 False
    if payload.is_primary is True:
        db.query(ResumeVersion).update({ResumeVersion.is_primary: False})

    if payload.name is not None:
        v.name = payload.name
    if payload.content_md is not None:
        v.content_md = payload.content_md
    if payload.target_tier is not None:
        v.target_tier = payload.target_tier
    if payload.is_primary is not None:
        v.is_primary = payload.is_primary

    db.commit()
    db.refresh(v)
    return ok(ResumeVersionOut.model_validate(v).model_dump(), "已更新版本")


@router.delete("/versions/{version_id}")
def delete_version(version_id: int, db: Session = Depends(get_db)):
    v = db.query(ResumeVersion).filter(ResumeVersion.id == version_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")
    db.delete(v)
    db.commit()
    return ok(None, "已删除版本")


# ───────────────────────────── 解析 / 诊断 ─────────────────────────────

@router.post("/parse")
def parse_resume(payload: ResumeParseIn, db: Session = Depends(get_db)):
    """简历 md → 结构化 claims（抽取即可校验的 claim 列表）。"""
    from app.agents.resume.engine import extract_claims

    claims = extract_claims(payload.content_md)
    return ok({"claims": claims, "count": len(claims)})


@router.post("/diagnose")
def diagnose(payload: ResumeDiagnoseIn, db: Session = Depends(get_db)):
    """防虚构诊断。

    - version_id 优先取版本 content_md；否则用 body.content_md
    - posting_id 给定时额外输出 jd_alignment（JD 要求技能的简历依据）
    """
    content: str | None = None
    if payload.version_id is not None:
        v = db.query(ResumeVersion).filter(ResumeVersion.id == payload.version_id).first()
        if not v:
            raise HTTPException(status_code=404, detail="版本不存在")
        content = v.content_md
    if not content:
        content = payload.content_md

    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="请提供简历内容或有效的版本 ID")

    facts = _fact_records(db)

    required: list[str] | None = None
    if payload.posting_id is not None:
        p = db.query(JobPosting).filter(JobPosting.id == payload.posting_id).first()
        if p:
            required = p.required_skills or []

    diagnosis = ResumeEngine.diagnose(content, facts, required)
    return ok(_diag_to_out(diagnosis))


# ───────────────────────────── 事实锚点库 ─────────────────────────────

@router.get("/facts")
def list_facts(db: Session = Depends(get_db)):
    """事实锚点库（按分类、id 排序）。"""
    rows = db.query(ResumeFact).order_by(ResumeFact.category, ResumeFact.id).all()
    return ok([ResumeFactOut.model_validate(r).model_dump() for r in rows])


@router.post("/facts")
def create_fact(payload: ResumeFactCreate, db: Session = Depends(get_db)):
    """新增一条事实锚点（防虚构依据）。"""
    f = ResumeFact(
        category=payload.category,
        title=payload.title,
        org=payload.org,
        start=payload.start,
        end=payload.end,
        facts=payload.facts,
        source=payload.source,
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return ok(ResumeFactOut.model_validate(f).model_dump(), "已新增事实锚点")


@router.delete("/facts/{fact_id}")
def delete_fact(fact_id: int, db: Session = Depends(get_db)):
    """删除事实锚点。"""
    f = db.query(ResumeFact).filter(ResumeFact.id == fact_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="事实锚点不存在")
    db.delete(f)
    db.commit()
    return ok(None, "已删除事实锚点")


# ───────────────────────────── 技能行（附证据） ─────────────────────────────

@router.get("/skill-lines")
def skill_lines(pending_min_level: int = 3, db: Session = Depends(get_db)):
    """简历技能行 —— 每行附可点开的证据。

    P4 / plan_30d Day 25 验收：「简历技能行每一项都能点开对应证据（代码 / 实验 / 论文）」。

    - ``ready``：已有真实证据（``evidence_gate >= 1``）的技能，可直接写进简历
    - ``pending``：自评 ``level >= pending_min_level`` 却尚无证据 —— 写进简历即虚构风险
    """
    return ok(collect_skill_lines(db, pending_min_level=pending_min_level))
