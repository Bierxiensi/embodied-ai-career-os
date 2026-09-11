"""面试线 API（Batch 3 核心）。

端点：
- GET    /api/interviews                面经列表
- POST   /api/interviews                记录面经
- GET    /api/interviews/stats          弱项统计
- DELETE /api/interviews/{id}           删除面经
- POST   /api/interviews/{id}/to-tasks  弱项 → 学习任务（回写 Task）
- GET    /api/interview-questions       题库（可按 category/difficulty 过滤）
- POST   /api/interview-questions       新增题目
- DELETE /api/interview-questions/{id}  删除题目
- POST   /api/interview/simulate        模拟面试抽题（命中次数 +1）

弱项聚合 / 任务映射 / 抽题全部走 agents/interview/engine（纯规则、可解释、不依赖 LLM）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.interview.engine import (
    coverage_matrix,
    pick_questions,
    weak_to_tasks,
    weakness_stats,
)
from app.core.response import ok
from app.core.target_roles import TARGET_ROLES
from app.db.base import get_db
from app.models.interview_log import InterviewLog
from app.models.interview_question import InterviewQuestion
from app.models.task import Task
from app.schemas.interview import (
    InterviewLogCreate,
    InterviewLogOut,
    InterviewQuestionCreate,
    InterviewQuestionOut,
    QuestionCoverageOut,
    SimulateIn,
    TaskDraftOut,
    ToTasksIn,
    WeakStatOut,
)

router = APIRouter(tags=["interviews"])


# ───────────────────────────── 面经 ─────────────────────────────

@router.get("/interviews")
def list_interviews(db: Session = Depends(get_db)):
    """面经列表（面试日期降序）。"""
    rows = (
        db.query(InterviewLog)
        .order_by(InterviewLog.interviewed_at.desc().nullslast(), InterviewLog.id.desc())
        .all()
    )
    return ok([InterviewLogOut.model_validate(r).model_dump() for r in rows])


@router.post("/interviews")
def create_interview(payload: InterviewLogCreate, db: Session = Depends(get_db)):
    """记录一条面经。"""
    log = InterviewLog(
        company=payload.company,
        role=payload.role,
        round=payload.round,
        asked_questions=payload.asked_questions,
        weak_questions=payload.weak_questions,
        jd_gaps=payload.jd_gaps,
        knowledge_gaps=payload.knowledge_gaps,
        next_actions=payload.next_actions,
        interviewed_at=payload.interviewed_at,
        notes=payload.notes,
        generated_task_ids=[],
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return ok(InterviewLogOut.model_validate(log).model_dump(), "已记录面经")


@router.delete("/interviews/{log_id}")
def delete_interview(log_id: int, db: Session = Depends(get_db)):
    log = db.query(InterviewLog).filter(InterviewLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="面经不存在")
    db.delete(log)
    db.commit()
    return ok(None, "已删除面经")


@router.get("/interviews/stats")
def interview_stats(db: Session = Depends(get_db)):
    """弱项统计（跨全部面经聚合，出现次数降序）。"""
    rows = db.query(InterviewLog).all()
    logs = [{"id": r.id, "weak_questions": r.weak_questions or []} for r in rows]
    stats = weakness_stats(logs)
    return ok({
        "total_logs": len(rows),
        "total_weak": sum(s.count for s in stats),
        "weak_topics": [WeakStatOut(topic=s.topic, count=s.count, log_ids=s.log_ids).model_dump() for s in stats],
    })


@router.post("/interviews/{log_id}/to-tasks")
def interview_to_tasks(log_id: int, payload: ToTasksIn, db: Session = Depends(get_db)):
    """把该面经的弱项 / 知识缺口回写为学习任务（写入 tasks 表）。"""
    log = db.query(InterviewLog).filter(InterviewLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="面经不存在")

    weak_items = weakness_stats([{"id": log.id, "weak_questions": log.weak_questions or []}])
    drafts = weak_to_tasks(
        weak_items,
        gaps=log.knowledge_gaps or [],
        limit=payload.limit,
        duration=payload.duration,
    )

    created: list[TaskDraftOut] = []
    created_ids: list[int] = []
    for d in drafts:
        task = Task(
            title=d.title,
            objective=d.objective,
            duration=d.duration,
            difficulty=d.difficulty,
            status="todo",
            skill_name=d.skill_name,
            acceptance=d.acceptance,
            resources=[],
        )
        db.add(task)
        db.flush()
        created_ids.append(task.id)
        created.append(
            TaskDraftOut(
                title=d.title,
                objective=d.objective,
                duration=d.duration,
                difficulty=d.difficulty,
                skill_name=d.skill_name,
                acceptance=d.acceptance,
            ).model_dump()
        )

    # 记录已生成任务 id（去重累积）
    existing = list(log.generated_task_ids or [])
    for tid in created_ids:
        if tid not in existing:
            existing.append(tid)
    log.generated_task_ids = existing

    db.commit()
    return ok(
        {"created": created, "task_ids": created_ids, "count": len(created)},
        message=f"已回写 {len(created)} 个学习任务",
    )


# ───────────────────────────── 题库 ─────────────────────────────

@router.get("/interview-questions")
def list_questions(
    category: str | None = None,
    difficulty: str | None = None,
    db: Session = Depends(get_db),
):
    """题库（可按分类 / 难度过滤）。"""
    q = db.query(InterviewQuestion)
    if category:
        q = q.filter(InterviewQuestion.category == category)
    if difficulty:
        q = q.filter(InterviewQuestion.difficulty == difficulty)
    rows = q.order_by(InterviewQuestion.category, InterviewQuestion.id).all()
    return ok([InterviewQuestionOut.model_validate(r).model_dump() for r in rows])


@router.get("/interview-questions/coverage")
def question_coverage(
    track_key: str | None = None, db: Session = Depends(get_db)
):
    """题库覆盖率矩阵（P3 · 决策 5）：回答「缺口在哪」。

    矩阵行 = 目标赛道的硬性要求技能（`track_key` 指定，缺省取「主攻」赛道）
    ∪ 题库里已出现过的 `skill_name`；列为四个分类，**红格 = 该 (技能, 分类) 一题为 0**。

    分类目标见 engine.QUESTION_CATEGORY_TARGETS（累计 150，核心必达 80）。
    纯规则聚合，不依赖 LLM；技能顺序沿用赛道 required_skills 的声明顺序。
    """
    track = None
    if track_key:
        track = next((r for r in TARGET_ROLES if r.key == track_key), None)
    if track is None:
        track = next(
            (r for r in TARGET_ROLES if r.priority == "主攻"),
            TARGET_ROLES[0] if TARGET_ROLES else None,
        )
    skills = list(track.required_skills) if track else []

    rows = db.query(InterviewQuestion).all()
    questions = [{"category": r.category, "skill_name": r.skill_name} for r in rows]
    data = coverage_matrix(questions, skills)
    return ok(QuestionCoverageOut(**data).model_dump())


@router.post("/interview-questions")
def create_question(payload: InterviewQuestionCreate, db: Session = Depends(get_db)):
    """新增一道题目。

    P2：可携带 source_day_seq / skill_name / is_verified，
    用于「四件套 questions 由题库当日条数自动判定」与 evidence-gated 晋级。
    """
    q = InterviewQuestion(
        category=payload.category,
        question=payload.question,
        difficulty=payload.difficulty,
        answer_outline=payload.answer_outline,
        source=payload.source,
        source_day_seq=payload.source_day_seq,
        skill_name=payload.skill_name,
        is_verified=payload.is_verified,
        hit_count=0,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return ok(InterviewQuestionOut.model_validate(q).model_dump(), "已新增题目")


@router.delete("/interview-questions/{question_id}")
def delete_question(question_id: int, db: Session = Depends(get_db)):
    q = db.query(InterviewQuestion).filter(InterviewQuestion.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="题目不存在")
    db.delete(q)
    db.commit()
    return ok(None, "已删除题目")


# ───────────────────────────── 模拟抽题 ─────────────────────────────

@router.post("/interview/simulate")
def simulate(payload: SimulateIn, db: Session = Depends(get_db)):
    """模拟面试抽题（纯规则）：按分类 / 难度抽 limit 道，命中次数少者优先。"""
    rows = db.query(InterviewQuestion).all()
    items = [
        {
            "id": r.id,
            "category": r.category,
            "question": r.question,
            "difficulty": r.difficulty,
            "answer_outline": r.answer_outline,
            "source": r.source,
            "hit_count": r.hit_count,
        }
        for r in rows
    ]
    picked = pick_questions(
        items,
        category=payload.category,
        difficulty=payload.difficulty,
        limit=payload.limit,
    )

    # 抽中即命中次数 +1
    for p in picked:
        row = db.query(InterviewQuestion).filter(InterviewQuestion.id == p["id"]).first()
        if row:
            row.hit_count = (row.hit_count or 0) + 1
            p["hit_count"] = row.hit_count
    db.commit()

    return ok({"picked": picked, "count": len(picked)})
