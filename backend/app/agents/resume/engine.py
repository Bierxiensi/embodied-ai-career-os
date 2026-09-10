"""简历防虚构诊断引擎（纯规则，可解释，不依赖 LLM）。

核心约束（v2.0 §8「简历不虚构」）：
    ResumeAgent 输出的每条 claim 必须在 ResumeFact 有锚点，否则标红并列出依据。

实现要点：
1. extract_claims(md)：从简历 md 抽取可校验的 claim（bullet / 编号项 / 含指标的独立行），
   跳过 markdown 标题与纯"小节标签"（以冒号结尾的短行）。
2. diagnose(md, facts, required_skills?)：对每条 claim 在事实锚点库做归一化子串匹配；
   命中 → anchored（绿），未命中 → unanchored（红），并计算 fabrication_risk（未锚定占比）。
   若给定 required_skills（JD 要求技能），额外给出 jd_alignment：每条技能在事实/已锚定
   claim 中是否有依据。

所有匹配都是确定性规则，前端可逐条展示"为什么绿 / 为什么红 / 依据是什么"。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ───────────────────────────── 数据结构 ─────────────────────────────

@dataclass
class FactRecord:
    """事实锚点（来自 ResumeFact 行的最小表示）。"""

    id: int
    category: str
    title: str
    org: str | None
    facts: list[str]


@dataclass
class ResumeClaim:
    """一条被抽取的简历 claim 及其锚定结果。"""

    text: str
    anchored: bool = False
    anchors: list[dict] = field(default_factory=list)  # [{fact_id, title, category}]
    reason: str = ""


@dataclass
class JdAlignmentItem:
    """JD 要求技能在简历事实中的支撑情况。"""

    skill: str
    supported: bool
    evidence: str | None = None


@dataclass
class ResumeDiagnosis:
    """一次完整诊断结果。"""

    total: int
    anchored_count: int
    unanchored_count: int
    fabrication_risk: int  # 0-100（未锚定占比）
    claims: list[ResumeClaim] = field(default_factory=list)
    jd_alignment: list[JdAlignmentItem] | None = None


# ───────────────────────────── 抽取规则 ─────────────────────────────

# bullet： - / * / • ；或编号 1. / 1)
_BULLET_RE = re.compile(r"^\s*([-*•]|\d+[.)])\s+(.+)$")
# markdown 标题 # / ##
_HEADER_RE = re.compile(r"^\s*#{1,6}\s+")
# 小节标签：短行且以冒号结尾，如 "工作经历：" / "Skills:"
_SECTION_LABEL_RE = re.compile(r"^[\u4e00-\u9fa5A-Za-z0-9&/（）()]{1,14}[：:]\s*$")
# 指标 token：含数字 + 单位（%，台，份，倍，+，→，万，k，x），用于把含指标的非 bullet 行也当 claim
_METRIC_RE = re.compile(r"\d")


# 归一化时去除的标点/空白（保留中文、字母、数字、% + → 等事实常用符号）
_PUNCT_RE = re.compile(
    r"[\s，。、；：,.;:!！？?（）()\[\]【】“”\"'·/\\|~`@#$^&*_=<>—\-]"
)


def _norm(text: str) -> str:
    """归一化：去空白 + 去标点 + 转小写，便于子串匹配。

    保留 % + → 等事实常用符号，避免破坏 '56%→90%' / '3000+ 份' 这类可锚定短语。
    """
    return _PUNCT_RE.sub("", text).lower()


def _strip_inline(md_line: str) -> str:
    """去掉行内 markdown 强调符号（** / ` / 粗体），保留文字。"""
    return md_line.replace("**", "").replace("`", "").strip()


def extract_claims(md: str | None) -> list[str]:
    """从简历 md 抽取可校验的 claim 列表（去重、保序）。

    抽取规则：
    - bullet / 编号项：剥离标记符后作为 claim
    - 非标题、非小节标签的独立行，若长度 >= 6 或含数字，作为 claim
    - 标题（# 开头）与"小节标签"（短且以冒号结尾）跳过
    """
    if not md:
        return []

    claims: list[str] = []
    seen: set[str] = set()

    for raw in md.splitlines():
        line = raw.strip()
        if not line:
            continue

        # markdown 标题：跳过
        if _HEADER_RE.match(line):
            continue

        # bullet / 编号项
        m = _BULLET_RE.match(raw)
        if m:
            text = _strip_inline(m.group(2))
            if text and text not in seen:
                claims.append(text)
                seen.add(text)
            continue

        # 小节标签（短 + 冒号结尾）：跳过
        if _SECTION_LABEL_RE.match(line):
            continue

        # 普通独立行：长度够或含数字才当 claim，避免噪声
        text = _strip_inline(line)
        if len(text) >= 6 or _METRIC_RE.search(text):
            if text and text not in seen:
                claims.append(text)
                seen.add(text)

    return claims


