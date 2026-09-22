"""技能依赖图种子脚本（幂等可重跑）。

把 app/core/skill_graph.py 的 SKILL_EDGES 投影到 skill_dependency 表：

    1. 插入缺失的边
    2. 更新 note 有变化的边
    3. **报告**库里多出来的边（不自动删 —— 见下）

为什么是"脚本 + Python 常量"而不是 CRUD 界面：
    与 target_roles.py / plan_30d.py / seed_phd.py 同一套约定 ——
    依赖边属于会反复调整的知识，但调整频率远低于查看频率。
    **改依赖 = 改 core/skill_graph.py + 重跑本脚本**，可 diff、可回滚。

为什么"库里多出来的边"只报告不删除：
    删除是不可逆动作。种子脚本静默删边会让人以为"我改错了"，实际可能是有意
    手工加的一条实验边。要删请显式加 ``--prune``，脚本会先打印待删清单。

运行：
    cd backend
    python scripts/seed_skill_graph.py              # 正常执行
    python scripts/seed_skill_graph.py --dry-run    # 只看会改什么，不写库
    python scripts/seed_skill_graph.py --prune      # 同时删除库里多出的边
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 允许从 backend 目录运行：将 backend 加入 sys.path 以便 import app
BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.skill_graph import SKILL_EDGES, find_cycle, unknown_skills  # noqa: E402
from app.core.skill_profile import SKILL_DOMAINS, domain_of  # noqa: E402
from app.db.base import SessionLocal, init_db  # noqa: E402
from app.models.skill import Skill  # noqa: E402
from app.models.skill_graph import SkillDependency  # noqa: E402


def _preflight() -> None:
    """写库前先拦下"边指向不存在的技能"和"有环"两种硬错误。"""

    bad = unknown_skills()
    if bad:
        raise SystemExit(
            "SKILL_EDGES 引用了 SKILL_PROFILE 之外的技能名："
            + "、".join(bad)
            + "。请修正 core/skill_graph.py 后重跑。"
        )
    cycle = find_cycle()
    if cycle:
        raise SystemExit(
            "SKILL_EDGES 存在环（先修关系互相等待，学习顺序无法求解）："
            + " -> ".join(cycle)
        )


def upsert_edges(db, dry_run: bool = False) -> tuple[int, int, list[SkillDependency]]:
    """同步 SKILL_EDGES 到库。返回 (新增, 更新 note, 库中冗余的行)。"""

    existing = {
        (row.prerequisite, row.dependent): row
        for row in db.query(SkillDependency).all()
    }

    created = 0
    updated = 0
    for prereq, dep, note in SKILL_EDGES:
        row = existing.pop((prereq, dep), None)
        if row is None:
            created += 1
            if not dry_run:
                db.add(SkillDependency(prerequisite=prereq, dependent=dep, note=note))
            continue
        if (row.note or None) != (note or None):
            updated += 1
            if not dry_run:
                row.note = note

    # existing 里剩下的就是"库里有、SKILL_EDGES 里没有"的边
    stale = list(existing.values())

    if not dry_run:
        db.commit()

    return created, updated, stale


def main() -> None:
    parser = argparse.ArgumentParser(description="技能依赖图种子脚本（幂等）")
    parser.add_argument(
        "--dry-run", action="store_true", help="只报告将要发生的变更，不写库"
    )
    parser.add_argument(
        "--prune", action="store_true", help="删除库中不在 SKILL_EDGES 里的边"
    )
    args = parser.parse_args()

    _preflight()

    init_db()
    db = SessionLocal()
    try:
        # 先把不在 skills 表里的技能名点出来（不是错误，但要让人知道）
        known_skills = {s.name for s in db.query(Skill).all()}
        missing_in_db = sorted(
            {n for p, d, _ in SKILL_EDGES for n in (p, d)} - known_skills
        )

        created, updated, stale = upsert_edges(db, args.dry_run)

        prefix = "[dry-run] " if args.dry_run else ""
        print(f"{prefix}skill_dependency：新增 {created} 条，更新 note {updated} 条")

        if stale:
            print(f"{prefix}库中另有 {len(stale)} 条不在 SKILL_EDGES 里的边：")
            for row in stale:
                print(f"    - {row.prerequisite} -> {row.dependent}")
            if args.prune and not dry_run:
                for row in stale:
                    db.delete(row)
                db.commit()
                print(f"    已删除 {len(stale)} 条（--prune）")
            elif not dry_run:
                print("    （未删除。要删除请显式加 --prune）")

        if missing_in_db:
            print(f"\n⚠️ 以下技能出现在依赖边里，但 skills 表里没有：{missing_in_db}")
            print("   （依赖图仍可用，但前端标注会找不到等级）")

        if args.dry_run:
            print("\n（dry-run 未写库。去掉 --dry-run 以实际执行）")
            return


        total = db.query(SkillDependency).count()
        print(f"\n当前 skill_dependency 共 {total} 条边")

        # 按域统计边的分布：确认六域都真的连上了（避免"整张图只覆盖 LLM 基础"）
        by_domain: dict[str, int] = {}
        for prereq, dep, _ in SKILL_EDGES:
            for name in (prereq, dep):
                key = domain_of(name) or "(no-domain)"
                by_domain[key] = by_domain.get(key, 0) + 1
        labels = {key: label for key, label in SKILL_DOMAINS}
        print(
            "域分布（端点计数）："
            + "，".join(
                f"{labels.get(k, k)} {v}"
                for k, v in sorted(by_domain.items(), key=lambda kv: -kv[1])
            )
        )
        print("\n下一步：curl http://127.0.0.1:8000/api/skills/graph")
    finally:
        db.close()


if __name__ == "__main__":
    main()
