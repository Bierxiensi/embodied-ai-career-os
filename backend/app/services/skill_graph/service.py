"""技能结构服务（Phase 3）：六域聚合 + 依赖图装配。

模块划分：
- ``core/skill_profile.py``  技能自评与**六域归属**的单一真源（纯数据）
- ``core/skill_graph.py``    依赖边（先修 -> 后继）的单一真源（纯数据）
- 本模块                    把上面两份真源与库里的技能**等级**拼成可下发结构

边界（docs/CODEX_MODULAR_DESIGN_STANDARD.md §1）：
    本模块不持有技能清单、不持有依赖边，也不写库。
    它只做"读两份真源 + 读 skills 表等级 → 组装"。
    因此改域归属改 skill_profile、改依赖改 skill_graph，两处都不用碰这里。

为什么需要"先修未满足"这层计算：
    只有缺口排序（gap 降序）时会推出"RoPE 缺 4 分，先补它"这类结论；
    但 RoPE 的先修是 Attention —— 若 Attention 还没到 PREREQ_SATISFIED_LEVEL，
    直接学 RoPE 是空转。本模块把"先修是否满足"算出来挂在每项缺口技能上，
    让前端能显示"先修 Attention 未达标，先补它"。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.skill_graph import (
    PREREQ_SATISFIED_LEVEL,
    SKILL_EDGES,
    prerequisites_of,
)
from app.core.skill_profile import (
    DOMAIN_LABELS,
    SKILL_DOMAINS,
    SKILL_PROFILE,
    domain_of,
    skills_in_domain,
    unmapped_skills,
)
from app.models.skill import Skill


def _levels_by_name(db: Session) -> dict[str, Skill]:
    """技能名（小写）-> Skill 行。"""

    return {s.name.lower(): s for s in db.query(Skill).all()}


def prereq_status(skill_name: str, levels: dict[str, Skill]) -> list[dict]:
    """列出某项技能的全部先修及其达成状态。

    ``met`` 的判定用 ``PREREQ_SATISFIED_LEVEL``（=3，独立做过项目），
    而不是"达到 target_level" —— 理由见 core/skill_graph.py 的说明。
    先修名在库里查不到时 level=None 且 met=False：**缺项不等于满足**，
    这是本文件唯一一个"宁可判不满足"的地方。
    """

    out: list[dict] = []
    for name in prerequisites_of(skill_name):
        row = levels.get(name.lower())
        level = row.level if row is not None else None
        note = next((n for p, d, n in SKILL_EDGES if p == name and d == skill_name), None)
        out.append(
            {
                "name": name,
                "level": level,
                "met": level is not None and level >= PREREQ_SATISFIED_LEVEL,
                "note": note,
            }
        )
    return out


def build_domain_overview(db: Session) -> dict:
    """六域聚合（R2 雷达的数据源）。

    ``current_avg`` / ``target_avg`` 用**域内均值**：均值同时回答两个问题 ——
    "这一层投入够不够"（当前高度）与"离目标多远"（两圈之差）。
    域内技能取自 ``skills_in_domain``（= SKILL_PROFILE 的 domain 字段），
    等级则**优先取库里的行**（用户的真实进度在库里），库里缺该项才回落到画像。

    为什么回落：库与画像应当一致，但用户手工删过技能行时不能整条轴消失 ——
    少一根轴会让雷达变成五边形且没有任何报错。
    """

    levels = _levels_by_name(db)
    domains: list[dict] = []

    for key, label in SKILL_DOMAINS:
        profiles = skills_in_domain(key)
        count = len(profiles)
        if count == 0:  # 由 domains_are_all_populated() 护栏拦截，此处仅防御
            continue

        cur_sum = 0
        tgt_sum = 0
        gap_skills: list[dict] = []
        for p in profiles:
            row = levels.get(p.name.lower())
            level = row.level if row is not None else p.level
            target = row.target_level if row is not None else p.target_level
            cur_sum += level
            tgt_sum += target
            gap = max(target - level, 0)
            if gap > 0:
                gap_skills.append(
                    {
                        "name": p.name,
                        "level": level,
                        "target_level": target,
                        "gap": gap,
                        "prerequisites": prereq_status(p.name, levels),
                    }
                )

        gap_skills.sort(key=lambda g: (-g["gap"], g["name"]))
        current_avg = round(cur_sum / count, 1)
        target_avg = round(tgt_sum / count, 1)
        domains.append(
            {
                "key": key,
                "label": label,
                "skill_count": count,
                "current_avg": current_avg,
                "target_avg": target_avg,
                "gap_avg": round(target_avg - current_avg, 1),
                "gap_skills": gap_skills,
            }
        )

    unmapped = unmapped_skills()
    return {
        "domains": domains,
        "mapped_count": sum(d["skill_count"] for d in domains),
        "unmapped_count": len(unmapped),
        "unmapped_names": [p.name for p in unmapped],
        "prereq_satisfied_level": PREREQ_SATISFIED_LEVEL,
    }


def build_graph(db: Session) -> dict:
    """依赖图（节点 + 边）。

    节点取 **SKILL_PROFILE ∩ 库**：画像给出域与目标等级，库给出当前等级。
    库里没有的技能行仍然出节点（level=None），因为依赖边引用它，
    少一个节点会让前端画出指向虚空的边。
    """

    levels = _levels_by_name(db)

    nodes: list[dict] = []
    seen: set[str] = set()
    for p in SKILL_PROFILE:
        row = levels.get(p.name.lower())
        seen.add(p.name.lower())
        key = p.domain
        nodes.append(
            {
                "name": p.name,
                "domain": key,
                "domain_label": DOMAIN_LABELS.get(key) if key else None,
                "level": row.level if row is not None else p.level,
                "target_level": row.target_level if row is not None else p.target_level,
                "frozen": (row.target_level if row is not None else p.target_level)
                <= (row.level if row is not None else p.level),
            }
        )

    # 库里有、画像里没有的技能：只出一个"无域"节点，不猜它属于哪一域
    for name, row in levels.items():
        if name in seen:
            continue
        nodes.append(
            {
                "name": row.name,
                "domain": domain_of(row.name),
                "domain_label": DOMAIN_LABELS.get(domain_of(row.name) or ""),
                "level": row.level,
                "target_level": row.target_level,
                "frozen": row.target_level <= row.level,
            }
        )

    return {
        "nodes": nodes,
        "edges": [
            {"prerequisite": p, "dependent": d, "note": n}
            for p, d, n in SKILL_EDGES
        ],
        "prereq_satisfied_level": PREREQ_SATISFIED_LEVEL,
    }
