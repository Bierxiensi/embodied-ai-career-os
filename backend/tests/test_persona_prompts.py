"""过时人设守卫：具身旧口径不得再出现在 prompt 里（2026-09-24）。"""

from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

FORBIDDEN = ["具身智能学习导师", "机器人行业猎头", "Robot AI Engineer / VLA Engineer", "薪资 30k+"]

FILES = [
    BACKEND / "app/agents/planner/generators/llm_generator.py",
    BACKEND / "app/agents/reviewer/nodes.py",
    BACKEND / "app/agents/career/nodes.py",
]


def test_no_stale_persona_in_prompts():
    for f in FILES:
        src = f.read_text(encoding="utf-8")
        for bad in FORBIDDEN:
            assert bad not in src, f"{f.name} 仍含过时人设：{bad}"


def test_planner_persona_is_post_training():
    from app.agents.planner.generators.llm_generator import _build_system_prompt

    prompt = _build_system_prompt()
    assert "Post-Training" in prompt
    assert "SFT" in prompt and "DPO" in prompt
