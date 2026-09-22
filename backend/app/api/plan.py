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
4. 今日任务的**赛道口径**（Milestone B）不在本文件实现：
   统一走 services/action_planning/task_scope.py，与 /api/job-hunt 同一个入口。
   本路由只负责"第几天"这个轴（plan_day_id），"哪条赛道"由服务层负责 ——
   两个轴正交，各留各的模块，避免复制出第二份赛道判断。
"""

from __future__ import annotations

import os
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.github_client import fetch_github_commits
from app.core.response import ApiResponse, ok
from app.core.target_roles import SPRINT_END, SPRINT_START, TARGET_ROLES
from app.db.base import get_db
from app.api.risk import build_risk_result
from app.core.career_roi import compute_task_roi
from app.models.day_artifact import (
    ARTIFACT_KIND_COMMIT,
    ARTIFACT_KIND_QUESTIONS,
    ARTIFACT_KINDS,
    DayArtifact,
    QUESTIONS_MIN_PER_DAY,
)
from app.models.day_progress import (
    PROGRESS_COMPRESSED,
    PROGRESS_DONE,
    PROGRESS_PASSED,
    PROGRESS_PENDING,
    DayProgress,
)
from app.models.interview_question import InterviewQuestion
from app.models.plan_day import PlanDay
from app.models.skill import Skill
from app.models.task import Task
from app.schemas.plan import (
    ArtifactCreate,
    ArtifactOut,
    DayProgressOut,
    LedgerItem,
    PlanDayOut,
    PlanDayStatusItem,
    PlanOverview,
    ProgressUpdate,
    TodayView,
)
from app.schemas.risk import RiskOut, RoiTaskOut
from app.schemas.task import TaskOut
from app.schemas.task_scope import to_scoped_task_ref, to_task_scope_out
from app.services.action_planning.task_scope import (
    TaskTrackScope,
    resolve_task_scope,
    select_tasks,
)

router = APIRouter(prefix="/plan", tags=["plan"])

TOTAL_DAYS = 30
# 计划 §十 的累计目标
TARGET_CODE = 30
TARGET_NOTE = 30
TARGET_COMMIT = 30
TARGET_QUESTIONS = 150


class CommitSyncIn(BaseModel):
    """commit 同步入参。repo / token 缺省读环境变量（PLAN_REPO / GITHUB_TOKEN）。

    commits 为测试 / 演示用：直接传入 commit 列表即可绕过 GitHub API，
    便于离线验证归集逻辑（不依赖真实 token）。
    """

    repo: str | None = None
    token: str | None = None
    since: str | None = None
    until: str | None = None
    commits: list[dict] | None = None


def _sync_commits_to_artifacts(
    db: Session, commits: list[dict], sprint_start: str
) -> int:
    """把 commit 列表按日期归集到对应课程日，幂等写入 commit artifact。

    映射规则：commit_date - SPRINT_START 的天数 + 1 = 课程日序号（1..30）。
    超出窗口的 commit 跳过。同一 (plan_day, sha) 不重复写（去重）。
    """

    start = date.fromisoformat(sprint_start)
    synced = 0
    for c in commits:
        cd = (c.get("date") or "")[:10]
        if not cd:
            continue
        try:
            day_index = (date.fromisoformat(cd) - start).days + 1
        except ValueError:
            continue
        if day_index < 1 or day_index > TOTAL_DAYS:
            continue
        day = db.query(PlanDay).filter(PlanDay.seq == day_index).first()
        if day is None:
            continue
        sha = c.get("sha")
        existing = (
            db.query(DayArtifact)
            .filter(
                DayArtifact.plan_day_id == day.id,
                DayArtifact.kind == ARTIFACT_KIND_COMMIT,
            )
            .all()
        )
        if sha and any((a.payload or {}).get("sha") == sha for a in existing):
            continue
        db.add(
            DayArtifact(
                plan_day_id=day.id,
                kind=ARTIFACT_KIND_COMMIT,
                title=(c.get("message") or "")[:120],
                url=c.get("html_url"),
                auto_verified=True,
                payload={
                    "sha": sha,
                    "repo": c.get("repo"),
                    "author": c.get("author"),
                    "date": cd,
                },
            )
        )
        synced += 1
    db.commit()
    return synced


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
    #
    # 口径（Milestone B）：与 /api/job-hunt **共用** services/action_planning/
    # task_scope.py —— 赛道过滤只有那一处实现，本路由不自己拼 track_key 条件。
    #
    # 为什么课程日任务也要按模式过滤（而不是"课程日是硬排期、不受模式影响"）：
    #   本次改造要回答的是"总数为什么变小"，两个视图必须给同一个答案。若看板
    #   按模式排除了冻结赛道的任务、今日页却把它列成"今天要做的事"，同一份库里
    #   就有两个口径，用户无从判断哪个数字可信，冻结赛道的任务也会继续占用
    #   今日待办 —— 正是 Milestone B 要消灭的现象。
    #
    # 两个轴是正交的，各自留在自己的模块：`plan_day_id`（第几天）由课程计划
    #   权威（core/plan_30d.py），`track_key`（哪条赛道）由 task_scope 权威。
    #   本查询只负责前者，后者整段交给 select_tasks。
    #
    # 当前配置下的实际效果：30 天课程的 track_key 只有 llm / vlm，二者均未冻结，
    #   因此这里的过滤是**恒等变换**（不排除任何任务）。它是为"课程日将来落到
    #   冻结赛道、或课程日任务被标为冻结赛道"准备的，届时无需改动本处。
    #   该恒等性质由 tests/test_task_scope_service.py 显式钉住，防止有人误以为
    #   "课程日不受模式影响"而把这段删掉。
    scoped_tasks = select_tasks(
        db.query(Task)
        .filter(Task.plan_day_id == plan_day.id)
        .filter(Task.source != "test")
        .order_by(Task.id.asc()),
        resolve_task_scope(db),
    )
    tasks = list(scoped_tasks.included)
    completed = sum(1 for t in tasks if t.status == "done")

    # Phase 2：七维风险雷达（与 /api/risk 同源，复用 build_risk_result）
    risk_result = build_risk_result(db, today)

    # Phase 2：当日任务 ROI Top5（附加视图，不改 tasks 原有排序）
    main_role = next((r for r in TARGET_ROLES if r.priority == "主攻"), None)
    main_required = (
        [s.lower() for s in main_role.required_skills] if main_role else []
    )
    active_track_keys = scoped_tasks.scope.active_track_keys
    skill_rows = {s.name.lower(): s for s in db.query(Skill).all()}
    roi_items: list[RoiTaskOut] = []
    for t in tasks:
        sname = t.skill_name
        srow = skill_rows.get(sname.lower()) if sname else None
        gap = max(srow.target_level - srow.level, 0) if srow else 0
        res = compute_task_roi(
            skill_name=sname,
            skill_gap=gap,
            track_keys_active=active_track_keys,
            main_track_required=main_required,
            task_source=t.source,
            duration_minutes=t.duration,
            track_key=t.track_key,
        )
        roi_items.append(
            RoiTaskOut(
                task_id=t.id,
                title=t.title,
                skill_name=sname,
                roi=res.roi,
                reasons=res.reasons,
            )
        )
    # 不改 tasks 原有排序：ROI 列表是独立降序视图，取 Top5
    roi_items.sort(key=lambda r: r.roi, reverse=True)
    roi_ranked_tasks = roi_items[:5]

    # 四件套状态（手工 artifact 计数）
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

    # P2：questions 轴可由题库当日条数自动判定（>= QUESTIONS_MIN_PER_DAY）。
    # 这样「每天录 5 题」不再靠手工勾一个 questions artifact，而是看题库真实条数。
    questions_from_bank = (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.source_day_seq == plan_day.seq)
        .count()
    )
    questions_satisfied = (
        status.get(ARTIFACT_KIND_QUESTIONS, 0) > 0
        or questions_from_bank >= QUESTIONS_MIN_PER_DAY
    )
    # 展示用的 questions 计数取「手工勾选」与「题库当日条数」的较高者
    status[ARTIFACT_KIND_QUESTIONS] = max(
        status.get(ARTIFACT_KIND_QUESTIONS, 0), questions_from_bank
    )

    missing = [
        k
        for k in ARTIFACT_KINDS
        if k == ARTIFACT_KIND_QUESTIONS and not questions_satisfied
        or k != ARTIFACT_KIND_QUESTIONS and status.get(k, 0) == 0
    ]

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
            task_scope=to_task_scope_out(scoped_tasks),
            excluded_tasks=[
                to_scoped_task_ref(t, TaskTrackScope.FROZEN)
                for t in scoped_tasks.frozen_items
            ],
            artifacts=[ArtifactOut.model_validate(a) for a in artifacts],
            artifact_status=status,
            questions_from_bank=questions_from_bank,
            missing_kinds=missing,
            all_done=not missing,
            ledger=ledger,
            risk=RiskOut(**risk_result.to_dict()),
            roi_ranked_tasks=roi_ranked_tasks,
        )
    )


@router.get("/overview")
def get_overview(
    day: int | None = None, db: Session = Depends(get_db)
) -> ApiResponse[PlanOverview]:
    """30 天课程总览 + 滑期计算（P1 核心视图）。

    返回每日状态投影与「课程进度 vs 日历进度」的偏差：
        behind        = 已错过的天数（>0 即落后）
        completed_days= 已通过（done/compressed）且 seq <= 当前天的天数

    滑期口径（决策 1 / 风险 3）：
        - seq 与日历解耦；「当前天」由日历推导（clamp 1..30）
        - 落后**只提示、不自动顺延**：页面把标红日期交给用户手动决策
        - 某天「通过」判定：有 day_progress 且 status∈(done,compressed)，
          或四件套齐全（与 /today 口径一致）

    `?day=N` 可覆盖「当前天」（回看 / 预看 / 测试用），不改变 day_index 的日历含义。
    """

    today = date.today()
    day_index, elapsed, before_start, after_end = _resolve_day_index(today)
    # 覆盖「当前天」：仅影响 is_missed / completed_days / behind 的口径
    view_seq = day if day is not None else day_index
    if view_seq < 1 or view_seq > TOTAL_DAYS:
        raise HTTPException(status_code=422, detail="day 必须在 1..30 之间")

    days = db.query(PlanDay).order_by(PlanDay.seq.asc()).all()
    progress_by_day = {p.plan_day_id: p for p in db.query(DayProgress).all()}

    # 四件套齐全情况（推导 done 的依据之一）
    rows = db.query(DayArtifact.plan_day_id, DayArtifact.kind).distinct().all()
    full_by_day: dict[int, bool] = {}
    tmp: dict[int, set[str]] = {}
    for pid, kind in rows:
        tmp.setdefault(pid, set()).add(kind)

    # P2：questions 轴可由题库当日条数自动判定。一次性按 source_day_seq 聚合，
    # 避免 N 次查询。seq 与 plan_day.id 通过 days 列表映射。
    seq_by_id = {d.id: d.seq for d in days}
    qrows = (
        db.query(InterviewQuestion.source_day_seq, func.count())
        .filter(InterviewQuestion.source_day_seq.isnot(None))
        .group_by(InterviewQuestion.source_day_seq)
        .all()
    )
    qcount_by_seq = {int(seq): cnt for seq, cnt in qrows}
    artifact_kinds_no_q = set(ARTIFACT_KINDS) - {ARTIFACT_KIND_QUESTIONS}

    for d in days:
        kinds = tmp.get(d.id, set())
        code_note_commit_ok = artifact_kinds_no_q <= kinds
        q_count = qcount_by_seq.get(d.seq, 0)
        questions_ok = (
            ARTIFACT_KIND_QUESTIONS in kinds
            or q_count >= QUESTIONS_MIN_PER_DAY
        )
        full_by_day[d.id] = bool(code_note_commit_ok and questions_ok)

    items: list[PlanDayStatusItem] = []
    for d in days:
        rec = progress_by_day.get(d.id)
        if rec is not None:
            status = rec.status
            note = rec.deviation_note
        elif full_by_day.get(d.id):
            status = PROGRESS_DONE
            note = None
        else:
            status = PROGRESS_PENDING
            note = None

        is_missed = (d.seq <= view_seq) and (status not in PROGRESS_PASSED)
        items.append(
            PlanDayStatusItem(
                seq=d.seq,
                plan_day_id=d.id,
                phase=d.phase,
                phase_name=d.phase_name,
                title=d.title,
                theme=d.theme,
                track_key=d.track_key,
                est_minutes=d.est_minutes,
                status=status,
                full_artifacts=bool(full_by_day.get(d.id, False)),
                is_missed=is_missed,
                deviation_note=note,
            )
        )

    # 课程进度 = 已通过且 seq <= view_seq 的天数
    completed = sum(
        1 for it in items if it.seq <= view_seq and it.status in PROGRESS_PASSED
    )
    behind = max(0, view_seq - completed)

    return ok(
        PlanOverview(
            day_index=day_index,
            total_days=TOTAL_DAYS,
            sprint_start=SPRINT_START,
            sprint_end=SPRINT_END,
            calendar_days_elapsed=elapsed,
            is_before_start=before_start,
            is_after_end=after_end,
            behind=behind,
            completed_days=completed,
            days=items,
        )
    )


@router.post("/progress")
def set_progress(
    payload: ProgressUpdate, db: Session = Depends(get_db)
) -> ApiResponse[DayProgressOut]:
    """手动记录一天的执行决策（P1 滑期机制的写入口）。

    滑期约束（风险 3）：落后时**只提示、不自动顺延**。
    用户必须显式选 status（压缩 / 顺延 / 放弃 / 完成），且建议写 deviation_note。

    幂等 upsert：同一 plan_day_id 重复提交会更新既有记录。
    done/compressed 时写入执行日期（你真的在这一天做了）；
    deferred/skipped 清空执行日期（你没在这一天执行）。
    """

    day = db.get(PlanDay, payload.plan_day_id)
    if day is None:
        raise HTTPException(status_code=404, detail="PlanDay not found")

    rec = (
        db.query(DayProgress)
        .filter(DayProgress.plan_day_id == payload.plan_day_id)
        .first()
    )
    if rec is None:
        rec = DayProgress(plan_day_id=payload.plan_day_id)
        db.add(rec)

    rec.status = payload.status
    if payload.deviation_note is not None:
        rec.deviation_note = payload.deviation_note
    if payload.actual_minutes is not None:
        rec.actual_minutes = payload.actual_minutes

    # 实际执行（done/compressed）才写执行日期；顺延/放弃不写（你没在这一天执行）
    if payload.status in (PROGRESS_DONE, PROGRESS_COMPRESSED):
        rec.calendar_date = date.today().isoformat()
    else:
        rec.calendar_date = None

    db.commit()
    db.refresh(rec)
    return ok(
        DayProgressOut.model_validate(rec),
        message=f"已记录 Day {day.seq} → {payload.status}",
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


@router.post("/commits/sync")
def sync_commits(
    payload: CommitSyncIn | None = None, db: Session = Depends(get_db)
) -> ApiResponse[dict]:
    """GitHub commit 按课程日自动归集（P2 证据闭环核心机制之一）。

    映射：commit_date - SPRINT_START 天数 + 1 = 课程日序号；超出窗口跳过。
    写入 day_artifacts(kind=commit, auto_verified=True)，去重按 (plan_day, sha)。

    三路来源：
    1. payload.commits 直接传入（测试 / 演示，绕过 GitHub API）
    2. 真实 GitHub：repo/token 缺省读 PLAN_REPO / GITHUB_TOKEN 环境变量
    3. 未配置 token：优雅跳过，返回 skipped=True（不 500）
    """

    payload = payload or CommitSyncIn()
    repo = payload.repo or os.environ.get("PLAN_REPO")
    token = payload.token or os.environ.get("GITHUB_TOKEN")
    since = payload.since or SPRINT_START
    until = payload.until or date.today().isoformat()

    # 1) 测试 / 演示：直接传入 commit 列表
    if payload.commits:
        synced = _sync_commits_to_artifacts(db, payload.commits, SPRINT_START)
        return ok(
            {"synced": synced, "source": "inline"},
            message=f"已归集 {synced} 条 commit（inline）",
        )

    # 2) 未配置 token：优雅跳过
    if not token:
        return ok(
            {"synced": 0, "skipped": True, "reason": "未配置 GITHUB_TOKEN，跳过"},
            message="未配置 GITHUB_TOKEN，跳过 commit 归集",
        )

    # 3) 真实 GitHub
    try:
        commits = fetch_github_commits(repo, since, until, token)
    except RuntimeError as e:
        return ok({"synced": 0, "error": str(e)}, message=str(e))
    synced = _sync_commits_to_artifacts(db, commits, SPRINT_START)
    return ok(
        {"synced": synced, "repo": repo},
        message=f"已从 GitHub 归集 {synced} 条 commit",
    )
