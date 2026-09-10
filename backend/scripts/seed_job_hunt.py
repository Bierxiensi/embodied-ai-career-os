"""求职看板种子数据（幂等可重跑）。

把 Career OS 从「学习记录系统」灌入「求职作战看板」所需的业务数据：

    1. 更新 Career 单例：薪资目标 40K、截止日 2026-10-31、备注三赛道策略
    2. 校准技能画像：把库内等级对齐 app/core/skill_profile.py 真实自评（幂等覆盖）
    3. 创建「求职冲刺 · 2026 Q4」项目 + 5 个里程碑（V0-V4）
    4. 追加求职周任务（关联该项目）
    5. 灌入若干示例投递记录（按 company+role 去重，避免重复）

运行：
    cd backend
    python scripts/seed_job_hunt.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# 允许从 backend 目录运行：将 backend 加入 sys.path 以便 import app
BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.target_roles import JOB_HUNT_PROJECT_NAME, TARGET_ROLES
from app.db.base import SessionLocal, init_db
from app.models.career import Career
from app.models.job_application import JobApplication
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.skill import Skill
from app.models.task import Task


def _collect_required_skills() -> set[str]:
    """汇总三条赛道要求的全部技能名（去空白）。"""
    names: set[str] = set()
    for role in TARGET_ROLES:
        names.update(s.strip() for s in role.required_skills)
    return names


def update_career(db: SessionLocal) -> None:
    """更新 Career 单例为求职冲刺口径（幂等：始终对齐最新策略）。"""
    career = db.query(Career).first()
    if not career:
        career = Career(target_role="Robot AI Engineer")
        db.add(career)
        db.flush()

    career.target_role = "LLM / 大模型算法工程师（主攻）"
    career.salary_target = 40000  # 36-42K 中值，便于看板对照
    career.timeframe = "2026-10-31"  # 截止签约日（防社保中断）
    career.notes = (
        "v2.0 战略：LLM 深度为主 + VLM 轻量卡位。"
        "主攻 LLM 算法(36-45K)，卡位多模态/VLM(36-45K)，保底 AI 算法/推理(30-40K)；"
        "具身智能长期观察，30 天内不投入。10 月底前落定以防社保中断。"
    )
    db.commit()
    print(
        f"  ✓ Career 已更新：目标薪资 {career.salary_target}，"
        f"截止 {career.timeframe}"
    )


def calibrate_skills(db: SessionLocal) -> None:
    """把库内技能等级校准到真实画像（幂等，可反复重跑）。

    真实自评的唯一数据源是 app/core/skill_profile.py：
    - 已存在的技能：对齐 level / target_level / category / evidence
      （修正历史遗留的失真数据，如把 ROS2 从旧值纠正为真实值）
    - 缺失的技能：按画像插入
    - 画像未覆盖但赛道要求的技能：按 level=0 补齐
    """
    from app.core.skill_profile import SKILL_PROFILE

    existing = {s.name.lower(): s for s in db.query(Skill).all()}
    updated: list[str] = []
    added: list[str] = []

    for p in SKILL_PROFILE:
        s = existing.get(p.name.lower())
        if s is None:
            db.add(
                Skill(
                    name=p.name,
                    category=p.category,
                    level=p.level,
                    target_level=p.target_level,
                    evidence=list(p.evidence),
                )
            )
            added.append(p.name)
            continue
        if (
            s.level != p.level
            or s.target_level != p.target_level
            or s.category != p.category
            or (s.evidence or []) != p.evidence
        ):
            s.category = p.category
            s.level = p.level
            s.target_level = p.target_level
            s.evidence = list(p.evidence)
            updated.append(p.name)

    # 兜底：赛道要求但画像未定义的技能（防止 target_roles 改了却没同步）
    profiled = {p.name.lower() for p in SKILL_PROFILE}
    for name in sorted(_collect_required_skills()):
        if name.lower() in profiled or name.lower() in existing:
            continue
        req_level = max(
            (
                r.required_level
                for r in TARGET_ROLES
                if name in {x.strip() for x in r.required_skills}
            ),
            default=4,
        )
        db.add(Skill(name=name, category="Weak", level=0, target_level=req_level, evidence=[]))
        added.append(name)

    db.commit()
    if updated:
        print(f"  ✓ 校准技能 {len(updated)} 项：{', '.join(updated)}")
    if added:
        print(f"  ✓ 新增技能 {len(added)} 项：{', '.join(added)}")
    if not updated and not added:
        print("  - 技能画像已对齐，无需变更")


def ensure_project_and_milestones(db: SessionLocal) -> Project:
    """创建求职项目 + 5 个里程碑（V0-V4）。"""
    project = (
        db.query(Project).filter(Project.name == JOB_HUNT_PROJECT_NAME).first()
    )
    if not project:
        project = Project(
            name=JOB_HUNT_PROJECT_NAME,
            goal="2026 Q4 求职冲刺：10月底前落定 36-42K 具身/机器人方向 offer",
            description="主攻具身VLA / 折中机器人软件 / 保底Agent应用 三赛道并进",
            status="active",
            current_version="V0",
            sort_order=1,
        )
        db.add(project)
        db.flush()
        print(f"  ✓ 创建项目：{JOB_HUNT_PROJECT_NAME}")
    else:
        print(f"  - 项目已存在：{JOB_HUNT_PROJECT_NAME}")

    milestones = [
        ("V0", "画像与简历", "对齐三赛道岗位JD，产出针对性简历（Agent工程主线 + SO101真机闭环亮点）", "doing"),
        ("V1", "内推与海投启动", "激活内推网络 + Boss/猎聘每日海投，建立投递漏斗", "todo"),
        ("V2", "技术面准备", "整理SO101真机demo与指标、算法/系统设计题、ROS2+VLA技术叙事", "todo"),
        ("V3", "面试冲刺", "并行推进多场面试，按反馈迭代话术与证据", "todo"),
        ("V4", "offer谈判与落定", "对比offer，10/31前签约，确保薪资与社保衔接", "todo"),
    ]
    existing_ms = {
        m.version
        for m in db.query(Milestone).filter(Milestone.project_id == project.id)
    }
    added = 0
    for i, (ver, title, goal, status) in enumerate(milestones):
        if ver in existing_ms:
            continue
        db.add(
            Milestone(
                project_id=project.id,
                version=ver,
                title=title,
                goal=goal,
                status=status,
                sort_order=i,
            )
        )
        added += 1
    if added:
        db.commit()
        print(f"  ✓ 新增里程碑 {added} 个")
    else:
        print("  - 里程碑已齐备，无需新增")
    return project


def ensure_tasks(db: SessionLocal, project: Project) -> None:
    """追加求职周任务（按 title 去重）。"""
    existing = {t.title for t in db.query(Task).all()}
    tasks = [
        Task(
            title="完善简历：突出 Agent 工程 + SO101 真机闭环",
            objective="产出 3 版针对性简历（主攻/折中/保底），量化项目指标",
            duration=180, difficulty="intermediate", status="doing",
            skill_name="Job Hunt", project_id=project.id,
            acceptance=["3版简历定稿", "SO101 指标可视化", "内推人清单整理"],
        ),
        Task(
            title="整理 SO101 真机 demo 与成功率数据",
            objective="录制并剪辑真机闭环视频，整理成功率/泛化指标",
            duration=120, difficulty="intermediate", status="todo",
            skill_name="Robot Learning", project_id=project.id,
            acceptance=["demo 视频", "成功率数据表", "泛化案例"],
        ),
        Task(
            title="每日海投 + 内推节奏",
            objective="每日海投 5 家 + 内推 2 家，维护投递漏斗",
            duration=60, difficulty="beginner", status="todo",
            skill_name="Job Hunt", project_id=project.id,
            acceptance=["投递记录入系统", "每周复盘漏斗"],
        ),
        Task(
            title="算法/系统设计题刷题（具身方向）",
            objective="覆盖机器人SLAM/VLA/控制相关高频题",
            duration=90, difficulty="advanced", status="todo",
            skill_name="Deep Learning", project_id=project.id,
            acceptance=["每周 10 题", "整理题解"],
        ),
    ]
    added = 0
    for t in tasks:
        if t.title in existing:
            continue
        db.add(t)
        added += 1
    if added:
        db.commit()
        print(f"  ✓ 新增求职任务 {added} 项")
    else:
        print("  - 求职任务已齐备，无需新增")


def ensure_applications(db: SessionLocal) -> None:
    """灌入示例投递记录（按 company+role 去重，仅在偏空时补充）。"""
    samples = [
        JobApplication(
            company="某自动驾驶机器人公司", role="具身智能算法工程师",
            track="embodied", source="内推", status="screening",
            salary_range="38-45K", applied_at=date(2026, 9, 15),
            next_action="等待技术一面安排",
        ),
        JobApplication(
            company="某工业具身初创", role="机器人软件工程师(ROS2+AI)",
            track="robot-software", source="Boss直聘", status="applied",
            salary_range="32-38K", applied_at=date(2026, 9, 18),
            next_action="HR初筛中",
        ),
        JobApplication(
            company="某AI应用大厂", role="Agent 应用算法工程师",
            track="agent", source="猎聘", status="interview",
            salary_range="35-42K", applied_at=date(2026, 9, 10),
            next_action="准备二面：Agent架构设计",
        ),
        JobApplication(
            company="某RAG创业公司", role="LLM 算法工程师",
            track="agent", source="官网", status="rejected",
            salary_range="30-36K", applied_at=date(2026, 9, 5),
            next_action="复盘笔试题",
        ),
    ]
    existing_keys = {(a.company, a.role) for a in db.query(JobApplication).all()}
    added = 0
    for a in samples:
        if (a.company, a.role) in existing_keys:
            continue
        db.add(a)
        added += 1
    if added:
        db.commit()
        print(f"  ✓ 新增示例投递 {added} 条")
    else:
        print("  - 投递记录已存在，无需新增")


def main() -> None:
    print("== 求职看板种子数据 ==")
    init_db()  # 保证表结构 + 基础种子就绪
    db = SessionLocal()
    try:
        update_career(db)
        calibrate_skills(db)
        project = ensure_project_and_milestones(db)
        ensure_tasks(db, project)
        ensure_applications(db)
        print("== 完成 ==")
    finally:
        db.close()


if __name__ == "__main__":
    main()
