"""七维风险雷达纯函数（Phase 2）。

规则口径全部定死（docs/task-packages/2026-09-21-phase2-risk-roi.md 规格 A），
无 LLM 依赖，LLM 未配置时全功能可用。输出统一为
``{key, label, level, reason}``，level ∈ "green" | "amber" | "red"。

同文件导出 ``track_strict_pct`` —— 供 /api/job-hunt 的 roles_out 复用，
消除「双实现」导致的口径漂移（llm 当前 67%/23%/3/13 是回归锚点）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# 固定参考日期（口径决策，不得自行调整）
DEFENSE_DEADLINE = date(2026, 12, 31)      # 答辩硬截止
PHD_CONTACT_WINDOW = date(2026, 11, 1)     # 导师联系窗口关闭日

# 公司 / 财务维度常量（恒 green，配置在文件顶部，便于一眼看清）
_COMPANY_REASON = "已确认留任，在职转型窗口 2026.09–2027.03"
_FINANCIAL_REASON = "在职收入稳定"


@dataclass
class RiskDimension:
    """单个风险维度。"""

    key: str
    label: str
    level: str          # green | amber | red
    reason: str


@dataclass
class RiskResult:
    """七维风险计算结果。"""

    dimensions: list[RiskDimension]
    overall_level: str  # 取最差维度

    def to_dict(self) -> dict:
        return {
            "dimensions": [
                {
                    "key": d.key,
                    "label": d.label,
                    "level": d.level,
                    "reason": d.reason,
                }
                for d in self.dimensions
            ],
            "overall_level": self.overall_level,
        }


def _level_rank(level: str) -> int:
    """level 严重程度排序：green < amber < red。"""

    return {"green": 0, "amber": 1, "red": 2}.get(level, 0)


def compute_risk(
    days_since_last_experiment: int | None,     # None = 从未有实验
    days_since_last_code_artifact: int | None,  # None = 从未有 code 产物
    defense_deadline_days: int,                 # 距 2026-12-31 答辩的天数
    has_defense_task: bool,                     # 是否存在标题/目标含"答辩"的任务
    contacted_advisors: int,                    # phd_advisors.contacted=True 计数
    phd_window_days: int,                       # 距 2026-11-01（导师联系窗口）天数
    main_track_strict_pct: int,                 # 主攻赛道严格达标率 0-100
    main_track_gap_ratio: float,                # 主攻赛道 gap>0 技能占比 0-1
    today: date | None = None,
) -> RiskResult:
    """七维风险计算（阈值定死，不得自行调整）。

    ``today`` 仅用于测试注入固定日期，生产路径由 API 层传入 ``date.today()``。
    """

    # 执行力：两项均 >7 天（或 None）→ red；任一 >3 天 → amber；否则 green
    exp_stale = days_since_last_experiment is None or days_since_last_experiment > 7
    code_stale = (
        days_since_last_code_artifact is None or days_since_last_code_artifact > 7
    )
    if exp_stale and code_stale:
        execution_level, execution_reason = "red", "超过 7 天无实验与代码产出"
    elif (days_since_last_experiment is not None and days_since_last_experiment > 3) or (
        days_since_last_code_artifact is not None
        and days_since_last_code_artifact > 3
    ):
        execution_level, execution_reason = "amber", "3 天内有动作，但超过 3 天未持续"
    else:
        execution_level, execution_reason = "green", "近 3 天有实验 / 代码产出"

    # 学术：<90 且无答辩任务 → red；<90 有任务 → amber；≥90 → green
    if defense_deadline_days < 90 and not has_defense_task:
        academic_level, academic_reason = "red", "距答辩不足 90 天且尚无答辩任务"
    elif defense_deadline_days < 90:
        academic_level, academic_reason = "amber", "距答辩不足 90 天，已有答辩任务在推进"
    else:
        academic_level, academic_reason = "green", "距答辩 ≥90 天，节奏可控"

    # 博士：<45 且 0 人 → red；<45 且 1-2 人 → amber；其余 green
    if phd_window_days < 45 and contacted_advisors == 0:
        phd_level, phd_reason = "red", "导师联系窗口不足 45 天，尚未联系任何导师"
    elif phd_window_days < 45 and contacted_advisors <= 2:
        phd_level, phd_reason = (
            "amber",
            f"导师联系窗口不足 45 天，已联系 {contacted_advisors} 位导师",
        )
    else:
        phd_level, phd_reason = (
            "green",
            f"导师联系窗口充裕，已联系 {contacted_advisors} 位导师",
        )

    # 技能：<20 → red；<40 → amber；≥40 → green
    if main_track_strict_pct < 20:
        skill_level, skill_reason = "red", f"主攻赛道严格达标率 {main_track_strict_pct}% < 20%"
    elif main_track_strict_pct < 40:
        skill_level, skill_reason = (
            "amber",
            f"主攻赛道严格达标率 {main_track_strict_pct}% < 40%",
        )
    else:
        skill_level, skill_reason = (
            "green",
            f"主攻赛道严格达标率 {main_track_strict_pct}% ≥ 40%",
        )

    # 职业：gap 占比 >0.6 → amber；否则 green
    if main_track_gap_ratio > 0.6:
        career_level, career_reason = (
            "amber",
            f"主攻赛道 gap 技能占比 {main_track_gap_ratio:.0%} > 60%",
        )
    else:
        career_level, career_reason = (
            "green",
            f"主攻赛道 gap 技能占比 {main_track_gap_ratio:.0%} ≤ 60%",
        )

    dimensions = [
        RiskDimension("execution", "执行力", execution_level, execution_reason),
        RiskDimension("academic", "学术", academic_level, academic_reason),
        RiskDimension("phd", "博士", phd_level, phd_reason),
        RiskDimension("skill", "技能", skill_level, skill_reason),
        RiskDimension("career", "职业", career_level, career_reason),
        RiskDimension("company", "公司", "green", _COMPANY_REASON),
        RiskDimension("financial", "财务", "green", _FINANCIAL_REASON),
    ]
    overall_level = max(dimensions, key=lambda d: _level_rank(d.level)).level
    return RiskResult(dimensions=dimensions, overall_level=overall_level)


def track_strict_pct(
    required_skills: list[str],
    required_level: int,
    skill_levels: dict[str, int],
) -> tuple[int, int, int]:
    """返回 (strict_pct, qualified_count, required_count)。skill_levels 键为小写规范名。

    与 /api/job-hunt roles_out 共用，消除双实现（口径同源）。
    strict_pct = level >= required_level 的技能占比；qualified_count 为达标技能数。
    """

    required_count = len(required_skills)
    if required_count == 0:
        return 0, 0, 0
    qualified = sum(
        1 for name in required_skills
        if skill_levels.get(name.lower(), 0) >= required_level
    )
    strict_pct = round(qualified / required_count * 100)
    return strict_pct, qualified, required_count
