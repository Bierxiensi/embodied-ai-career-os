"""Career ROI 纯函数（Phase 2）。

给当日任务算一个 ROI，取 Top5 作为「今天最值得做」的附加视图。
纯规则，无 LLM 依赖。各维归一启发式 v1（标注"可配置"，后续可调权重）。

``roi = (Σ weight×dim) × (40 / max(duration or 40, 20))``
短任务增益、长任务打折；最终 cap 1.5。
"""

from __future__ import annotations

from dataclasses import dataclass

# 四维权重（可配置）
WEIGHTS = {
    "skill_delta": 0.3,
    "goal_relevance": 0.3,
    "evidence_value": 0.2,
    "real_project": 0.2,
}

# ROI 上限（可配置）
ROI_CAP = 1.5

# 各来源的"真实项目"分（可配置）
_REAL_PROJECT_SCORES = {"planner": 0.8, "user": 0.6, "seed": 0.5}


@dataclass
class RoiResult:
    """单个任务的 ROI 计算结果。"""

    roi: float
    reasons: list[str]

    def to_dict(self) -> dict:
        return {"roi": self.roi, "reasons": self.reasons}


def compute_task_roi(
    skill_name: str | None,
    skill_gap: int,
    track_keys_active: tuple[str, ...],
    main_track_required: list[str],
    task_source: str,
    duration_minutes: int | None,
    track_key: str | None = None,
) -> RoiResult:
    """计算单任务 ROI。

    参数说明：
    - skill_name：任务关联技能名（None 表示非技能类任务，如写周报）
    - skill_gap：该技能 target_level - level（无技能传 0）
    - track_keys_active：当前 CareerMode 的 active_track_keys
    - main_track_required：主攻赛道 required_skills（小写比较）
    - task_source：user / seed / planner
    - duration_minutes：任务预计时长（分钟）
    - track_key：任务所属赛道（用于"任务带赛道且属生效赛道 → 0.6"判定）

    各维归一（0-1）：
    - skill_delta = min(gap, 3) / 3（gap 越大越值钱；无关联技能 = 0.2 保底）
    - goal_relevance = 技能 ∈ 主攻 → 1.0；任务带 track_key 且 ∈ active → 0.6；其余 0.3
    - evidence_value = 技能非空 → 0.7；空 → 0.3
    - real_project = planner 0.8 / user 0.6 / seed 0.5
    """

    # 技能增量：gap 越大越值钱（封顶 3），无关联技能保底 0.2
    skill_delta = min(skill_gap, 3) / 3 if skill_name else 0.2

    # 目标相关度
    main_required_lower = {s.lower() for s in main_track_required}
    if skill_name and skill_name.lower() in main_required_lower:
        goal_relevance = 1.0
    elif track_key and track_key.lower() in {t.lower() for t in track_keys_active}:
        goal_relevance = 0.6
    else:
        goal_relevance = 0.3

    # 证据价值
    evidence_value = 0.7 if skill_name else 0.3

    # 真实项目
    real_project = _REAL_PROJECT_SCORES.get(task_source, 0.5)

    weighted = (
        WEIGHTS["skill_delta"] * skill_delta
        + WEIGHTS["goal_relevance"] * goal_relevance
        + WEIGHTS["evidence_value"] * evidence_value
        + WEIGHTS["real_project"] * real_project
    )

    duration = duration_minutes or 40
    duration_factor = 40 / max(duration, 20)
    roi = min(weighted * duration_factor, ROI_CAP)
    # 四舍五入避免浮点尾巴；不影响排序比较
    roi = round(roi, 4)

    reasons = [
        f"技能增量 {skill_delta:.2f}",
        f"目标相关度 {goal_relevance:.2f}",
        f"证据价值 {evidence_value:.2f}",
        f"真实项目 {real_project:.2f}",
        f"时长系数 {duration_factor:.2f}",
    ]
    return RoiResult(roi=roi, reasons=reasons)
