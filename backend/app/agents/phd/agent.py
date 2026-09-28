"""博士六维匹配引擎（纯规则，可解释，不依赖 LLM）。

设计哲学复用 agents/match/engine.py：确定性规则、逐维可解释、可单测。
输入为已归一化的标量（方向兴趣分 / 院校层次 / 城市 / 成果门槛 / 在职友好 /
截止日），不直接碰 DB / LLM；API 层取字段后调用。

六维（权重合计 1.0）：
  direction_fit     研究方向契合  0.30  ← ResearchDirection.interest_weight
  institution_tier  院校层次      0.15
  geo               地域/在职便利 0.10
  publication_match 成果门槛匹配  0.15
  in_service_friend 在职/非全友好 0.15
  timeline          时间窗口      0.15

基准事实（镜像 docs/MY_CONTEXT.md + docs/北京在职博士-*.md）：
  用户：北航非全硕士在读（硕士），EI 一作（STM-SHAP），在职，北京，
        主攻 Post-Training(llm) + 多模态(vlm)，长期具身/VLA。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.models.job_match import grade_of

# 院校层次 → 分数
_TIER_SCORE: dict[str, int] = {
    "985": 92,
    "中科院": 90,
    "海外": 85,
    "211": 78,
    "双一流": 72,
    "市属": 60,
    "普通": 55,
}
_DEFAULT_TIER_SCORE = 60

# 成果门槛 → 分数（用户有 EI 一作）
_PUB_SCORE: dict[str, int] = {
    "none": 100,  # 无硬性要求
    "ei": 100,    # 用户有 EI 一作，满足
    "sci": 60,    # 用户为 EI 非 SCI，部分满足
}
_DEFAULT_PUB_SCORE = 75  # 未知 → 中性

WEIGHTS: dict[str, float] = {
    "direction_fit": 0.30,
    "institution_tier": 0.15,
    "geo": 0.10,
    "publication_match": 0.15,
    "in_service_friendly": 0.15,
    "timeline": 0.15,
}

# 低于该分的维度计入 gap（待补强项）
_GAP_THRESHOLD = 60

_HINTS: dict[str, str] = {
    "direction_fit": "研究方向与转型目标契合度偏低",
    "institution_tier": "院校层次一般，平台资源有限",
    "geo": "异地就读，在职便利性较差",
    "publication_match": "成果门槛高于现有基础（缺 SCI）",
    "in_service_friendly": "在职 / 非全友好度低，需额外确认名额",
    "timeline": "本轮申请窗口已错过或较远",
}


@dataclass
class PhDMatchResult:
    """一次博士机会六维匹配结果。"""

    overall: int
    grade: str
    dimensions: dict[str, int]
    gaps: list[dict] = field(default_factory=list)


def _timeline_score(deadline: date | None, today: date) -> int:
    """时间窗口分（2026-09-24 X4 修复）：按「窗口距今」分带计分。

    旧实现 None→70、≤365 天一律 100，导致不录截止日的排名虚高、
    一个月内截止的「来不及准备」反而满分。新分带：
      None→55 未公布（中性偏保守） | 已过期→20 | <30 天→50 来不及
      30-270 天→95 黄金窗口（有准备期） | 270-540→75 | 更远→55
    """

    if deadline is None:
        return 55
    days = (deadline - today).days
    if days < 0:
        return 20
    if days < 30:
        return 50
    if days <= 270:
        return 95
    if days <= 540:
        return 75
    return 55


class PhDMatchEngine:
    """博士机会六维匹配（纯规则）。

    compute 接收已归一化的标量入参，便于单测（不依赖 DB / LLM）。
    """

    @staticmethod
    def compute(
        direction_interest: int,
        tier: str | None,
        city: str | None,
        min_publication: str | None,
        target_in_service: bool,
        advisor_in_service: bool,
        application_deadline: date | None,
        today: date | None = None,
    ) -> PhDMatchResult:
        """计算六维匹配结果。

        Args:
            direction_interest: 该方向的用户兴趣契合基准分（0-100），
                通常取自 ResearchDirection.interest_weight。
            tier: 院校层次（985/211/双一流/中科院/市属/普通/海外）。
            city: 就读城市（含"北京"即视为本地便利）。
            min_publication: 成果门槛（none/ei/sci）。
            target_in_service: 院校/项目是否在职友好。
            advisor_in_service: 导师是否愿意带非全/在职。
            application_deadline: 报名截止日（None = 常年/未公布）。
            today: 计算基准日（默认当天，单测可注入）。
        """

        today = today or date.today()

        direction_fit = max(0, min(100, int(direction_interest)))
        institution_tier = _TIER_SCORE.get((tier or "").strip(), _DEFAULT_TIER_SCORE)
        geo = 100 if city and "北京" in city else 60
        publication_match = _PUB_SCORE.get(
            (min_publication or "").strip().lower(), _DEFAULT_PUB_SCORE
        )
        in_service = 100 if (target_in_service or advisor_in_service) else 40
        timeline = _timeline_score(application_deadline, today)

        dimensions = {
            "direction_fit": direction_fit,
            "institution_tier": institution_tier,
            "geo": geo,
            "publication_match": publication_match,
            "in_service_friendly": in_service,
            "timeline": timeline,
        }

        overall = int(round(sum(WEIGHTS[k] * dimensions[k] for k in WEIGHTS)))
        overall = max(0, min(100, overall))
        grade = grade_of(overall)

        gaps: list[dict] = []
        for k, v in dimensions.items():
            if v < _GAP_THRESHOLD:
                gaps.append({"dimension": k, "score": v, "hint": _HINTS[k]})

        return PhDMatchResult(
            overall=overall, grade=grade, dimensions=dimensions, gaps=gaps
        )