# ───────────────────────────── 锚定规则 ─────────────────────────────

# 锚点片段最小长度：避免 "AI" / "RL" 等过短 token 误命中
_MIN_ANCHOR_LEN = 2


def _fact_searchable(fact: FactRecord) -> list[str]:
    """构事实可检索片段（title / org / 每条 facts），归一化。"""
    segs: list[str] = []
    for s in [fact.title, fact.org or "", *fact.facts]:
        n = _norm(s)
        if n:
            segs.append(n)
    return segs


def _claim_anchors(claim_norm: str, facts: list[FactRecord]) -> list[dict]:
    """返回 claim 命中的事实锚点列表（可能多个）。

    匹配方向：fact 片段 ⊆ claim（最常见，简历里复述了事实原文），
    或 claim ⊆ fact 片段（claim 是事实的某部分）。两者任一即视为有依据。
    """
    anchors: list[dict] = []
    for fact in facts:
        if len(fact.title) < _MIN_ANCHOR_LEN and not fact.facts:
            continue
        for seg in _fact_searchable(fact):
            if len(seg) < _MIN_ANCHOR_LEN:
                continue
            if seg in claim_norm or claim_norm in seg:
                anchors.append({
                    "fact_id": fact.id,
                    "title": fact.title,
                    "category": fact.category,
                })
                break  # 同一事实命中一次即可
    return anchors


# ───────────────────────────── 诊断主流程 ─────────────────────────────

class ResumeEngine:
    """简历防虚构诊断（纯规则）。"""

    @staticmethod
    def diagnose(
        md: str | None,
        facts: list[FactRecord],
        required_skills: list[str] | None = None,
    ) -> ResumeDiagnosis:
        """对简历 md 做防虚构诊断。

        Args:
            md: 简历 markdown 原文
            facts: 事实锚点库（ResumeFact 行的最小表示）
            required_skills: 可选，JD 要求的规范技能名列表（用于 jd_alignment）
        """
        claims_text = extract_claims(md)

        claims: list[ResumeClaim] = []
        for text in claims_text:
            cn = _norm(text)
            anchors = _claim_anchors(cn, facts)
            if anchors:
                claims.append(ResumeClaim(
                    text=text,
                    anchored=True,
                    anchors=anchors,
                    reason=f"命中事实锚点：{anchors[0]['title']}",
                ))
            else:
                claims.append(ResumeClaim(
                    text=text,
                    anchored=False,
                    anchors=[],
                    reason="未在事实锚点库找到依据，疑似虚构或需补充事实",
                ))

        anchored = [c for c in claims if c.anchored]
        unanchored = [c for c in claims if not c.anchored]
        total = len(claims)
        risk = int(round((len(unanchored) / total) * 100)) if total else 0

        jd_alignment = None
        if required_skills:
            jd_alignment = _jd_alignment(required_skills, facts, anchored)

        return ResumeDiagnosis(
            total=total,
            anchored_count=len(anchored),
            unanchored_count=len(unanchored),
            fabrication_risk=risk,
            claims=claims,
            jd_alignment=jd_alignment,
        )


def _jd_alignment(
    required_skills: list[str],
    facts: list[FactRecord],
    anchored_claims: list[ResumeClaim],
) -> list[JdAlignmentItem]:
    """JD 要求的技能，在事实库 / 已锚定 claim 中是否有依据。"""

    # 可检索语料：事实片段 + 已锚定 claim 文本（归一化）
    corpus: list[str] = []
    for f in facts:
        corpus.extend(_fact_searchable(f))
    for c in anchored_claims:
        corpus.append(_norm(c.text))

    items: list[JdAlignmentItem] = []
    for skill in required_skills or []:
        sn = _norm(skill)
        if not sn:
            continue
        hit = None
        for seg in corpus:
            if sn in seg or seg in sn:
                hit = seg
                break
        # 还原展示用：直接给技能名 + 是否支撑
        items.append(JdAlignmentItem(
            skill=skill,
            supported=hit is not None,
            evidence=("命中事实/简历依据" if hit else None),
        ))
    return items
