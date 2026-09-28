"""单元网格：把 30 天脊梁 + 论文库确定性铺成 mastery_units 骨架。

FreeLingo 式「确定性网格」：网格本身不调 LLM、可预测、可校验；
内容（unit_items）打开才懒生成（generate.py）。sync_grid 幂等，可反复跑。
"""

from __future__ import annotations

import json

from app.core.plan_30d import PLAN_30D, SKILL_TO_DAY_SEQ
from app.models.mastery import MasteryUnit

_TITLE_KEYWORD_SKILLS = (
    ("DPO", "DPO"),
    ("Preference", "DPO"),
    ("LoRA", "LoRA"),
    ("QLoRA", "LoRA"),
    ("GRPO", "GRPO"),
    ("PPO", "RLHF"),
    ("RLHF", "RLHF"),
    ("InstructGPT", "RLHF"),
    ("Attention", "SFT"),
    ("Llama", "SFT"),
    ("Qwen", "VLM SFT"),
)


def _skills_for_title(title: str) -> list[str]:
    for kw, skill in _TITLE_KEYWORD_SKILLS:
        if kw.lower() in title.lower():
            return [skill]
    return []


def build_unit_specs(papers: list[tuple[int, str]]) -> list[dict]:
    """纯函数：papers 为 (id, title) 列表。返回 UnitSpec 列表。"""
    specs: list[dict] = []
    for d in PLAN_30D:
        skills = [s for s, seq in SKILL_TO_DAY_SEQ.items() if seq == d.seq]
        specs.append({
            "source_type": "lecture",
            "source_ref": f"plan_day:{d.seq}",
            "title": f"Day {d.seq} · {d.title}",
            "skill_ids": skills,
            "day_seq": d.seq,
        })
    for pid, title in papers:
        specs.append({
            "source_type": "paper",
            "source_ref": f"paper:{pid}",
            "title": title,
            "skill_ids": _skills_for_title(title),
            "day_seq": None,
        })
    return specs


def sync_grid(db) -> dict:
    """幂等铺格：缺失的单元补建（status=locked），已存在不动。"""
    from app.models.paper import Paper

    papers = [(p.id, p.title) for p in db.query(Paper).all()]
    specs = build_unit_specs(papers)
    existing = {
        (u.source_type, u.source_ref)
        for u in db.query(MasteryUnit).all()
    }
    created = 0
    for s in specs:
        key = (s["source_type"], s["source_ref"])
        if key in existing:
            continue
        db.add(MasteryUnit(
            source_type=s["source_type"],
            source_ref=s["source_ref"],
            title=s["title"],
            skill_ids=json.dumps(s["skill_ids"], ensure_ascii=False),
            day_seq=s["day_seq"],
            generation_mode="rule",
            content_hash=None,
            status="locked",
        ))
        created += 1
    db.commit()
    total = db.query(MasteryUnit).count()
    return {"created": created, "total": total}
