# backend/tests/test_v33_weighting.py
"""v3.3 推理优化支再加权钉（spec 2026-10-19-v33）：结构不变 + 口径进单一真源。"""

from pathlib import Path

from app.core.target_roles import TARGET_ROLES

_ROLES_SRC = Path(__file__).resolve().parents[1] / "app" / "core" / "target_roles.py"


def test_track_structure_unchanged():
    # spec 边界：不新增/不删赛道，priority 序不变
    assert [r.key for r in TARGET_ROLES] == ["llm", "vlm", "ai-algo", "embodied"]
    assert [r.priority for r in TARGET_ROLES] == ["主攻", "卡位", "保底", "暂缓"]
    frozen = {r.key: r.frozen for r in TARGET_ROLES}
    assert frozen == {"llm": False, "vlm": False, "ai-algo": False, "embodied": True}


def test_main_track_name_unchanged():
    llm = next(r for r in TARGET_ROLES if r.key == "llm")
    assert llm.name == "大模型后训练 / Post-Training 算法工程师"


def test_llm_note_carries_new_focus_and_ratio():
    llm = next(r for r in TARGET_ROLES if r.key == "llm")
    assert "推理优化支" in llm.note
    assert "40/40/20" in llm.note


def test_ai_algo_note_hooks_inference_branch():
    ai = next(r for r in TARGET_ROLES if r.key == "ai-algo")
    assert "承载推理优化支" in ai.note


def test_embodied_note_and_freeze_preserved():
    emb = next(r for r in TARGET_ROLES if r.key == "embodied")
    assert emb.frozen is True
    assert "长期观察" in emb.note


def test_module_carries_v33_ratio_comment():
    src = _ROLES_SRC.read_text(encoding="utf-8")
    assert "40/40/20（v3.3 再加权，2026-10-19）" in src
    for line in ("40% 推理优化支主攻", "40% Agent/RAG 护城河维持", "20% 观察带"):
        assert line in src, line


def test_llm_required_skills_still_include_moat():
    # 护城河技能必须仍在匹配要求里（40% 护城河兑现的机制前提）
    llm = next(r for r in TARGET_ROLES if r.key == "llm")
    assert "RAG" in llm.required_skills and "Agent Application" in llm.required_skills
