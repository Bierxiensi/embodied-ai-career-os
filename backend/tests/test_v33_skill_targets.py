# backend/tests/test_v33_skill_targets.py
"""v3.3 提级钉（spec §3.2）：五项 target≥4、护城河三项==5、50 项不增、level 不动。"""

from pathlib import Path

from app.core.skill_profile import SKILL_PROFILE

_SRC = Path(__file__).resolve().parents[1] / "app" / "core" / "skill_profile.py"

INFERENCE_FIVE = ["Attention", "KV Cache", "Quantization", "vLLM", "FlashAttention"]
MOAT_THREE = ["Agent Application", "RAG", "Python"]
# level 快照（level=实测，spec 禁止改动）
LEVEL_SNAPSHOT = {
    "Attention": 3, "KV Cache": 2, "Quantization": 2, "vLLM": 2, "FlashAttention": 1,
}


def _of(name: str):
    return next(s for s in SKILL_PROFILE if s.name == name)


def test_inference_five_targets_at_least_4():
    for name in INFERENCE_FIVE:
        s = _of(name)
        assert 4 <= s.target_level <= 5, f"{name}.target_level={s.target_level}"


def test_moat_three_targets_pinned_at_5():
    for name in MOAT_THREE:
        assert _of(name).target_level == 5, name


def test_levels_untouched():
    for name, level in LEVEL_SNAPSHOT.items():
        assert _of(name).level == level, f"{name}.level 被改动（spec：level=实测不改）"


def test_skill_count_stays_50():
    assert len(SKILL_PROFILE) == 50  # 不新增技能项


def test_source_has_v33_moat_comment():
    src = _SRC.read_text(encoding="utf-8")
    assert "# v3.3：护城河维持，不因推理支加权降权" in src
