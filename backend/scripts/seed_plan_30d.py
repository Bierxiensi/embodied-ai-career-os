"""30 天课程脊梁种子脚本（幂等可重跑）。

把 app/core/plan_30d.py 的课程内容投影到数据库：

    1. upsert 30 条 plan_days（按 seq 匹配：存在则更新内容，不存在则插入）
    2. 回填已有任务的 plan_day_id（按 skill_name → 课程日映射，只填 NULL 的行）

为什么是"脚本 + Python 文件"而不是 CRUD 界面（见 docs/platform-direction-30day.md §八）：
    计划会变，但变更频率远低于查看频率。给 30 条固定记录做一套管理界面，
    是典型的"建设平台吞掉学习时间"。**改计划 = 改 plan_30d.py + 重跑本脚本**，
    可版本控制、可 diff、可回滚 —— 与 target_roles.py / seed_job_hunt.py 同一套约定。

幂等性：
    - plan_days 按 seq 匹配后更新，重复执行结果一致，不会产生重复行
    - 任务回填只处理 plan_day_id IS NULL 的行，不覆盖手工指定
    - 具身技能（ROS2/Isaac/VLA/...）与 "Job Hunt" 故意不映射，保持 NULL

运行：
    cd backend
    python scripts/seed_plan_30d.py              # 正常执行
    python scripts/seed_plan_30d.py --dry-run    # 只看会改什么，不写库
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 允许从 backend 目录运行：将 backend 加入 sys.path 以便 import app
BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.plan_30d import PLAN_30D, SKILL_TO_DAY_SEQ
from app.db.base import SessionLocal, init_db
from app.models.plan_day import PlanDay
from app.models.task import Task


def upsert_plan_days(db, dry_run: bool = False) -> tuple[int, int]:
    """把 PLAN_30D 写入 plan_days。返回 (新增数, 更新数)。"""

    existing = {d.seq: d for d in db.query(PlanDay).all()}
    created = 0
    updated = 0

    for seed in PLAN_30D:
        row = existing.get(seed.seq)
        payload = {
            "phase": seed.phase,
            "phase_name": seed.phase_name,
            "title": seed.title,
            "theme": seed.theme,
            "objectives": list(seed.objectives),
            "acceptance": list(seed.acceptance),
            "interview_topics": list(seed.interview_topics),
            "resources": list(seed.resources),
            "est_minutes": seed.est_minutes,
            "track_key": seed.track_key,
        }

        if row is None:
            if not dry_run:
                db.add(PlanDay(seq=seed.seq, **payload))
            created += 1
            continue

        changed = any(getattr(row, k) != v for k, v in payload.items())
        if changed:
            if not dry_run:
                for k, v in payload.items():
                    setattr(row, k, v)
            updated += 1

    if not dry_run:
        db.commit()
    return created, updated


def bind_tasks(db, dry_run: bool = False, rebind: bool = False) -> tuple[int, int]:
    """把已有任务按 skill_name 回填到课程日。返回 (已绑定数, 无映射跳过数)。

    默认只处理 ``plan_day_id IS NULL`` 的任务，不覆盖已有指定。

    ``rebind=True``：先清空全部 plan_day_id 再重绑。用于**修正错误的回填** ——
    映射规则收紧后（例如把过于通用的 "Python" 从 SKILL_TO_DAY_SEQ 移除），
    旧的错绑不会自动消失，必须显式重置一次。
    plan_day_id 是派生元数据（不是用户内容），重置安全。
    """

    # seq -> plan_day.id
    seq_to_id = {d.seq: d.id for d in db.query(PlanDay).all()}
    if not seq_to_id:
        return 0, 0

    if rebind:
        stale = (
            db.query(Task)
            .filter(Task.plan_day_id.is_not(None))
            .filter(Task.source != "test")
            .all()
        )
        if not dry_run:
            for task in stale:
                task.plan_day_id = None
            db.commit()

    candidates = (
        db.query(Task)
        .filter(Task.plan_day_id.is_(None))
        .filter(Task.source != "test")
        .all()
    )

    bound = 0
    skipped = 0
    for task in candidates:
        skill = (task.skill_name or "").strip()
        seq = SKILL_TO_DAY_SEQ.get(skill)
        if seq is None or seq not in seq_to_id:
            skipped += 1
            continue
        if not dry_run:
            task.plan_day_id = seq_to_id[seq]
        bound += 1

    if not dry_run:
        db.commit()
    return bound, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="30 天课程脊梁种子脚本（幂等）")
    parser.add_argument(
        "--dry-run", action="store_true", help="只报告将要发生的变更，不写库"
    )
    parser.add_argument(
        "--rebind",
        action="store_true",
        help="先清空全部 plan_day_id 再重新回填（用于修正收紧映射规则后的错绑）",
    )
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        created, updated = upsert_plan_days(db, args.dry_run)
        bound, skipped = bind_tasks(db, args.dry_run, args.rebind)

        prefix = "[dry-run] " if args.dry_run else ""
        print(f"{prefix}课程脊梁 plan_days：新增 {created} 天，更新 {updated} 天")
        print(f"{prefix}任务回填 plan_day_id：绑定 {bound} 条，无映射跳过 {skipped} 条")

        if args.dry_run:
            print("\n（dry-run 未写库。去掉 --dry-run 以实际执行）")
            return

        total = db.query(PlanDay).count()
        print(f"\n当前 plan_days 共 {total} 天")
        by_track: dict[str, int] = {}
        for d in db.query(PlanDay).all():
            by_track[d.track_key] = by_track.get(d.track_key, 0) + 1
        print("赛道分布：" + "，".join(f"{k} {v} 天" for k, v in sorted(by_track.items())))

        print("\n下一步：curl http://127.0.0.1:8000/api/plan/today")
    finally:
        db.close()


if __name__ == "__main__":
    main()
