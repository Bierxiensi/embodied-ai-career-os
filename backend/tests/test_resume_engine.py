"""简历防虚构引擎单测（Batch 2）。

覆盖：claim 抽取、锚点命中、无锚点标红、JD 对齐、种子事实可达。
全部为纯规则，不依赖 DB / LLM。
"""

from __future__ import annotations

import pytest

from app.agents.resume.engine import FactRecord, ResumeEngine, extract_claims
from app.schemas.resume import ResumeFactCreate


# 复用的小事实库（镜像种子里与测试相关的片段）
_FACTS: list[FactRecord] = [
    FactRecord(
        id=1,
        category="work",
        title="标书审核 Agent",
        org="东鉴",
        facts=["标书审核 Agent 覆盖率 56%→90%", "单份 30min→10min", "3000+ 份"],
    ),
    FactRecord(
        id=2,
        category="metric",
        title="技术栈自评",
        org=None,
        facts=["Python", "PyTorch", "Linux", "Agent Application"],
    ),
    FactRecord(
        id=3,
        category="paper",
        title="STM-SHAP 论文",
        org="IEEE ISCTIS 2026",
        facts=["EI 一作论文 STM-SHAP", "NSE/RMSE 提升 13%"],
    ),
]


def test_extract_claims_skips_headers_and_labels():
    md = (
        "# 简历标题\n"
        "## 工作经历\n"
        "工作经历：\n"
        "- bullet one\n"
        "plain sentence with metric 56%\n"
        "short\n"
    )
    claims = extract_claims(md)
    # 标题 / 小节标签跳过；'short' 太短且无数字跳过
    assert claims == ["bullet one", "plain sentence with metric 56%"]


def test_anchored_claim_via_fact_phrase():
    md = "主导标书审核 Agent，覆盖率 56%→90%，单份处理 30min→10min"
    diag = ResumeEngine.diagnose(md, _FACTS)
    assert diag.total == 1
    assert diag.anchored_count == 1
    assert diag.unanchored_count == 0
    assert diag.claims[0].anchored is True
    assert diag.claims[0].anchors[0]["fact_id"] == 1


def test_unanchored_claim_flagged_red():
    md = "精通 CUDA 内核优化与算子开发"
    diag = ResumeEngine.diagnose(md, _FACTS)
    assert diag.total == 1
    assert diag.unanchored_count == 1
    assert diag.claims[0].anchored is False
    assert "未在事实锚点库" in diag.claims[0].reason


def test_skill_claim_anchored_by_keyword_fact():
    md = "熟练 Python、PyTorch，熟悉 Linux 训练环境"
    diag = ResumeEngine.diagnose(md, _FACTS)
    assert diag.anchored_count == 1
    assert diag.unanchored_count == 0


def test_mixed_diagnosis_counts_and_risk():
    md = (
        "- 主导标书审核 Agent，覆盖率 56%→90%\n"
        "- 熟练 Python 与 PyTorch\n"
        "- 精通 CUDA 内核优化（无锚点）\n"
    )
    diag = ResumeEngine.diagnose(md, _FACTS)
    assert diag.total == 3
    assert diag.anchored_count == 2
    assert diag.unanchored_count == 1
    assert diag.fabrication_risk == 33  # round(1/3*100)


def test_jd_alignment_supported_and_unsupported():
    md = "熟练 Python、PyTorch"
    diag = ResumeEngine.diagnose(md, _FACTS, required_skills=["PyTorch", "CUDA"])
    assert diag.jd_alignment is not None
    by_skill = {i.skill: i.supported for i in diag.jd_alignment}
    assert by_skill["PyTorch"] is True
    assert by_skill["CUDA"] is False


def test_paper_claim_anchored():
    md = "EI 一作论文 STM-SHAP（IEEE ISCTIS 2026），NSE/RMSE 提升 13%"
    diag = ResumeEngine.diagnose(md, _FACTS)
    assert diag.anchored_count == 1


def test_fact_create_rejects_bad_category():
    with pytest.raises(ValueError):
        ResumeFactCreate(category="bogus", title="x", facts=[])


def test_fact_create_accepts_valid_category():
    f = ResumeFactCreate(category="paper", title="X", facts=["y"])
    assert f.category == "paper"
