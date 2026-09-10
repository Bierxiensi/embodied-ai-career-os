"""课程计划 API 路由（30 天施工执行台）。

对应 docs/platform-direction-30day.md 的 P0：
    GET    /api/plan                     30 天课程脊梁（总览页用）
    GET    /api/plan/today               今日施工单（回答"今天第几天/干什么/做完没有"）
    POST   /api/plan/artifacts           勾选一件四件套产出
    DELETE /api/plan/artifacts/{id}      取消勾选

设计说明：
1. 「今天是 Day N」在 P0 由**日历**推导（SPRINT_START 起算，clamp 到 1..30）。
   P1 引入 day_progress 后再把"课程序号"与"日历日期"解耦 ——
   届时落后只提示、不自动顺延。本文件把日历口径单独返回
   （calendar_days_elapsed / is_before_start / is_after_end），
   就是为了让 P1 的改造只动这一处推导，不动下游。
2. 总账（ledger）跨全部 30 天累计，口径固定为计划 §十：
   30 段代码 / 30 篇笔记 / 30 个 commit / 150 道面试题 / 30 个"四件套齐全日"。
   面试题数取题库真实条数（interview_questions），不取产出条数 ——
   否则"录了一次"和"录了 5 道题"会混为一谈。
3. 四件套的 questions 槽位判定为「当天至少录过一次题」，
   与题库总账是两个层级：前者管"今天动没动"，后者管"攒够没有"。
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.core.target_roles import SPRINT_END, SPRINT_START
from app.db.base import get_db
from app.models.day_artifact import ARTIFACT_KINDS, DayArtifact
from app.models.interview_question import InterviewQuestion
from app.models.plan_day import PlanDay
from app.models.task import Task
from app.schemas.plan import (
    ArtifactCreate,
    ArtifactOut,
    LedgerItem,
    PlanDayOut,
    TodayView,
)
from app.schemas.task import TaskOut

router = APIRouter(prefix="/plan", tags=["plan"])

TOTAL_DAYS = 30
# 计划 §十 的累计目标
TARGET_CODE = 30
TARGET_NOTE = 30
TARGET_COMMIT = 30
TARGET_QUESTIONS = 150


def _sprint_bounds() -> tuple[date, date]:
    """解析冲刺窗口。配置缺失或格式错误时回落到当天前后，保证接口不 500。"""

    try:
        return date.fromisoformat(SPRINT_START), date.fromisoformat(SPRINT_END)
    except (TypeError, ValueError):
        today = date.today()
        return today, today


def _resolve_day_index(today: date) -> tuple[int, int, bool, bool]:
    """由日历推导「今天是 Day N」。

    返回 (day_index, calendar_days_elapsed, is_before_start, is_after_end)。
    day_index 始终 clamp 到 1..30，因此窗口外也能正常渲染页面。
    """

    start, end = _sprint_bounds()
    elapsed = (today - start).days
    return (
        min(max(elapsed + 1, 1), TOTAL_DAYS),
        elapsed + 1,
        today < start,
        today > end,
    )


def _load_day(db: Session, seq: int) -> PlanDay:
    """按序号取课程日，不存在则 404（提示先跑种子脚本）。"""

    day = db.query(PlanDay).filter(PlanDay.seq == seq).first()
    if day is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"课程日 Day {seq} 不存在。"
                "请先执行：cd backend && python scripts/seed_plan_30d.py"
            ),
        )
    return day


@router.get("")
def list_plan_days(db: Session = Depends(get_db)) -> ApiResponse[list[PlanDayOut]]:
    """获取 30 天课程脊梁（按 seq 升序）。

    供施工总览页（P1）与今日页的上下文使用。
    """

    days = db.query(PlanDay).order_by(PlanDay.seq.asc()).all()
    return ok([PlanDayOut.model_validate(d) for d in days])


@router.get("/today")
def get_today(
    day: int | None = None, db: Session = Depends(get_db)
) -> ApiResponse[TodayView]:
    """获取今日施工单。

    `day` 可显式指定课程日（用于回看 / 预看某一天）；不传则按日历推导。
    """

    today = date.today()
    day_index, elapsed, before_start, after_end = _resolve_day_index(today)
    seq = day if day is not None else day_index
    if seq < 1 or seq > TOTAL_DAYS:
        raise HTTPException(status_code=422, detail="day 必须在 1..30 之间")

    plan_day = _load_day(db, seq)

    # 今日任务
    tasks = (
        db.query(Task)
        .filter(Task.plan_day_id == plan_day.id)
        .filter(Task.source != "test")
        .order_by(Task.id.asc())
        .all()
    )
    completed = sum(1 for t in tasks if t.status == "done")

    # 四件套状态
    artifacts = (
        db.query(DayArtifact)
        .filter(DayArtifact.plan_day_id == plan_day.id)
        .order_by(DayArtifact.id.asc())
        .all()
    )
    status: dict[str, int] = {k: 0 for k in ARTIFACT_KINDS}
    for a in artifacts:
        if a.kind in status:
            status[a.kind] += 1
    missing = [k for k in ARTIFACT_KINDS if status.get(k, 0) == 0]

    # 总账
    def _count_kind(kind: str) -> int:
        return (
            db.query(DayArtifact)
            .filter(DayArtifact.kind == kind)
            .count()
        )

    questions_total = db.query(InterviewQuestion).count()

    # 四件套齐全的天数
    rows = db.query(DayArtifact.plan_day_id, DayArtifact.kind).distinct().all()
    by_day: dict[int, set[str]] = {}
    for pid, kind in rows:
        by_day.setdefault(pid, set()).add(kind)
    full_days = sum(1 for kinds in by_day.values() if set(ARTIFACT_KINDS) <= kinds)

    ledger = [
        LedgerItem(key="code", label="代码", done=_count_kind("code"), target=TARGET_CODE),
        LedgerItem(key="note", label="笔记", done=_count_kind("note"), target=TARGET_NOTE),
        LedgerItem(
            key="commit", label="commit", done=_count_kind("commit"), target=TARGET_COMMIT
        ),
        LedgerItem(
            key="questions",
            label="面试题",
            done=questions_total,
            target=TARGET_QUESTIONS,
        ),
        LedgerItem(key="days", label="四件套齐全", done=full_days, target=TOTAL_DAYS),
    ]

    return ok(
        TodayView(
            day=PlanDayOut.model_validate(plan_day),
            day_index=day_index,
            total_days=TOTAL_DAYS,
            calendar_days_elapsed=elapsed,
            sprint_start=SPRINT_START,
            is_before_start=before_start,
            is_after_end=after_end,
            tasks=[TaskOut.model_validate(t) for t in tasks],
            completed_tasks=completed,
            artifacts=[ArtifactOut.model_validate(a) for a in artifacts],
            artifact_status=status,
            missing_kinds=missing,
            all_done=not missing,
            ledger=ledger,
        )
    )


@router.post("/artifacts")
def create_artifact(
    payload: ArtifactCreate, db: Session = Depends(get_db)
) -> ApiResponse[ArtifactOut]:
    """勾选一件产出（代码 / 笔记 / 面试题 / commit）。

    P0 为手工记录，auto_verified 恒为 False。
    P2 起 commit 由 GitHub 按日期自动归集、questions 由题库条数自动判定。
    """

    if db.get(PlanDay, payload.plan_day_id) is None:
        raise HTTPException(status_code=404, detail="PlanDay not found")

    artifact = DayArtifact(
        plan_day_id=payload.plan_day_id,
        kind=payload.kind,
        title=payload.title,
        url=payload.url,
        note=payload.note,
        auto_verified=False,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return ok(ArtifactOut.model_validate(artifact), message=f"已记录 {payload.kind}")


@router.delete("/artifacts/{artifact_id}")
def delete_artifact(
    artifact_id: int, db: Session = Depends(get_db)
) -> ApiResponse[dict]:
    """取消勾选（删除一条产出记录）。

    四件套是"今天交了什么"的记录，误勾需要能撤销。
    与 Task 不同，这里允许删除 —— 它不承载历史决策依据（P2 起才承载，届时改软删）。
    """

    artifact = db.get(DayArtifact, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")

    db.delete(artifact)
    db.commit()
    return ok({"id": artifact_id}, message="已取消")
