"""测试残留数据清理脚本（默认 dry-run，破坏性操作需显式开启）。

================================================================================
背景（2026-09-10 系统审计）
================================================================================
`backend/tests/` 长期缺少 conftest.py，多数测试直连开发库 `data/app.db`；
`test_e2e_learning_loop.py` 还硬编码过 Linux 容器路径。结果每跑一次 pytest 就往
真实库里灌一批测试数据，累积成：

    projects   214 行（真实只有 2 行）
    milestones 178 行（88 行 in_progress）
    tasks      292 行（单任务最多重复 29 次）
    agent_runs 393 行（全部为测试产生）

pytest 隔离已在 `tests/conftest.py` 修好（新建数据不再进开发库），
但**存量**需要本脚本清理一次。

================================================================================
用法
================================================================================
    cd backend

    # 1) 默认 dry-run：只报告，不写任何东西
    python scripts/purge_test_data.py

    # 2) 执行「标记」—— 把识别出的测试残留 source 改为 'test'（可逆）
    #    API 层默认已过滤 source='test'，所以跑完这一步前端立刻干净
    python scripts/purge_test_data.py --apply

    # 3) 标记 + 物理删除（不可逆；执行前自动备份 app.db）
    python scripts/purge_test_data.py --apply --purge

    # 4) 额外清理重复任务（同 title+skill+status 只留最早一条）
    python scripts/purge_test_data.py --apply --purge --dedupe

================================================================================
安全约束
================================================================================
- 默认 dry-run；任何写入都需要 `--apply`
- 写入前**自动备份** `data/app.db` → `.workbuddy/backup/app.db.purge_<ts>`
- **白名单保护**：真实业务表一律不动
  （job_applications / resume_facts / interview_logs / career_goal /
    interview_questions / report_logs / skills / papers*）
- `PROTECTED_PROJECTS` 里的项目名永不判定为测试数据
- 分批执行（每批 ≤ BATCH_SIZE），每批后核对
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.db.base import SessionLocal  # noqa: E402
from app.models.agent_run import AgentRun  # noqa: E402
from app.models.milestone import Milestone  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.task import Task  # noqa: E402

# ===== 配置 =====

BATCH_SIZE = 10

# agent_runs 的测试残留签名。
#
# 依据（2026-09-10 审计实测）：dev 库 393 条 agent_runs 全部集中在当天，
# 且其 input_context 里的 target_role 一律是 "Robot AI Engineer" ——
# 这是 app/api/planner.py 历史上**硬编码的默认值**，已被改为读 TARGET_ROLES
# 的「主攻」赛道（现在默认是 "LLM / 大模型算法工程师"）。
# 此外测试套件直接以该字面量调 API，才会批量产生这批记录。
#
# 因此「input_context.target_role == 该废弃字面量」= 测试残留的可靠签名。
# 真实用户运行不会再带这个值（默认值已换、前端也不再传它）。
LEGACY_TEST_TARGET_ROLE = "Robot AI Engineer"

# 永不判定为测试数据的项目名（真实项目白名单）
PROTECTED_PROJECTS: set[str] = {
    "SO101 Embodied AI System",
    "求职冲刺 · 2026 Q4",
}

# 测试项目名识别规则（**显式列举 + 通用关键词**，全部可 review）
# 显式列举覆盖审计实测到的全部残留名，避免通用规则误伤。
TEST_PROJECT_EXACT: set[str] = {
    "m test project",
    "scaffold test",
    "test project",
    "planner test",
    "planner e2e",
    "idempotent test",
    "gen test",
    "filter test",
    "e2e so101",
    "readme test",
    "patch test",
    "detail test",
    "so101 embodied ai",
    "p",  # 单字符项目名，无意义
}

# 通用关键词（兜底：将来新测试留下的同类数据也能被识别）
TEST_PROJECT_PATTERN = re.compile(
    r"(\btest\b|\be2e\b|\bscaffold\b|\bidempotent\b|\bfixture\b|\bdummy\b|\bmock\b)",
    re.IGNORECASE,
)

# 测试任务标题识别规则
TEST_TASK_PATTERNS = [
    re.compile(r"^完成测试\s*-\s*第\d步$"),
    re.compile(r"^old task$", re.IGNORECASE),
    re.compile(r"^test task$", re.IGNORECASE),
    re.compile(r"^(test|测试)\s*\d*$", re.IGNORECASE),
]

# 白名单：这些表绝不触碰（真实业务数据）
PROTECTED_TABLES = [
    "job_applications",
    "resume_facts",
    "interview_logs",
    "career_goal",
    "interview_questions",
    "report_logs",
    "skills",
    "job_postings",
    "job_matches",
]


def _is_test_project_name(name: str) -> bool:
    n = (name or "").strip()
    if n in PROTECTED_PROJECTS:
        return False
    if n.lower() in TEST_PROJECT_EXACT:
        return True
    return bool(TEST_PROJECT_PATTERN.search(n))


def _is_test_task_title(title: str) -> bool:
    t = (title or "").strip()
    return any(p.search(t) for p in TEST_TASK_PATTERNS)


def _is_test_agent_run(
    run_context: str | None,
    existing_task_ids: set[int] | None = None,
    agent_name: str | None = None,
) -> bool:
    """判断 agent_run 是否测试残留。

    两条规则（任一命中即为残留）：
      1. ``input_context.target_role`` 等于已废弃的硬编码默认值
         ``"Robot AI Engineer"`` —— 测试套件直接以该字面量调 API 留下的签名。
      2. **孤儿引用**：reviewer 之类的运行记录的 ``task_id`` 指向已不存在的任务
         （任务被清理后，这些运行记录只指向空气，留着只会污染 Agent 活动面板）。
         ⚠️ 依赖调用方传入 ``existing_task_ids``，否则规则 2 不生效 ——
         避免调用方忘了传就把所有 reviewer 记录误判为残留。
    """
    if not run_context:
        return False
    try:
        ctx = json.loads(run_context)
    except (ValueError, TypeError):
        return False

    if ctx.get("target_role") == LEGACY_TEST_TARGET_ROLE:
        return True

    # 规则 2：仅在能校验时才判定，防止误伤
    task_id = ctx.get("task_id")
    if existing_task_ids is not None and isinstance(task_id, int):
        return task_id not in existing_task_ids

    return False


def analyze(db) -> dict:
    """扫描并按规则分类，返回待处理清单（不写库）。"""
    projects = db.query(Project).all()
    tasks = db.query(Task).all()
    milestones = db.query(Milestone).all()
    runs = db.query(AgentRun).all()

    test_projects = [p for p in projects if p.source != "test" and _is_test_project_name(p.name)]
    test_project_ids = {p.id for p in test_projects}

    # 任务：标题命中测试模式，或挂在测试项目下
    test_tasks = [
        t
        for t in tasks
        if t.source != "test"
        and (_is_test_task_title(t.title) or (t.project_id in test_project_ids))
    ]
    test_task_ids = {t.id for t in test_tasks}

    # 里程碑：挂在测试项目下
    test_milestones = [
        m
        for m in milestones
        if m.source != "test" and m.project_id in test_project_ids
    ]

    # Agent 运行：废弃 target_role 签名，或引用了已不存在的任务
    existing_task_ids = {t.id for t in tasks}
    test_runs = [
        r for r in runs if _is_test_agent_run(r.input_context, existing_task_ids, r.agent_name)
    ]

    # 重复任务：同 (title, skill_name, status) 保留最早一条，其余视为冗余
    seen: dict[tuple, int] = {}
    dup_tasks = []
    for t in sorted(tasks, key=lambda x: x.id):
        key = ((t.title or "").strip(), (t.skill_name or "").strip(), t.status)
        if key in seen:
            if t.id not in test_task_ids:
                dup_tasks.append(t)
        else:
            seen[key] = t.id

    # 项目 status 分布（用于报告）
    from collections import Counter

    return {
        "projects_total": len(projects),
        "tasks_total": len(tasks),
        "milestones_total": len(milestones),
        "runs_total": len(runs),
        "test_projects": test_projects,
        "test_tasks": test_tasks,
        "test_milestones": test_milestones,
        "test_runs": test_runs,
        "dup_tasks": dup_tasks,
        "project_status": Counter(p.status for p in projects),
        "real_projects": [p for p in projects if p.name in PROTECTED_PROJECTS],
    }


def print_report(report: dict, mode: str) -> None:
    print("=" * 72)
    print(f"  测试残留数据清理 · {mode}")
    print("=" * 72)
    print()
    print("【现状】")
    print(f"  projects   {report['projects_total']} 行")
    print(f"  tasks      {report['tasks_total']} 行")
    print(f"  milestones {report['milestones_total']} 行")
    print(f"  项目状态分布: {dict(report['project_status'])}")
    print()
    print("【识别为真实项目（白名单保护）】")
    for p in report["real_projects"]:
        print(f"  ✓ #{p.id} {p.name}")
    print()
    print(f"【识别为测试项目】共 {len(report['test_projects'])} 个")
    for p in report["test_projects"][:20]:
        print(f"  - #{p.id} {p.name!r}")
    if len(report["test_projects"]) > 20:
        print(f"  … 其余 {len(report['test_projects']) - 20} 个同类")
    print()
    print(f"【识别为测试任务】共 {len(report['test_tasks'])} 条")
    for t in report["test_tasks"][:10]:
        print(f"  - #{t.id} [{(t.status or ''):7s}] {t.title[:52]!r}")
    if len(report["test_tasks"]) > 10:
        print(f"  … 其余 {len(report['test_tasks']) - 10} 条同类")
    print()
    print(f"【识别为测试里程碑】共 {len(report['test_milestones'])} 条")
    print()
    print(
        f"【识别为测试 Agent 运行】共 {len(report['test_runs'])} 条"
        f" / 总数 {report['runs_total']}"
    )
    print(f"  规则 1：input_context.target_role == {LEGACY_TEST_TARGET_ROLE!r}（该默认值已废弃）")
    print("  规则 2：引用了已不存在的 task_id（孤儿记录）")
    print()
    print(f"【重复任务（同题同技能同状态，仅保留最早一条）】共 {len(report['dup_tasks'])} 条")
    for t in report["dup_tasks"][:10]:
        print(f"  - #{t.id} {t.title[:52]!r}")
    if len(report["dup_tasks"]) > 10:
        print(f"  … 其余 {len(report['dup_tasks']) - 10} 条同类")
    print()
    print("【白名单保护的表（绝不触碰）】")
    print(f"  {', '.join(PROTECTED_TABLES)}")
    print()


def backup_db() -> Path | None:
    """写入前备份 SQLite 文件。"""
    import app.core.config as cfg

    url = cfg.settings.database_url
    if not url.startswith("sqlite"):
        print(f"  ⚠ 非 SQLite（{url}），跳过文件备份 —— 请自行确保有数据库级备份")
        return None

    raw = url.split("sqlite:///", 1)[-1]
    src = Path(raw)
    if not src.is_absolute():
        src = BACKEND / src
    if not src.exists():
        print(f"  ⚠ 未找到数据库文件 {src}，跳过备份")
        return None

    backup_dir = BACKEND.parent / ".workbuddy" / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    dst = backup_dir / f"app.db.purge_{ts}"
    shutil.copy2(src, dst)
    print(f"  ✓ 已备份: {dst}")
    return dst


def _batched(items: list, action, label: str) -> int:
    """分批执行，每批后核对。"""
    total = 0
    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i : i + BATCH_SIZE]
        for obj in batch:
            action(obj)
        total += len(batch)
        print(f"    {label}: {total}/{len(items)}")
    return total


def main() -> int:
    parser = argparse.ArgumentParser(
        description="清理开发库中的测试残留数据（默认 dry-run）"
    )
    parser.add_argument("--apply", action="store_true", help="真正写入（默认只报告）")
    parser.add_argument(
        "--purge", action="store_true", help="物理删除已标记的测试残留（需 --apply，不可逆）"
    )
    parser.add_argument(
        "--dedupe", action="store_true", help="同时清理重复任务（保留最早一条）"
    )
    args = parser.parse_args()

    if args.purge and not args.apply:
        print("✗ --purge 必须与 --apply 一起使用（防止误删）")
        return 2

    db = SessionLocal()
    try:
        report = analyze(db)
        mode = "DRY-RUN（不写库）" if not args.apply else "APPLY"
        print_report(report, mode)

        if not args.apply:
            print("-" * 72)
            print("这是 dry-run，未修改任何数据。确认清单无误后执行：")
            print("  python scripts/purge_test_data.py --apply            # 仅标记")
            print("  python scripts/purge_test_data.py --apply --purge    # 标记 + 删除")
            return 0

        print("-" * 72)
        print("【执行】")
        backup_db()

        # 1) 标记测试项目
        changed_p = _batched(
            report["test_projects"],
            lambda p: setattr(p, "source", "test"),
            "标记测试项目",
        )
        # 2) 标记测试任务
        changed_t = _batched(
            report["test_tasks"],
            lambda t: setattr(t, "source", "test"),
            "标记测试任务",
        )
        # 3) 标记测试里程碑
        changed_m = _batched(
            report["test_milestones"],
            lambda m: setattr(m, "source", "test"),
            "标记测试里程碑",
        )
        db.commit()
        print(f"  ✓ 标记完成：项目 {changed_p} / 任务 {changed_t} / 里程碑 {changed_m}")

        # 4) 物理删除（可选）
        if args.purge:
            print()
            print("  【删除已标记的测试残留】")
            n_m = db.query(Milestone).filter(Milestone.source == "test").delete(synchronize_session=False)
            n_t = db.query(Task).filter(Task.source == "test").delete(synchronize_session=False)
            # 先删里程碑/任务（子表），再删项目，避免外键约束问题
            n_p = db.query(Project).filter(Project.source == "test").delete(synchronize_session=False)
            # Agent 运行：无 source 列，按废弃签名直接删（见 LEGACY_TEST_TARGET_ROLE 注释）
            n_r = (
                db.query(AgentRun)
                .filter(AgentRun.id.in_([r.id for r in report["test_runs"]]))
                .delete(synchronize_session=False)
                if report["test_runs"]
                else 0
            )
            db.commit()
            print(f"  ✓ 已删除：里程碑 {n_m} / 任务 {n_t} / 项目 {n_p} / Agent 运行 {n_r}")

        # 5) 重复任务（可选）
        if args.dedupe:
            print()
            print("  【清理重复任务：同 title+skill+status 保留最早一条】")
            deduped = _batched(
                report["dup_tasks"],
                lambda t: setattr(t, "source", "test"),
                "标记重复任务",
            )
            db.commit()
            if args.purge and deduped:
                n_dup = (
                    db.query(Task)
                    .filter(Task.id.in_([t.id for t in report["dup_tasks"]]))
                    .delete(synchronize_session=False)
                )
                db.commit()
                print(f"  ✓ 已删除重复任务 {n_dup} 条")
            else:
                print(f"  ✓ 已标记重复任务 {deduped} 条（未删除，加 --purge 才删）")

        print()
        print("=" * 72)
        print("  完成。建议复核：curl 127.0.0.1:8000/api/projects | head -c 400")
        print("=" * 72)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
