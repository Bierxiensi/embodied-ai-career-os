"""岗位池 API（Batch 1 核心）。

- POST   /api/job-postings              录入 / 批量录入 JD（自动解析技能 + 自动匹配）
- GET    /api/job-postings              岗位池（带匹配结果，可按 tier/grade/track/status 过滤）
- POST   /api/job-postings/{id}/match   重算并存储匹配（幂等，可重算）
- GET    /api/job-postings/stats        梯队分布 + A/B/C/D 分布

匹配逻辑全部走 agents/match/engine（纯规则、可解释、不依赖 LLM）。
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents.match.engine import JDParser, MatchEngine
from app.core.response import ok
from app.db.base import get_db
from app.models.interview_question import InterviewQuestion
from app.models.job_match import GRADE_ORDER, JobMatch, grade_of
from app.models.job_posting import POSTING_STATUS_ORDER, JobPosting
from app.models.skill import Skill
from app.schemas.job_posting import JobPostingCreate, JobPostingOut, JobPostingPatch

router = APIRouter(prefix="/job-postings", tags=["job-postings"])


def _dedup_key(company: str, title: str) -> str:
    return f"{company.strip().lower()}::{title.strip().lower()}"


def _build_skill_levels(db: Session) -> dict[str, int]:
    """从 Skill 表构建 '规范技能名(小写)' -> 等级 映射（实时，反映手动改级）。"""
    return {s.name.strip().lower(): s.level for s in db.query(Skill).all()}


def _match_and_store(db: Session, posting: JobPosting, skill_levels: dict[str, int]) -> JobMatch:
    """对一条岗位计算匹配并 upsert 到 job_matches，返回 JobMatch 行。"""
    required = posting.required_skills or []
    result = MatchEngine.compute(
        required_skills=required,
        track=posting.track,
        education=posting.education,
        min_years=posting.min_years,
        paper_required=posting.paper_required,
        skill_levels=skill_levels,
    )
    match = db.query(JobMatch).filter(JobMatch.posting_id == posting.id).first()
    if match is None:
        match = JobMatch(posting_id=posting.id)
        db.add(match)
    match.match_score = result.match_score
    match.grade = result.grade
    match.dimension_scores = result.dimension_scores
    match.gaps = result.gaps
    match.matched_track = result.matched_track
    match.updated_at = datetime.utcnow()
    return match


@router.post("")
def create_postings(
    payload: JobPostingCreate | list[JobPostingCreate],
    db: Session = Depends(get_db),
):
    """录入一条或批量录入 JD。

    每条自动：
    - 计算 dedup_key（公司+岗位），重复则跳过并提示
    - 未给 required_skills 时从 jd_text 解析
    - 计算并存储匹配结果
    """
    items = payload if isinstance(payload, list) else [payload]
    skill_levels = _build_skill_levels(db)

    created: list[JobPostingOut] = []
    skipped: list[str] = []

    for item in items:
        key = _dedup_key(item.company, item.title)
        exists = db.query(JobPosting).filter(JobPosting.dedup_key == key).first()
        if exists:
            skipped.append(f"{item.company}/{item.title}")
            continue

        required = item.required_skills
        if not required and item.jd_text:
            required = JDParser.parse_required_skills(item.jd_text)

        posting = JobPosting(
            company=item.company,
            title=item.title,
            jd_text=item.jd_text,
            track=item.track,
            tier=item.tier,
            city=item.city,
            salary_range=item.salary_range,
            source=item.source,
            url=item.url,
            posted_at=item.posted_at,
            education=item.education,
            min_years=item.min_years,
            paper_required=item.paper_required,
            required_skills=required,
            status=item.status,
            dedup_key=key,
        )
        db.add(posting)
        db.flush()  # 拿到 posting.id 以便存 match
        # 注意：SessionLocal(autoflush=False)，新增的 match 在 commit 前不会被 SELECT 看到，
        # 因此直接用 _match_and_store 返回的内存对象，不要回查。
        match = _match_and_store(db, posting, skill_levels)
        created.append(JobPostingOut.from_rows(posting, match))

    db.commit()
    return ok(
        {
            "created": [c.model_dump() for c in created],
            "skipped": skipped,
            "count": len(created),
        },
        message=f"已录入 {len(created)} 条" + (f"，跳过重复 {len(skipped)} 条" if skipped else ""),
    )


@router.get("")
def list_postings(
    tier: int | None = None,
    grade: str | None = None,
    track: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """岗位池（内联匹配）。支持按梯队 / 等级 / 赛道 / 状态过滤。"""
    rows = db.query(JobPosting).all()
    matches = {m.posting_id: m for m in db.query(JobMatch).all()}

    out: list[JobPostingOut] = []
    for p in rows:
        m = matches.get(p.id)
        # 过滤
        if tier is not None and p.tier != tier:
            continue
        if track and p.track != track:
            continue
        if status and p.status != status:
            continue
        if grade and (m is None or m.grade != grade):
            continue
        out.append(JobPostingOut.from_rows(p, m))

    # 默认按匹配分降序（未匹配排末尾）
    out.sort(key=lambda o: (o.match_score if o.match_score is not None else -1), reverse=True)
    return ok([o.model_dump() for o in out])


@router.post("/{posting_id}/match")
def recompute_match(posting_id: int, db: Session = Depends(get_db)):
    """重算并存储某岗位的匹配（幂等）。技能等级变化后调用此接口刷新。"""
    posting = db.query(JobPosting).filter(JobPosting.id == posting_id).first()
    if not posting:
        raise HTTPException(status_code=404, detail="岗位不存在")

    skill_levels = _build_skill_levels(db)
    match = _match_and_store(db, posting, skill_levels)
    db.commit()
    db.refresh(posting)
    return ok(JobPostingOut.from_rows(posting, match).model_dump(), "已重算匹配")


@router.delete("/{posting_id}")
def delete_posting(posting_id: int, db: Session = Depends(get_db)):
    """删除岗位（级联删除其匹配记录）。"""
    posting = db.query(JobPosting).filter(JobPosting.id == posting_id).first()
    if not posting:
        raise HTTPException(status_code=404, detail="岗位不存在")
    db.query(JobMatch).filter(JobMatch.posting_id == posting_id).delete()
    db.delete(posting)
    db.commit()
    return ok(None, "已删除")


@router.get("/stats")
def posting_stats(db: Session = Depends(get_db)):
    """岗位池统计：梯队分布 + A/B/C/D 等级分布 + 推荐数。"""
    rows = db.query(JobPosting).all()
    matches = {m.posting_id: m for m in db.query(JobMatch).all()}

    tier_counts = {1: 0, 2: 0, 3: 0}
    grade_counts = {g: 0 for g in GRADE_ORDER}
    for p in rows:
        if p.tier in tier_counts:
            tier_counts[p.tier] += 1
        m = matches.get(p.id)
        if m:
            grade_counts[m.grade] = grade_counts.get(m.grade, 0) + 1

    total = len(rows)
    recommended = grade_counts.get("A", 0) + grade_counts.get("B", 0)
    return ok({
        "total": total,
        "by_tier": tier_counts,
        "by_grade": grade_counts,
        "recommended": recommended,  # A+B 合计（可优先投）
        "unmatched": sum(1 for p in rows if p.id not in matches),
    })


@router.get("/{posting_id}/recommendations")
def posting_recommendations(posting_id: int, db: Session = Depends(get_db)):
    """JD 驱动学习推荐：根据岗位缺口推荐面试题。

    返回：
    - gaps: 该 JD 要求但用户水平不足的技能列表
    - recommendations: 每个缺口技能对应的已有题目 + 缺题情况
    - summary: 总缺口数、已有题覆盖数、需补题数
    """
    posting = db.query(JobPosting).filter(JobPosting.id == posting_id).first()
    if not posting:
        raise HTTPException(404, "岗位不存在")

    skill_levels = {s.name.strip().lower(): s.level for s in db.query(Skill).all()}
    required = posting.required_skills or []

    result = MatchEngine.compute(
        required_skills=required,
        track=posting.track,
        education=posting.education,
        min_years=posting.min_years,
        paper_required=posting.paper_required,
        skill_levels=skill_levels,
    )

    # 查题库
    all_questions = db.query(InterviewQuestion).all()
    q_by_skill: dict[str, list[dict]] = {}
    for q in all_questions:
        if q.skill_name:
            q_by_skill.setdefault(q.skill_name, []).append({
                "id": q.id,
                "category": q.category,
                "difficulty": q.difficulty,
                "question": q.question,
                "hit_count": q.hit_count,
                "is_verified": q.is_verified,
            })

    recommendations = []
    total_covered = 0
    total_missing = 0
    for gap in result.gaps:
        skill = gap["skill"]
        existing = q_by_skill.get(skill, [])
        # 按分类统计已有题数
        by_category = {}
        for q in existing:
            by_category[q["category"]] = by_category.get(q["category"], 0) + 1

        has_questions = len(existing) > 0
        if has_questions:
            total_covered += 1
        else:
            total_missing += 1

        recommendations.append({
            "skill": skill,
            "current_level": gap["level"],
            "required_level": gap["required"],
            "gap": gap["gap"],
            "question_count": len(existing),
            "questions": existing[:5],  # 最多返回5题预览
            "by_category": by_category,
            "status": "有题可练" if has_questions else "缺题，需补充",
        })

    return ok({
        "posting": {
            "id": posting.id,
            "company": posting.company,
            "title": posting.title,
            "track": posting.track,
        },
        "match": {
            "score": result.match_score,
            "grade": result.grade,
        },
        "gaps": recommendations,
        "summary": {
            "total_gaps": len(recommendations),
            "covered": total_covered,
            "missing_questions": total_missing,
        },
    })
