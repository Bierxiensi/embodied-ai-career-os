"""JD 匹配引擎纯规则单测（不依赖 DB / LLM）。

验证 v2.0 §22 的 5 维权重、等级阈值、差距计算与 JD 解析。
"""

from __future__ import annotations

import pytest

from app.agents.match.engine import JDParser, MatchEngine
from app.models.job_match import grade_of


def _full_levels(skills: list[str], level: int = 5) -> dict[str, int]:
    return {s.lower(): level for s in skills}


def test_grade_thresholds():
    assert grade_of(80) == "A"
    assert grade_of(65) == "B"
    assert grade_of(50) == "C"
    assert grade_of(49) == "D"
    assert grade_of(100) == "A"


def test_full_match_is_grade_a():
    skills = ["Transformer", "Attention", "SFT", "LoRA/QLoRA", "PyTorch", "Python", "Deep Learning"]
    res = MatchEngine.compute(
        required_skills=skills,
        track="llm",
        education="硕士",
        min_years=3,
        paper_required=False,
        skill_levels=_full_levels(skills, 5),
    )
    # 全维度满分 → 100 → A
    assert res.match_score == 100
    assert res.grade == "A"
    assert res.dimension_scores["tech_stack"] == 100
    assert res.dimension_scores["project"] == 100
    assert res.gaps == []


def test_partial_match_grade_b():
    # 技能中等（level 3），项目维度 hands_on 计入
    skills = ["Transformer", "Attention", "SFT", "LoRA/QLoRA", "PyTorch", "Python"]
    levels = _full_levels(skills, 3)
    res = MatchEngine.compute(
        required_skills=skills,
        track="llm",
        education="硕士",
        min_years=3,
        skill_levels=levels,
    )
    # tech = 60, project = 15+18*6=100(封顶), edu=100, research=100, industry=100
    # score = 0.4*60 + 0.25*100 + 0.15*100 + 0.1*100 + 0.1*100 = 24+25+15+10+10 = 84 → A
    assert res.grade == "A"
    # 技能等级 3 < 要求 4 → 产生差距
    assert len(res.gaps) == len(skills)
    assert all(g["gap"] == 1 for g in res.gaps)


def test_embodied_low_match_is_grade_d():
    skills = ["ROS2", "VLA", "Robot Learning", "Isaac"]
    # 这些技能在画像里等级低（ROS2=2, VLA=1, Robot Learning=2, Isaac=1）
    levels = {"ros2": 2, "vla": 1, "robot learning": 2, "isaac": 1}
    res = MatchEngine.compute(
        required_skills=skills,
        track="embodied",
        education="硕士",
        min_years=2,
        skill_levels=levels,
    )
    # tech 低 + industry 70（转型）→ 应落在 D
    assert res.grade == "D"
    assert res.dimension_scores["industry"] == 70


def test_missing_skill_counts_as_gap():
    skills = ["Transformer", "UnknownSkillXYZ"]
    levels = {"transformer": 5}
    res = MatchEngine.compute(
        required_skills=skills,
        track="llm",
        skill_levels=levels,
    )
    # UnknownSkillXYZ 不在画像 → level 0 → 差 4
    unknown = [g for g in res.gaps if g["skill"] == "UnknownSkillXYZ"]
    assert unknown and unknown[0]["gap"] == 4


def test_paper_required_with_user_paper():
    # 用户有 EI 一作论文（USER_HAS_PAPER=True），JD 要求论文 → research 满分
    skills = ["Python", "PyTorch"]
    levels = _full_levels(skills, 5)
    res = MatchEngine.compute(
        required_skills=skills,
        track="llm",
        paper_required=True,
        skill_levels=levels,
    )
    assert res.dimension_scores["research"] == 100


def test_paper_required_but_no_paper(monkeypatch):
    # 模拟"无论文"分支：要求论文且用户无 → research=30，拖低总分
    from app.agents.match import engine as engine_mod

    monkeypatch.setattr(engine_mod, "USER_HAS_PAPER", False)
    skills = ["Python", "PyTorch"]
    levels = _full_levels(skills, 5)
    res = MatchEngine.compute(
        required_skills=skills,
        track="llm",
        paper_required=True,
        skill_levels=levels,
    )
    assert res.dimension_scores["research"] == 30
    # 其余维度满分，仅科研 30 → 0.4*100+0.25*100+0.15*100+0.1*30+0.1*100 = 98 → 仍 A
    assert res.grade == "A"


def test_jd_parser_extracts_known_skills():
    text = (
        "负责大模型预训练与 SFT，使用 LoRA 微调，基于 Transformer/Attention 结构，"
        "精通 PyTorch 与 Python，做过 RAG 与 Agent 应用，了解 CLIP 与 VLM 多模态对齐。"
    )
    found = JDParser.parse_required_skills(text)
    for expected in ["Transformer", "Attention", "SFT", "LoRA/QLoRA", "PyTorch", "Python", "RAG", "Agent Application", "CLIP", "VLM", "Multimodal Alignment"]:
        assert expected in found


def test_jd_parser_empty_text():
    assert JDParser.parse_required_skills("") == []
    assert JDParser.parse_required_skills(None) == []


# ============================================================
# 别名表防误判（2026-09-11 修正回归）
# ============================================================
# 背景：别名表是「小写子串命中」，过宽的别名会把毫不相干的描述误判成技能。
# 实测某 JD（知识图谱 / 标准文本方向）因裸 "对齐" 别名，把"语义对齐 / 实体对齐"
# 误判成 Multimodal Alignment，凭空多出一条 gap=3 的缺口；裸 "zero" 则会把
# 英文 zero-shot 误判成 FSDP/ZeRO 并行。两处别名已收窄。

def test_jd_parser_ignores_semantic_alignment():
    """知识图谱语境的"对齐"不应被当成多模态对齐。"""
    found = JDParser.parse_required_skills(
        "实现实体对齐与关系推理，建立跨文档的统一语义对齐标准，构建知识图谱。"
    )
    assert "Multimodal Alignment" not in found


def test_jd_parser_ignores_bare_zero():
    """英文 zero-shot / zero-cost 不应被当成 ZeRO 并行。"""
    found = JDParser.parse_required_skills("支持 zero-shot 与少样本场景，zero cost 部署。")
    assert "FSDP/ZeRO" not in found


def test_jd_parser_still_captures_real_multimodal_alignment():
    """收窄后，真正的多模态对齐仍要能抽到（不能把功能修没了）。"""
    found = JDParser.parse_required_skills("做过多模态对齐与跨模态对齐，理解 vision-language 空间。")
    assert "Multimodal Alignment" in found


def test_jd_parser_captures_chinese_aliases():
    """中文写法此前整类漏抽：注意力机制 / 分布式训练。"""
    found = JDParser.parse_required_skills(
        "熟练掌握 Transformer、MoE 架构及注意力机制变种；熟悉分布式训练与模型压缩。"
    )
    assert "Attention" in found
    assert "Distributed Training" in found
    assert "Transformer" in found
    assert "MoE" in found
