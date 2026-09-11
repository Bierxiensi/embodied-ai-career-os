"""技能晋级 evidence-gated 推导（证据闭环 P2 · 决策 3）。

把「技能等级」从自评变成从真实证据推导：

    L1 能解释     → 该技能映射课程日有 note 产出，或有关联面试题（skill_name）
    L2 能实现/修改 → 该日有 code 产出 + 已归集 commit（auto_verified）
    L3 能做实验   → 一条 Experiment（skill_name 命中）
    L4 能研究     → 对比实验（变体>=2 且 kind∈finetune/ablation）+ 复现报告 note

返回 {gate_level, evidence:[{level, kind, label, ref}]}，
evidence 的 ref 即前端「技能升级弹窗显示因为这份代码」的文案来源。

技能 → 课程日的映射复用 plan_30d.SKILL_TO_DAY_SEQ（只收录课程特有技能，
通用技能不映射，避免错绑 —— 见该文件注释）。
"""

from __future__ import annotations

from app.core.plan_30d import SKILL_TO_DAY_SEQ
from app.models.day_artifact import ARTIFACT_KIND_CODE, ARTIFACT_KIND_COMMIT, ARTIFACT_KIND_NOTE
from app.models.day_artifact import DayArtifact
from app.models.experiment import Experiment
from app.models.interview_question import InterviewQuestion
from app.models.plan_day import PlanDay


# 视为「对比实验」的类型（多变体才有公平对比）
_COMPARISON_KINDS = {"finetune", "ablation"}


def compute_skill_evidence(skill_name: str, db) -> dict:
    """推导某技能的证据等级与证据清单。

    Args:
        skill_name: 技能名（与 skills.name / SKILL_TO_DAY_SEQ 对齐）
        db: SQLAlchemy Session

    Returns:
        {"gate_level": int(0-4), "evidence": [{level, kind, label, ref}, ...]}
    """

    gate = 0
    evidence: list[dict] = []

    day_seq = SKILL_TO_DAY_SEQ.get(skill_name)
    plan_day = (
        db.query(PlanDay).filter(PlanDay.seq == day_seq).first() if day_seq else None
    )
    pid = plan_day.id if plan_day else None

    # ── L1 能解释 ──
    if pid is not None:
        note_arts = (
            db.query(DayArtifact)
            .filter(DayArtifact.plan_day_id == pid, DayArtifact.kind == ARTIFACT_KIND_NOTE)
            .all()
        )
        if note_arts:
            gate = max(gate, 1)
            evidence.append(
                {
                    "level": 1,
                    "kind": "note",
                    "label": "能解释",
                    "ref": f"Day {day_seq} 的笔记：{note_arts[0].title or '技术笔记'}",
                }
            )
    q_for_skill = (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.skill_name == skill_name)
        .all()
    )
    if q_for_skill:
        gate = max(gate, 1)
        verified = sum(1 for q in q_for_skill if q.is_verified)
        evidence.append(
            {
                "level": 1,
                "kind": "question",
                "label": "能解释",
                "ref": f"{len(q_for_skill)} 道关联面试题（{verified} 道已通过验收）",
            }
        )

    # ── L2 能实现 / 修改 ──
    if pid is not None:
        code_arts = (
            db.query(DayArtifact)
            .filter(DayArtifact.plan_day_id == pid, DayArtifact.kind == ARTIFACT_KIND_CODE)
            .all()
        )
        commit_arts = (
            db.query(DayArtifact)
            .filter(
                DayArtifact.plan_day_id == pid,
                DayArtifact.kind == ARTIFACT_KIND_COMMIT,
                DayArtifact.auto_verified == True,  # noqa: E712
            )
            .all()
        )
        if code_arts and commit_arts:
            gate = max(gate, 2)
            evidence.append(
                {
                    "level": 2,
                    "kind": "code",
                    "label": "能实现/修改",
                    "ref": (
                        f"Day {day_seq} 的代码 {code_arts[0].title or 'code'} "
                        f"+ 已归集 commit（auto_verified）"
                    ),
                }
            )

    # ── L3 能做实验 ──
    exps = db.query(Experiment).filter(Experiment.skill_name == skill_name).all()
    if exps:
        gate = max(gate, 3)
        evidence.append(
            {
                "level": 3,
                "kind": "experiment",
                "label": "能做实验",
                "ref": f"实验：{exps[0].name}（{exps[0].kind}）",
            }
        )

    # ── L4 能研究 ──
    comparison = [
        e
        for e in exps
        if e.kind in _COMPARISON_KINDS and len(e.variants or []) >= 2
    ]
    if comparison and pid is not None:
        report = (
            db.query(DayArtifact)
            .filter(DayArtifact.plan_day_id == pid, DayArtifact.kind == ARTIFACT_KIND_NOTE)
            .all()
        )
        if report:
            gate = max(gate, 4)
            evidence.append(
                {
                    "level": 4,
                    "kind": "research",
                    "label": "能研究",
                    "ref": (
                        f"对比实验 {comparison[0].name}（"
                        f"{len(comparison[0].variants or [])} 变体）+ 复现报告"
                    ),
                }
            )

    return {"gate_level": gate, "evidence": evidence}
