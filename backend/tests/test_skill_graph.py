"""Phase 3 技能依赖图 / 六域聚合 测试。

覆盖三层：
 1. **数据完整性**（core/skill_profile.py + core/skill_graph.py）：
    六域是 50 项技能的一个划分；依赖边只引用真实技能名、无重边、无环。
    这几条是"图上写了错东西"的早期拦截 —— 依赖边按**名字**引用技能，
    拼错不会被数据库拦住，只能由测试守。
 2. **种子脚本**（scripts/seed_skill_graph.py）：幂等、不静默删边、写库前拦住坏数据。
 3. **API 契约**（/api/skills/domains、/api/skills/graph、/api/skills）：
    字段齐全、六轴守恒、依赖边的两端都在节点里。

为什么值得写这么多护栏：
    依赖图是"该先学哪个"的唯一依据。它一旦错了（少了边 / 有环 / 指向不存在
    的技能），平台会静默给出一条学不动的最优路径 —— 不报错、但结论是错的。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.skill_graph import (
    PREREQ_SATISFIED_LEVEL,
    SKILL_EDGES,
    dependents_of,
    edge_pairs,
    find_cycle,
    prerequisites_of,
    unknown_skills,
)
from app.core.skill_profile import (
    SKILL_DOMAINS,
    SKILL_PROFILE,
    domain_of,
    domains_are_all_populated,
    skills_in_domain,
    unmapped_skills,
)
from app.db.base import SessionLocal
from app.main import app
from app.models.skill_graph import SkillDependency

# 六域 key —— 硬编码在测试里是**故意**的：
# 这是产品契约（前端按 key 判断、文档按 key 引用），不是实现细节。
# 改 key 必须同时改这里，等于强制一次"回头确认前端也要改"。
EXPECTED_DOMAIN_KEYS = [
    "llm_foundation",
    "finetune_alignment",
    "inference_engineering",
    "multimodal",
    "engineering_delivery",
    "research_foundation",
]


def _load_seed_script():
    """按文件路径加载 seed_skill_graph.py（scripts/ 不是包，没有 __init__.py）。"""

    path = Path(__file__).resolve().parents[1] / "scripts" / "seed_skill_graph.py"
    spec = importlib.util.spec_from_file_location("seed_skill_graph_under_test", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ==============================================================================
# 1. 数据完整性
# ==============================================================================


def test_six_domains_are_exactly_the_declared_six():
    """六域 key 与顺序是产品契约，不是实现细节。"""

    assert [key for key, _ in SKILL_DOMAINS] == EXPECTED_DOMAIN_KEYS
    labels = [label for _, label in SKILL_DOMAINS]
    assert labels == ["LLM基础", "微调对齐", "推理工程", "多模态", "工程交付", "科研底座"]


def test_domains_partition_all_skills():
    """六域 + 无域（冻结/旁证）= 全部技能，且每项技能只属于一个域。

    这是"六域雷达"能当一张图看的前提：域之间不重叠、加起来是全量。
    少了任何一项都会让雷达少算一块（而不会报错）。
    """

    total = sum(len(skills_in_domain(k)) for k, _ in SKILL_DOMAINS)
    assert total + len(unmapped_skills()) == len(SKILL_PROFILE)

    seen: set[str] = set()
    for p in SKILL_PROFILE:
        if p.domain is None:
            continue
        assert p.domain in EXPECTED_DOMAIN_KEYS, f"{p.name} 的域 {p.domain} 未声明"
        assert p.name not in seen, f"{p.name} 被重复计入多个域"
        seen.add(p.name)
    assert len(seen) == total


def test_every_domain_has_skills():
    """空域会在雷达上画出一根退化到中心的轴，且均值变成 0/0。"""

    assert domains_are_all_populated() is True
    for key, _ in SKILL_DOMAINS:
        assert len(skills_in_domain(key)) > 0


def test_unmapped_skills_are_exactly_the_frozen_ones():
    """不在六域内的当前只有 7 项冻结 / 历史旁证技能。

    这条把"域归属"与"冻结"两个概念钉在一起：若将来解冻具身赛道，
    测试会红，逼着人显式决定"要不要给它一个域"。
    """

    names = sorted(p.name for p in unmapped_skills())
    assert names == sorted(
        [
            "ROS2",
            "Robot Learning",
            "Mujoco Simulation",
            "Isaac",
            "VLA",
            "Sim2Real",
            "MoveIt2",
        ]
    )
    # 全部为冻结（target == level）
    assert all(p.target_level <= p.level for p in unmapped_skills())


def test_domain_of_is_case_insensitive_and_unknown_returns_none():
    assert domain_of("transformer") == "llm_foundation"
    assert domain_of("Transformer") == "llm_foundation"
    assert domain_of("  SFT ") == "finetune_alignment"
    assert domain_of("ROS2") is None          # 在画像里，但无域
    assert domain_of("不存在的技能") is None
    assert domain_of("") is None


def test_edges_reference_only_real_skills():
    """依赖边按名字引用技能，拼错数据库拦不住，只能靠这条断言。"""

    assert unknown_skills() == []


def test_edges_are_unique():
    """重边会让"解锁了什么"重复计数，也让种子脚本的唯一约束报错。"""

    pairs = edge_pairs()
    assert len(pairs) == len(set(pairs))


def test_edges_have_no_cycle():
    """有环时"先补先修"会互相等待，且不会报错 —— 必须硬拦。"""

    cycle = find_cycle()
    assert cycle is None, f"依赖图存在环：{cycle}"


def test_core_chain_pytorch_transformer_attention():
    """产品文档点名的链条必须真的存在：PyTorch → Transformer → Attention。"""

    assert "PyTorch" in prerequisites_of("Transformer")
    assert "Transformer" in prerequisites_of("Attention")
    # 反向也要能查（"学了这个能解锁什么"）
    assert "Transformer" in dependents_of("PyTorch")


def test_prereq_satisfied_level_is_three():
    """先修判定阈值是 3（独立做过项目），不是 target_level —— 见 core/skill_graph.py。"""

    assert PREREQ_SATISFIED_LEVEL == 3


# ==============================================================================
# 2. 种子脚本
# ==============================================================================


def test_seed_edges_is_idempotent():
    """跑两次的结果必须一致（第二次 0 新增），否则脚本不能重跑。"""

    seed = _load_seed_script()
    db = SessionLocal()
    try:
        created, updated, stale = seed.upsert_edges(db)
        assert created == len(SKILL_EDGES)
        assert stale == []
        again_created, _, again_stale = seed.upsert_edges(db)
        assert again_created == 0
        assert again_stale == []
        assert db.query(SkillDependency).count() == len(SKILL_EDGES)
    finally:
        # 自清理：本模块写的行要删掉，避免影响同会话其他用例
        db.query(SkillDependency).delete()
        db.commit()
        db.close()


def test_seed_reports_stale_edges_without_deleting_them():
    """库里有、种子源里没有的边只报告不删除（删除必须显式 --prune）。"""

    seed = _load_seed_script()
    db = SessionLocal()
    try:
        db.add(SkillDependency(prerequisite="Python", dependent="手工加的假边"))
        db.commit()

        created, _, stale = seed.upsert_edges(db)
        assert created == len(SKILL_EDGES)
        assert [s.dependent for s in stale] == ["手工加的假边"]
        # 关键：没有 --prune 时**不能**删
        assert (
            db.query(SkillDependency)
            .filter(SkillDependency.dependent == "手工加的假边")
            .count()
            == 1
        )
    finally:
        db.query(SkillDependency).delete()
        db.commit()
        db.close()


def test_seed_preflight_rejects_unknown_skill(monkeypatch):
    """写库前的体检必须拦住"边指向不存在的技能"，否则坏数据会进库。

    ⚠️ 要 patch 的是 ``app.core.skill_graph.SKILL_EDGES``（校验函数的取值来源），
    不是种子脚本里的同名绑定 —— 后者只是 import 时的一份引用，
    改它不会影响 ``unknown_skills()`` 读到的内容（第一版就踩了这个）。
    """

    import app.core.skill_graph as skill_graph

    seed = _load_seed_script()
    monkeypatch.setattr(
        skill_graph, "SKILL_EDGES", (("不存在的技能", "Transformer", None),)
    )
    with pytest.raises(SystemExit) as exc:
        seed._preflight()
    assert "不存在的技能" in str(exc.value)


def test_seed_preflight_rejects_cycle(monkeypatch):
    """环同样必须在写库前被拦住。"""

    import app.core.skill_graph as skill_graph

    seed = _load_seed_script()
    monkeypatch.setattr(
        skill_graph,
        "SKILL_EDGES",
        (("Attention", "Transformer", None), ("Transformer", "Attention", None)),
    )
    with pytest.raises(SystemExit) as exc:
        seed._preflight()
    assert "环" in str(exc.value)


# ==============================================================================
# 3. API 契约
# ==============================================================================


def test_api_skill_domains_returns_six_axes():
    """/api/skills/domains 返回六根轴，且覆盖计数守恒。"""

    with TestClient(app) as client:
        body = client.get("/api/skills/domains").json()

    assert body["success"] is True
    data = body["data"]
    assert [d["key"] for d in data["domains"]] == EXPECTED_DOMAIN_KEYS
    assert data["prereq_satisfied_level"] == PREREQ_SATISFIED_LEVEL
    assert data["mapped_count"] + data["unmapped_count"] == len(SKILL_PROFILE)
    assert data["unmapped_count"] == len(unmapped_skills())

    for d in data["domains"]:
        assert d["skill_count"] > 0
        assert 0 <= d["current_avg"] <= 5
        assert 0 <= d["target_avg"] <= 5
        # 缺口均值必须等于两均值之差（防止有人把公式改了忘了同步文档）
        assert d["gap_avg"] == pytest.approx(
            round(d["target_avg"] - d["current_avg"], 1), abs=0.11
        )
        # 缺口技能按 gap 降序
        gaps = [g["gap"] for g in d["gap_skills"]]
        assert gaps == sorted(gaps, reverse=True)


def test_api_domain_gap_skills_carry_unmet_prerequisites():
    """域内待补技能必须带上先修状态 —— 这是"该先学哪个"的答案来源。"""

    with TestClient(app) as client:
        data = client.get("/api/skills/domains").json()["data"]

    llm = next(d for d in data["domains"] if d["key"] == "llm_foundation")
    rope = next(g for g in llm["gap_skills"] if g["name"] == "RoPE")
    assert rope["gap"] > 0
    prereqs = {p["name"]: p for p in rope["prerequisites"]}
    assert "Attention" in prereqs
    # 库内 Attention = 3 ≥ 阈值 3 → 已满足；这也顺带验证了等级来自**库**而不是画像
    assert prereqs["Attention"]["met"] is True
    assert prereqs["Attention"]["level"] is not None


def test_api_skill_graph_nodes_cover_every_edge_endpoint():
    """边引用的每个技能都必须在节点里，否则前端会画出指向虚空的边。"""

    with TestClient(app) as client:
        data = client.get("/api/skills/graph").json()["data"]

    node_names = {n["name"] for n in data["nodes"]}
    assert len(data["edges"]) == len(SKILL_EDGES)
    for e in data["edges"]:
        assert e["prerequisite"] in node_names, e
        assert e["dependent"] in node_names, e

    # 节点带域信息（六域模式要用）
    transformer = next(n for n in data["nodes"] if n["name"] == "Transformer")
    assert transformer["domain"] == "llm_foundation"
    assert transformer["domain_label"] == "LLM基础"
    assert transformer["level"] is not None


def test_api_skills_list_carries_domain_without_db_column():
    """/api/skills 的技能条目补上 domain，且不靠 skills 表的列。"""

    with TestClient(app) as client:
        items = client.get("/api/skills").json()["data"]

    by_name = {s["name"]: s for s in items}
    assert by_name["Transformer"]["domain"] == "llm_foundation"
    assert by_name["Transformer"]["domain_label"] == "LLM基础"
    # 冻结技能无域（None），一眼能看出"它不在六域雷达里"
    assert by_name["ROS2"]["domain"] is None
    assert by_name["ROS2"]["domain_label"] is None
    # 守恒：有域的技能数 == 六域成员总数
    mapped = sum(1 for s in items if s["domain"] is not None)
    assert mapped == sum(len(skills_in_domain(k)) for k, _ in SKILL_DOMAINS)
