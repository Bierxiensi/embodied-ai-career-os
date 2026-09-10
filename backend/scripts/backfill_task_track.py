"""任务赛道回填脚本（默认 dry-run）。

================================================================================
背景（2026-09-10 用户反馈「任务没有跟随不同的角色看板走」）
================================================================================
tasks 表新增了 ``track_key`` 列（见 migrations/0008），但**存量任务**该列为
NULL —— 看板按视角过滤时会一条都看不到。本脚本按技能的赛道归属把它们补上。

归类规则（**先匹配者胜**，按 TARGET_ROLES 的声明顺序：
主攻 llm → 卡位 vlm → 保底 ai-algo → 冻结 embodied）：

    1. task.skill_name 命中某条赛道的 required_skills → 该赛道
    2. 未命中（含 skill_name 为 NULL 的补强任务、Job Hunt 这类运营任务）
       → 归入「主攻」赛道

第 2 条是有意的保守选择：这些任务都是冲刺期产物（面试弱项补强、海投节奏），
归到主攻赛道符合它们被创建时的语境。归属是**可逆**的（`--reset` 清空，
或直接改库），不会丢数据。

注意 PyTorch / Python / Deep Learning 同时出现在多条赛道里，规则 1 的
"声明顺序优先" 会把它们判给 llm（主攻）—— 这是刻意的：冲刺期它们服务于
主攻岗位，且避免同一条任务在两个视角重复出现。

================================================================================
用法
================================================================================
    cd backend

    # 1) 默认 dry-run：只打印归类结果，不写库
    python scripts/backfill_task_track.py

    # 2) 执行归类（写入前自动备份 app.db）
    python scripts/backfill_task_track.py --apply

    # 3) 撤销：把 track_key 全部清回 NULL（同样需 --apply，同样先备份）
    python scripts/backfill_task_track.py --reset --apply

================================================================================
安全约束
================================================================================
- 默认 dry-run；写入需要 `--apply`
- 写入前**自动备份** `data/app.db` → `.workbuddy/backup/app.db.track_<ts>`
- 只改 `tasks.track_key` 一列，不碰 status / title / acceptance 等任何业务字段
- 分批执行（每批 ≤ BATCH_SIZE），每批后核对
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.target_roles import TARGET_ROLES  # noqa: E402
from app.db.base import SessionLocal  # noqa: E402
from app.models.task import Task  # noqa: E402

BATCH_SIZE = 10


def _main_track_key() -> str | None:
    """主攻赛道 key —— 兜底归类目标。"""
    hit = next((r for r in TARGET_ROLES if r.priority == "主攻"), None)
    if hit is None:
        hit = TARGET_ROLES[0] if TARGET_ROLES else None
    return hit.key if hit else None


def _build_skill_index() -> dict[str, str]:
    """技能名（小写）→ 赛道 key。按 TARGET_ROLES 声明顺序，先匹配者胜。"""
    index: dict[str, str] = {}
    for role in TARGET_ROLES:
        for name in role.required_skills:
            key = name.strip().lower()
            index.setdefault(key, role.key)
    return index


def classify(skill_name: str | None, index: dict[str, str], fallback: str | None) -> str | None:
    """给一个技能名判定赛道。未命中回退主攻赛道。"""
    if skill_name:
        hit = index.get(skill_name.strip().lower())
        if hit:
            return hit
    return fallback


def backup_db() -> Path | None:
    """写入前备份 SQLite 文件。"""
    import app.core.config as cfg

    url = cfg.settings.database_url
    if not url.startswith("sqlite"):
        print(f"  ! 非 SQLite（{url}），跳过文件备份 —— 请自行确保有数据库级备份")
        return None

    raw = url.split("sqlite:///", 1)[-1]
    src = Path(raw)
    if not src.is_absolute():
        src = BACKEND / src
    if not src.exists():
        print(f"  ! 未找到数据库文件 {src}，跳过备份")
        return None

    backup_dir = BACKEND.parent / ".workbuddy" / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    dst = backup_dir / f"app.db.track_{ts}"
    shutil.copy2(src, dst)
    print(f"  OK 已备份: {dst}")
    return dst


def main() -> int:
    parser = argparse.ArgumentParser(
        description="按赛道归属回填 tasks.track_key（默认 dry-run）"
    )
    parser.add_argument("--apply", action="store_true", help="真正写入（默认只打印）")
    parser.add_argument(
        "--reset", action="store_true", help="把 track_key 全部清回 NULL（撤销归类）"
    )
    args = parser.parse_args()

    index = _build_skill_index()
    fallback = _main_track_key()

    db = SessionLocal()
    try:
        tasks = db.query(Task).order_by(Task.id).all()
        if not tasks:
            print("（没有任务，无需处理）")
            return 0

        track_names = {r.key: r.name for r in TARGET_ROLES}

        print("=" * 72)
        print(" 任务赛道归类" + ("（撤销模式：清回 NULL）" if args.reset else ""))
        print("=" * 72)
        print(f" 兜底赛道（未匹配技能的归属）: {fallback} · {track_names.get(fallback, '—')}")
        print(f" 任务总数: {len(tasks)}")
        print()

        # 计算目标值
        plan: list[tuple[Task, str | None, str]] = []  # (task, target, 说明)
        for t in tasks:
            if args.reset:
                plan.append((t, None, "撤销 → NULL"))
                continue
            target = classify(t.skill_name, index, fallback)
            if t.skill_name and t.skill_name.strip().lower() in index:
                why = f"技能 {t.skill_name} 命中赛道配置"
            else:
                why = f"未匹配（skill={t.skill_name or 'NULL'}）→ 归主攻"
            plan.append((t, target, why))

        # 预览分组
        by_track: dict[str, list[tuple[Task, str]]] = {}
        for t, target, why in plan:
            by_track.setdefault(target or "(NULL)", []).append((t, why))

        for key, items in by_track.items():
            label = track_names.get(key, key)
            print(f"【{key} · {label}】{len(items)} 条")
            for t, why in items:
                will_change = (t.track_key or None) != (
                    None if key == "(NULL)" else key
                )
                marker = "* " if will_change else "  "
                print(
                    f" {marker}#{t.id:<4} {str(t.skill_name or '—'):<18} "
                    f"{t.title[:34]:<36} | {why}"
                )
            print()

        changed = [
            (t, target)
            for t, target, _ in plan
            if (t.track_key or None) != (target if target is not None else None)
        ]

        print("-" * 72)
        print(f" 需要写入的任务: {len(changed)} / {len(tasks)}（`*` 标记为将有变更的行）")

        if not changed:
            print("\n 已是最新，无需写入。")
            return 0

        if not args.apply:
            print("\n [dry-run] 未写入任何内容。确认无误后加 --apply 执行。")
            return 0

        print()
        backup_db()

        for i in range(0, len(changed), BATCH_SIZE):
            for t, target in changed[i : i + BATCH_SIZE]:
                t.track_key = target
            db.commit()
            done = min(i + BATCH_SIZE, len(changed))
            print(f"    写入: {done}/{len(changed)}")

        # 复核
        print()
        print(" 复核（各赛道实际条数）：")
        for role in TARGET_ROLES:
            n = db.query(Task).filter(Task.track_key == role.key).count()
            print(f"   {role.key:<10} {role.name:<26} {n} 条")
        n_null = db.query(Task).filter(Task.track_key.is_(None)).count()
        print(f"   {'(NULL)':<10} {'未归类':<26} {n_null} 条")
        print("\n 完成。")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
