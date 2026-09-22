"""Career Transition Dashboard 聚合服务（Phase 3）。

把"五区"里**不随日期变化**的三区（职业进度 / 当前工作 / 学术与博士）
从各自真源读出来拼成一份 payload：

    职业进度 ← services/readiness（就绪度，与 /api/job-hunt 同源）
             + core/transition_context.key_milestones()（关键节点倒计时）
    当前工作 ← core/transition_context.EMPLOYMENT / TRANSITION_WINDOW_*
    学术     ← core/transition_context.DEFENSE_*（答辩）
             + phd_targets / phd_advisors（博士申请进度）

另外两区（ROI 任务、风险雷达）留在 ``/api/plan/today`` —— 它们与"今天"强相关
（当日任务排序、当日风险取值），搬过来会让本服务承担 plan 的职责。

边界：本模块不写库、不改任何状态。``phd_advisors.match_json`` 是既有缓存的
**只读**消费，不在本端点里触发重算（重算是 /api/phd/advisors/match-all 的事）。
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.transition_context import (
    DEFENSE_DEADLINE,
    DEFENSE_LABEL,
    EMPLOYMENT,
    PHD_APPLICATION_SEASON_LABEL,
    PHD_CONTACT_WINDOW,
    PHD_WINDOW_LABEL,
    TRANSITION_WINDOW_END,
    TRANSITION_WINDOW_START,
    days_until,
    key_milestones,
)
from app.models.phd import PhDAdvisor, PhDTarget
from app.services.career_mode import service as career_mode_service
from app.services.readiness.service import (
    all_roles_readiness,
    load_skill_levels,
    primary_readiness,
)

# 倒计时紧张度分档（唯一权威，前端不重算）
#
# 分档而不是给连续天数：页面要的是"该不该现在动手"，
# 45 天与 44 天的区别没有意义，但"进入 30 天内"是行动信号。
#   overdue  已过期（负数）
#   urgent   30 天内 —— 必须本周动手
#   soon     90 天内 —— 排进本月
#   ok       90 天以上
STATUS_URGENT_DAYS = 30
STATUS_SOON_DAYS = 90


def _status_for(days_left: int) -> str:
    """把剩余天数映射成紧张度分档。见上面的阈值常量。"""

    if days_left < 0:
        return "overdue"
    if days_left <= STATUS_URGENT_DAYS:
        return "urgent"
    if days_left <= STATUS_SOON_DAYS:
        return "soon"
    return "ok"


def build_career_progress(db: Session, today: date) -> dict:
    """第 1 区：职业进度（各赛道双轨就绪度 + 关键节点倒计时）。"""

    readiness = all_roles_readiness(load_skill_levels(db))
    primary = primary_readiness(readiness)

    tracks = [
        {
            "key": r.key,
            "name": r.name,
            "priority": r.priority,
            "frozen": r.frozen,
            "match_pct": r.match_pct,
            "strict_pct": r.strict_pct,
            "qualified_count": r.qualified_count,
            "required_count": r.required_count,
            "skill_count": r.skill_count,
            "gap_count": r.gap_count,
        }
        for r in readiness
    ]

    milestones = [
        {
            "key": m.key,
            "label": m.label,
            "deadline": m.deadline,
            "days_left": days_until(m.deadline, today),
            "status": _status_for(days_until(m.deadline, today)),
            "note": m.note,
        }
        for m in key_milestones()
    ]

    return {
        "primary_track_key": primary.key if primary else None,
        "tracks": tracks,
        "milestones": milestones,
    }


def build_position() -> dict:
    """第 2 区：当前工作（在职事实 + 在职转型窗口）。"""

    return {
        "company": EMPLOYMENT.company,
        "role": EMPLOYMENT.role,
        "focus": EMPLOYMENT.focus,
        "since_label": EMPLOYMENT.since_label,
        "end_label": EMPLOYMENT.end_label,
        "status_label": EMPLOYMENT.status_label,
        "note": EMPLOYMENT.note,
        "transition_window_start": TRANSITION_WINDOW_START,
        "transition_window_end": TRANSITION_WINDOW_END,
        "transition_window_label": f"{TRANSITION_WINDOW_START} – {TRANSITION_WINDOW_END}",
    }


def build_academic(db: Session, today: date, top_n: int = 3) -> dict:
    """第 3 区：学术（硕士答辩 + 博士申请进度）。

    ``top_advisors`` 按六维匹配 overall 降序取前 N；
    没有 match_json 的导师排最后（不是排除 —— 用户刚录入还没算过匹配时
    这些人也要出现在列表里，否则"录了导师但落地页看不到"会很困惑）。
    """

    defense_days = days_until(DEFENSE_DEADLINE, today)
    degree = {
        "label": DEFENSE_LABEL,
        "deadline": DEFENSE_DEADLINE,
        "days_left": defense_days,
        "status": _status_for(defense_days),
        "note": "学位论文答辩硬截止；风险雷达的 academic 维度取同一日期",
    }

    window_days = days_until(PHD_CONTACT_WINDOW, today)

    targets = db.query(PhDTarget).all()
    advisors = db.query(PhDAdvisor).all()
    target_by_id = {t.id: t for t in targets}

    def _sort_key(a: PhDAdvisor) -> tuple[int, int, int]:
        match = a.match_json or {}
        overall = match.get("overall")
        return (
            -(overall if isinstance(overall, (int, float)) else -1),
            0 if a.contacted else 1,   # 同分时已联系的排前面（更有关注价值）
            a.id,
        )

    top_advisors = []
    for a in sorted(advisors, key=_sort_key)[:top_n]:
        target = target_by_id.get(a.target_id) if a.target_id else None
        match = a.match_json or {}
        overall = match.get("overall")
        top_advisors.append(
            {
                "id": a.id,
                "name": a.name,
                "institution": target.institution if target else None,
                "tier": target.tier if target else None,
                "contacted": bool(a.contacted),
                "match_overall": int(overall) if isinstance(overall, (int, float)) else None,
                "match_grade": match.get("grade"),
                "match_overall_max": 100,
            }
        )

    # 最近的申请截止日。
    #
    # 优先取**未过期里最早的那个**（那是真正要盯的日期）。
    # 若全部已过期，则退回**已过期里最晚的那个**并如实报出负数天数 ——
    # 不返回 None，因为"有截止日但全都过期了"本身就是必须被看见的事
    # （当前种子数据的截止日多为 2025-12，属待补录状态，落地页要能暴露这一点）。
    dated = [t for t in targets if t.application_deadline is not None]
    nearest = None
    if dated:
        future = [t for t in dated if t.application_deadline >= today]
        if future:
            picked = min(future, key=lambda t: t.application_deadline)
        else:
            picked = max(dated, key=lambda t: t.application_deadline)
        nearest = {
            "institution": picked.institution,
            "deadline": picked.application_deadline,
            "days_left": days_until(picked.application_deadline, today),
        }

    phd = {
        "season_label": PHD_APPLICATION_SEASON_LABEL,
        "window_label": PHD_WINDOW_LABEL,
        "window_deadline": PHD_CONTACT_WINDOW,
        "window_days_left": window_days,
        "window_status": _status_for(window_days),
        "target_count": len(targets),
        "advisor_count": len(advisors),
        "contacted_count": sum(1 for a in advisors if a.contacted),
        "matched_count": sum(1 for a in advisors if a.match_json),
        "nearest_deadline": nearest,
        "top_advisors": top_advisors,
    }

    return {"degree": degree, "phd": phd}


def build_dashboard(db: Session, today: date | None = None) -> dict:
    """五区中由本服务负责的三区 + 当前模式。

    返回**纯 dict**（不含 Pydantic 模型）：路由负责包 ``ok()`` 与校验契约，
    服务层不依赖 schemas —— 与 services/career_mode 的返回约定一致。
    """

    as_of = today or date.today()
    mode = career_mode_service.get_current_mode(db)
    return {
        "as_of": as_of,
        "mode": mode,
        "career_progress": build_career_progress(db, as_of),
        "position": build_position(),
        "academic": build_academic(db, as_of),
    }
