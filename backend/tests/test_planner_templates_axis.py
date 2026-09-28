"""Rule 模板必须在 Post-Training 主轴上（2026-09-24：rule 是默认生成器，模板不能出冻结赛道任务）。"""

import json
from pathlib import Path

from app.agents.planner.generators.llm_generator import _validate_and_fill
from app.agents.planner.templates import TEMPLATES

BACKEND = Path(__file__).resolve().parents[1]

FORBIDDEN = ["SO101", "ROS2", "Isaac", "VLA", "Robot Learning"]


def test_no_frozen_track_templates():
    for skill, items in TEMPLATES.items():
        for bad in FORBIDDEN:
            assert bad not in skill, f"模板键含冻结赛道：{skill}"
            for t in items:
                assert bad not in t["title"], f"{skill} 模板标题含冻结赛道：{t['title']}"
                assert bad not in t["objective"], f"{skill} 模板目标含冻结赛道：{t['objective']}"


def test_core_axis_covered():
    # 学→做→考→证的三个作品集模块必须各有模板
    for key_part in ("SFT", "LoRA", "DPO"):
        assert any(key_part in k for k in TEMPLATES), f"缺少 {key_part} 模板"


def test_template_shape():
    for skill, items in TEMPLATES.items():
        assert items, skill
        for t in items:
            assert t["acceptance"] and t["resources"]
            assert 15 <= t["base_minutes"] <= 180
            assert t["difficulty"] in ("beginner", "intermediate", "advanced")


def test_llm_generator_source_on_axis():
    # EXTRA 守卫：prompt 生成器源码不得残留旧岗位/冻结赛道字面量。
    # 注意：system prompt 规则 7 合法含 "Robot AI/VLA/SO101"（禁令本身），
    # 因此这里不禁裸串 VLA / SO101。
    src = (
        BACKEND / "app/agents/planner/generators/llm_generator.py"
    ).read_text(encoding="utf-8")
    assert "Robot AI Engineer" not in src, "llm_generator 仍含旧目标岗位字面量"
    assert "ROS2" not in src and "Isaac" not in src, "llm_generator 仍含冻结赛道字面量"


def test_llm_fallback_fill_never_emits_frozen_track():
    # 行为钉（比上面的源码钉更强）：LLM 返回空 JSON、selected_skill 也空时，
    # _validate_and_fill 的兜底填充不得回吐冻结赛道字符串。
    # 注意钉的是**输出**而非模块源码 —— system prompt 规则 7 合法含 "Robot AI/VLA/SO101"。
    out = _validate_and_fill({}, {"selected_skill": "", "available_minutes": 45})
    rendered = json.dumps(out, ensure_ascii=False)
    assert "Robot AI" not in rendered, f"兜底填充仍含冻结赛道：{rendered}"
    assert out["skill"] == "Post-Training"
    assert "Post-Training" in out["objective"]
    assert any("Post-Training" in a for a in out["acceptance"])
