"""日报 / 周报引擎（Batch 4）。

纯规则：读库 → 组装 ``ReportData``（分段落 + 指标）→ 渲染 markdown。
不依赖 LLM、可单测、可解释 —— 与 Match / Resume / Interview 三个引擎同一取向
（见 JOB_SEARCH_AGENT_DESIGN.md §0.1.3 的有意偏离说明）。

设计文档 §7 约定：

- 日报（每日 08:30）：新推荐岗位 / 匹配理由 / 简历动作 / 面试题 / 学习任务 /
  投递状态 / 今日优先
- 周报（每周一 09:00）：投递统计 / 能力差距 / 项目进度 / 面试汇总 / 下周任务 /
  博士积累
- 跟进提醒（每日 10:00）：``next_action`` 到期 / 停滞过久的投递

本模块只负责"算什么"与"长什么样"，"发给谁 / 存哪"交给 ``service.py``。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from app.models.job_match import (
    DIM_EDU_EXP,
    DIM_INDUSTRY,
    DIM_PROJECT,
    DIM_RESEARCH,
    DIM_TECH,
)

# ─────────────────────────── 常量 ───────────────────────────

REPORT_DAILY = "daily"
REPORT_WEEKLY = "weekly"

DIM_LABELS: dict[str, str] = {
    DIM_TECH: "技术栈",
    DIM_PROJECT: "项目",
    DIM_EDU_EXP: "学历/年限",
    DIM_RESEARCH: "科研",
    DIM_INDUSTRY: "行业",
}

TRACK_LABELS: dict[str, str] = {
    "llm": "LLM",
    "vlm": "VLM",
    "ai-algo": "AI算法",
    "embodied": "具身",
    "other": "其他",
}

# 科研底座（博士叙事起点）——与 core/skill_profile.py「科研底座」段保持一致
RESEARCH_SKILL_NAMES: tuple[str, ...] = ("Small-data Forecasting", "Explainability")

# applied / screening 属于"还在推进"，超过 stale 天无更新即提醒跟进
_ACTIVE_STATUSES: tuple[str, ...] = ("applied", "screening")
DEFAULT_STALE_DAYS = 5

# 日报各段落最多展示条数（控制推送长度）
_DAILY_LIMIT = 3
_MAX_BULLETS = 5


# ─────────────────────────── 数据结构 ───────────────────────────

@dataclass
class ReportSection:
    """报告的一段。``lines`` 为空时渲染为"（无）"。"""

    key: str
    title: str
    lines: list[str] = field(default_factory=list)


@dataclass
class ReportData:
    """一份报告。``metrics`` 供前端做结构化展示，``sections`` 供推送渲染。"""

    kind: str
    period_key: str
    title: str
    sections: list[ReportSection]
    metrics: dict = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "period_key": self.period_key,
            "title": self.title,
            "sections": [
                {"key": s.key, "title": s.title, "lines": s.lines} for s in self.sections
            ],
            "metrics": self.metrics,
            "generated_at": self.generated_at.isoformat(),
        }


# ─────────────────────────── 小工具 ───────────────────────────

def _today(today: date | None) -> date:
    return today or date.today()


def week_key(d: date) -> str:
    """ISO 年-周标识，如 ``2026-W37``。同一周内重复生成视为同一期。"""
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def week_bounds(today: date) -> tuple[date, date]:
    """返回本周一 ~ 本周日。"""
    start = today - timedelta(days=today.weekday())
    return start, start + timedelta(days=6)


def parse_next_action_date(text: str | None, ref: date) -> date | None:
    """从 ``next_action`` 文本里解析日期。

    支持 ``2026-09-12`` / ``9/12`` / ``09-12`` / ``12日`` 四类写法；
    跨年（解析出的月份小于当前月）时按明年处理。
    """
    if not text:
        return None
    s = str(text)

    m = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None

    m = re.search(r"(\d{1,2})[-/](\d{1,2})", s)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = ref.year
        try:
            d = date(year, month, day)
        except ValueError:
            return None
        if d < ref - timedelta(days=180):  # 明显属于去年 → 顺延到明年
            try:
                d = date(year + 1, month, day)
            except ValueError:
                return None
        return d

    m = re.search(r"(\d{1,2})\s*日", s)
    if m:
        day = int(m.group(1))
        try:
            d = date(ref.year, ref.month, day)
        except ValueError:
            return None
        if d < ref:
            nxt = ref.replace(day=28) + timedelta(days=5)  # 落到下月
            try:
                d = date(nxt.year, nxt.month, day)
            except ValueError:
                return None
        return d

    return None


def funnel_of(apps: list) -> dict:
    """投递漏斗统计（``apps`` 为 JobApplication 列表或 dict 列表）。"""
    counts = {"applied": 0, "screening": 0, "interview": 0, "offer": 0, "rejected": 0}
    for a in apps:
        status = a["status"] if isinstance(a, dict) else a.status
        counts[status] = counts.get(status, 0) + 1
    total = len(apps)
    responded = counts["screening"] + counts["interview"] + counts["offer"]
    return {
        "total": total,
        "applied": counts["applied"],
        "screening": counts["screening"],
        "interview": counts["interview"],
        "offer": counts["offer"],
        "rejected": counts["rejected"],
        "response_rate": round(responded / total * 100) if total else 0,
    }


def due_followups(
    db,
    today: date | None = None,
    stale_days: int = DEFAULT_STALE_DAYS,
) -> list[dict]:
    """需要跟进的投递。

    两种触发条件（或的关系）：

    1. ``next_action`` 里能解析出日期且 <= 今天 → 计划到期；
    2. 状态仍为 applied/screening 且 ``updated_at`` 距今 >= ``stale_days`` → 停滞超期。

    返回 ``[{id, company, role, status, next_action, reason, days}]``，按紧急度降序。
    """
    from app.models.job_application import JobApplication

    ref = _today(today)
    out: list[dict] = []

    for a in db.query(JobApplication).order_by(JobApplication.id).all():
        planned = parse_next_action_date(a.next_action, ref)
        updated = (a.updated_at or a.created_at or datetime.utcnow()).date()
        idle_days = (ref - updated).days

        reason = None
        overdue = False
        if planned is not None and planned <= ref:
            overdue = True
            reason = f"计划 {planned.month}/{planned.day} 到期"
        elif a.status in _ACTIVE_STATUSES and idle_days >= stale_days:
            reason = f"停滞 {idle_days} 天无进展"

        if reason is None:
            continue

        out.append({
            "id": a.id,
            "company": a.company,
            "role": a.role,
            "status": a.status,
            "next_action": a.next_action,
            "reason": reason,
            "days": idle_days,
            "overdue": overdue,
        })

    out.sort(key=lambda x: (not x["overdue"], -x["days"]))
    return out


# ─────────────────────────── 日报 ───────────────────────────

def _daily_postings(db, limit: int = _DAILY_LIMIT) -> tuple[list[str], list[dict]]:
    """今日推荐岗位（A/B 级）+ 匹配理由。"""
    from app.models.job_match import JobMatch
    from app.models.job_posting import JobPosting

    matches = {m.posting_id: m for m in db.query(JobMatch).all()}
    rows: list[tuple[int, object, object]] = []
    for p in db.query(JobPosting).all():
        m = matches.get(p.id)
        if m and m.grade in ("A", "B"):
            rows.append((m.match_score, p, m))
    rows.sort(key=lambda r: -r[0])

    lines: list[str] = []
    metrics: list[dict] = []
    for score, p, m in rows[:limit]:
        track = TRACK_LABELS.get(p.track or "other", p.track or "其他")
        # 匹配理由：得分最高的维度 + 前两个缺口
        dims = m.dimension_scores or {}
        best_dim = max(dims, key=lambda k: dims[k]) if dims else DIM_TECH
        best_label = DIM_LABELS.get(best_dim, best_dim)
        gaps = (m.gaps or [])[:2]
        gap_str = "、".join(f"{g['skill']} {g['level']}→{g['required']}" for g in gaps) or "无硬缺口"
        lines.append(
            f"{p.company} · {p.title}｜{m.grade}{score}｜{track}"
            f"｜强项：{best_label}｜缺口：{gap_str}"
        )
        metrics.append({
            "id": p.id,
            "company": p.company,
            "title": p.title,
            "grade": m.grade,
            "score": m.match_score,
            "track": p.track,
            "gap_count": len(m.gaps or []),
        })
    return lines, metrics


def _daily_resume_actions(db, limit: int = _DAILY_LIMIT) -> tuple[list[str], list[str]]:
    """简历动作：按技能缺口给"补证据"建议。"""
    from app.models.resume_fact import ResumeFact
    from app.models.skill import Skill

    fact_count = db.query(ResumeFact).count()
    gaps = [
        s for s in db.query(Skill).all()
        if (s.target_level or 0) > (s.level or 0)
    ]
    gaps.sort(key=lambda s: (-((s.target_level or 0) - (s.level or 0)), s.name))

    lines: list[str] = []
    if fact_count == 0:
        lines.append("事实锚点库为空：先在 /resume 建立 ResumeFact，再让 Agent 改简历")
    for s in gaps[:limit]:
        lines.append(
            f"补 {s.name} 证据：Lv{s.level}→Lv{s.target_level}"
            f"（拿到证据后写入 ResumeFact，再更新版本）"
        )
    if not lines:
        lines.append("技能无缺口：保持现有版本与目标岗位对齐即可")

    return lines, [s.name for s in gaps[:limit]]


def _daily_questions(db, limit: int = 2) -> tuple[list[str], list[str]]:
    """今日面试题：命中次数最少者优先（保证覆盖面，不重复刷同几题）。"""
    from app.models.interview_question import InterviewQuestion

    rows = (
        db.query(InterviewQuestion)
        .order_by(InterviewQuestion.hit_count, InterviewQuestion.id)
        .limit(limit)
        .all()
    )
    lines = [f"[{q.category}/{q.difficulty}] {q.question}" for q in rows]
    return lines, [q.question for q in rows]


def _daily_tasks(db, limit: int = _DAILY_LIMIT) -> tuple[list[str], list[dict]]:
    """今日学习任务：todo / doing 优先。"""
    from app.models.task import Task

    rows = (
        db.query(Task)
        .filter(Task.status.in_(["todo", "doing"]))
        .order_by(Task.status, Task.id)
        .limit(limit)
        .all()
    )
    lines = [f"{t.title}（{t.duration or 30}min，{t.status}）" for t in rows]
    metrics = [
        {"id": t.id, "title": t.title, "status": t.status, "duration": t.duration}
        for t in rows
    ]
    return lines, metrics


def _daily_applications(db, today: date, stale_days: int) -> tuple[list[str], dict]:
    """投递状态 + 待跟进。"""
    from app.models.job_application import JobApplication

    apps = db.query(JobApplication).all()
    funnel = funnel_of(apps)
    lines = [
        f"在投 {funnel['total']}｜已投 {funnel['applied']} / 沟通 {funnel['screening']}"
        f" / 面试 {funnel['interview']} / offer {funnel['offer']}"
        f" / 已挂 {funnel['rejected']}｜响应率 {funnel['response_rate']}%"
    ]

    due = due_followups(db, today, stale_days)
    if due:
        names = "、".join(f"{d['company']}（{d['reason']}）" for d in due[:3])
        lines.append(f"待跟进 {len(due)} 家：{names}")
    else:
        lines.append("无待跟进：投递节奏正常")

    funnel["due_followups"] = len(due)
    return lines, funnel


def _daily_priority(
    gaps: list[str],
    postings: list[dict],
    tasks: list[dict],
    due: int,
    days_left: int,
) -> list[str]:
    """今日优先：确定性合成，最多 4 条（含 offer 倒计时）。"""
    out: list[str] = []
    if due:
        out.append(f"跟进到期投递（{due} 家）—— 求职 > 学习，先清跟进")
    elif postings:
        top = postings[0]
        out.append(f"投递 {top['company']}（{top['grade']}{top['score']}，缺口 {top['gap_count']} 项）")
    else:
        out.append("在 /jd 录入 1 条新 JD，补足岗位池")

    if tasks:
        out.append(f"完成学习任务：{tasks[0]['title']}")

    if gaps:
        out.append(f"为 {gaps[0]} 准备一条可写入简历的证据")

    if days_left >= 0:
        out.append(f"距离 offer 目标还有 {days_left} 天")
    return out[:4]


def build_daily(
    db,
    today: date | None = None,
    stale_days: int = DEFAULT_STALE_DAYS,
) -> ReportData:
    """组装日报（设计文档 §7 日报行）。"""
    from app.models.career import Career

    ref = _today(today)

    posting_lines, posting_metrics = _daily_postings(db)
    resume_lines, gap_names = _daily_resume_actions(db)
    question_lines, _ = _daily_questions(db)
    task_lines, task_metrics = _daily_tasks(db)
    app_lines, funnel = _daily_applications(db, ref, stale_days)

    career = db.query(Career).first()
    deadline = _offer_deadline(career)
    days_left = (deadline - ref).days

    sections = [
        ReportSection("postings", "🎯 今日推荐岗位（不盲投）", posting_lines),
        ReportSection("resume", "📄 简历动作", resume_lines),
        ReportSection("questions", "🧠 今日面试题", question_lines),
        ReportSection("tasks", "📚 今日学习任务", task_lines),
        ReportSection("applications", "📮 投递状态", app_lines),
    ]
    priority = _daily_priority(
        gap_names, posting_metrics, task_metrics, funnel["due_followups"], days_left
    )
    sections.append(ReportSection("priority", "⭐ 今日优先", priority))

    return ReportData(
        kind=REPORT_DAILY,
        period_key=ref.isoformat(),
        title=f"☀️ 求职日报 · {ref.month}月{ref.day}日（距 offer 目标 {days_left} 天）",
        sections=sections,
        metrics={
            "days_left": days_left,
            "deadline": deadline.isoformat(),
            "recommended_postings": len(posting_metrics),
            "top_postings": posting_metrics,
            "gap_top": gap_names,
            "due_followups": funnel["due_followups"],
            "todo_tasks": len(task_metrics),
            "funnel": funnel,
        },
        generated_at=datetime.utcnow(),
    )


# ─────────────────────────── 周报 ───────────────────────────

def _weekly_funnel(db, start: date, end: date) -> tuple[list[str], dict]:
    """投递统计（含本周新增）。"""
    from app.models.job_application import JobApplication

    apps = db.query(JobApplication).all()
    funnel = funnel_of(apps)
    new_this_week = sum(
        1 for a in apps
        if a.applied_at and start <= a.applied_at <= end
    )
    rate_note = ""
    if funnel["total"]:
        verdict = "达标" if funnel["response_rate"] >= 30 else "需优化简历/JD 匹配"
        rate_note = f"（目标 >30%，{verdict}）"
    lines = [
        f"累计投递 {funnel['total']}｜本周新增 {new_this_week}",
        f"漏斗：已投 {funnel['applied']} → 沟通 {funnel['screening']}"
        f" → 面试 {funnel['interview']} → offer {funnel['offer']}｜已挂 {funnel['rejected']}",
        f"响应率 {funnel['response_rate']}%{rate_note}",
    ]
    funnel["new_this_week"] = new_this_week
    return lines, funnel


def _weekly_gaps(db, limit: int = _MAX_BULLETS) -> tuple[list[str], list[dict]]:
    """能力差距 Top N（只列有 gap 的，30 天冲刺关注项）。"""
    from app.models.skill import Skill

    rows = [
        s for s in db.query(Skill).all()
        if (s.target_level or 0) > (s.level or 0)
    ]
    rows.sort(key=lambda s: (-((s.target_level or 0) - (s.level or 0)), s.name))

    lines = [
        f"{s.name}：Lv{s.level}→Lv{s.target_level}（差 {s.target_level - s.level}）"
        for s in rows[:limit]
    ]
    metrics = [
        {
            "name": s.name,
            "category": s.category,
            "level": s.level,
            "target_level": s.target_level,
            "gap": (s.target_level or 0) - (s.level or 0),
        }
        for s in rows[:limit]
    ]
    return lines, metrics


def _weekly_project(db) -> tuple[list[str], dict]:
    """项目进度（求职冲刺项目里程碑）。"""
    from app.core.target_roles import JOB_HUNT_PROJECT_NAME
    from app.models.milestone import Milestone
    from app.models.project import Project

    project = db.query(Project).filter(Project.name == JOB_HUNT_PROJECT_NAME).first()
    if project is None:
        return ["未找到求职冲刺项目（检查 seed 是否执行）"], {
            "name": None, "current_version": None, "completed": 0, "total": 0,
        }

    rows = (
        db.query(Milestone)
        .filter(Milestone.project_id == project.id)
        .order_by(Milestone.sort_order)
        .all()
    )
    done = [m for m in rows if m.status == "completed"]
    lines = [f"版本 {project.current_version or '-'}｜里程碑 {len(done)}/{len(rows)} 完成"]
    for m in rows:
        mark = "✅" if m.status == "completed" else ("🔄" if m.status == "in_progress" else "⏳")
        lines.append(f"{mark} {m.version} {m.title}（{m.status}）")

    metrics = {
        "name": project.name,
        "current_version": project.current_version,
        "completed": len(done),
        "total": len(rows),
        "milestones": [
            {"id": m.id, "version": m.version, "title": m.title, "status": m.status}
            for m in rows
        ],
    }
    return lines, metrics


def _weekly_interviews(db, start: date, end: date) -> tuple[list[str], dict]:
    """面试汇总：本周面经 + 弱项聚类。"""
    from app.agents.interview.engine import weakness_stats
    from app.models.interview_log import InterviewLog

    logs = db.query(InterviewLog).order_by(InterviewLog.id).all()
    in_week = []
    for log in logs:
        d = log.interviewed_at or (log.created_at.date() if log.created_at else None)
        if d and start <= d <= end:
            in_week.append(log)

    lines: list[str] = []
    if in_week:
        for log in in_week:
            rnd = f"（{log.round}）" if log.round else ""
            lines.append(f"{log.company} · {log.role}{rnd}")
    else:
        lines.append("本周无面试记录")

    stats = weakness_stats([
        {"id": log.id, "weak_questions": log.weak_questions or []} for log in in_week
    ])
    if stats:
        top = "；".join(f"{s.topic}×{s.count}" for s in stats[:3])
        lines.append(f"高频弱项：{top}")
    elif in_week:
        lines.append("本周无标注弱项")

    metrics = {
        "count": len(in_week),
        "logs": [
            {"id": log.id, "company": log.company, "role": log.role, "round": log.round}
            for log in in_week
        ],
        "weak_topics": [{"topic": s.topic, "count": s.count} for s in stats[:5]],
    }
    return lines, metrics


def _weekly_tasks(db, limit: int = _MAX_BULLETS) -> tuple[list[str], list[dict]]:
    """下周任务：未完成的 todo / doing。"""
    from app.models.task import Task

    rows = (
        db.query(Task)
        .filter(Task.status.in_(["todo", "doing"]))
        .order_by(Task.status, Task.id)
        .limit(limit)
        .all()
    )
    lines = [f"{t.title}（{t.duration or 30}min，{t.status}）" for t in rows]
    metrics = [
        {"id": t.id, "title": t.title, "status": t.status} for t in rows
    ]
    return lines, metrics


def _weekly_research(db) -> tuple[list[str], dict]:
    """博士积累：科研底座技能 + 论文叙事。"""
    from app.models.skill import Skill

    rows = (
        db.query(Skill)
        .filter(Skill.name.in_(list(RESEARCH_SKILL_NAMES)))
        .all()
    )
    by_name = {s.name: s for s in rows}
    lines: list[str] = []
    for name in RESEARCH_SKILL_NAMES:
        s = by_name.get(name)
        if s:
            lines.append(f"{name}：Lv{s.level}/Lv{s.target_level}（科研底座，简历可信度锚点）")
        else:
            lines.append(f"{name}：未入库（建议在技能画像补录，作为博士叙事起点）")
    lines.append("论文：EI 一作 STM-SHAP（已见刊）+ 学位论文 RL-RA-QR 在研 —— 保持每周有推进")

    metrics = {
        "skills": [
            {"name": name, "level": by_name[name].level if name in by_name else None}
            for name in RESEARCH_SKILL_NAMES
        ],
    }
    return lines, metrics


def build_weekly(db, today: date | None = None) -> ReportData:
    """组装周报（设计文档 §7 周报行）。"""
    ref = _today(today)
    start, end = week_bounds(ref)

    funnel_lines, funnel = _weekly_funnel(db, start, end)
    gap_lines, gap_metrics = _weekly_gaps(db)
    project_lines, project_metrics = _weekly_project(db)
    interview_lines, interview_metrics = _weekly_interviews(db, start, end)
    task_lines, task_metrics = _weekly_tasks(db)
    research_lines, research_metrics = _weekly_research(db)

    sections = [
        ReportSection("funnel", "📮 投递统计", funnel_lines),
        ReportSection("gaps", "📉 能力差距（Top 5）", gap_lines),
        ReportSection("project", "🚀 项目进度", project_lines),
        ReportSection("interviews", "🗣 面试汇总", interview_lines),
        ReportSection("tasks", "📅 下周任务", task_lines),
        ReportSection("research", "🎓 博士积累", research_lines),
    ]

    return ReportData(
        kind=REPORT_WEEKLY,
        period_key=week_key(ref),
        title=f"📊 求职周报 · {week_key(ref)}（{start.month}/{start.day}–{end.month}/{end.day}）",
        sections=sections,
        metrics={
            "week_start": start.isoformat(),
            "week_end": end.isoformat(),
            "funnel": funnel,
            "gaps": gap_metrics,
            "project": project_metrics,
            "interviews": interview_metrics,
            "tasks": task_metrics,
            "research": research_metrics,
        },
        generated_at=datetime.utcnow(),
    )


# ─────────────────────────── 渲染 ───────────────────────────

def render(data: ReportData) -> tuple[str, str]:
    """把 ReportData 渲染为 ``(title, markdown_body)``，供推送通道使用。"""
    parts: list[str] = []
    for sec in data.sections:
        parts.append(f"【{sec.title}】")
        if sec.lines:
            parts.extend(f"· {line}" for line in sec.lines)
        else:
            parts.append("· （无）")
        parts.append("")
    return data.title, "\n".join(parts).strip()


def _offer_deadline(career) -> date:
    """从 Career.timeframe 解析 offer 目标日期，失败回退默认值。"""
    from app.core.target_roles import DEFAULT_OFFER_DEADLINE

    if career is not None and career.timeframe:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y"):
            try:
                d = datetime.strptime(career.timeframe, fmt).date()
                if fmt == "%Y-%m":
                    nxt = date(d.year + (d.month == 12), (d.month % 12) + 1, 1)
                    return nxt - timedelta(days=1)
                if fmt == "%Y":
                    return date(d.year, 12, 31)
                return d
            except ValueError:
                continue
    return datetime.strptime(DEFAULT_OFFER_DEADLINE, "%Y-%m-%d").date()
