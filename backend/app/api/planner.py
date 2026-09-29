"""Planner Agent API 路由（Day6 迁移至 /api/planner 前缀）。

Day6 改动：
- 路由从 /planner 迁移到 /api/planner（统一前缀，便于前端代理）
- 生成任务后写入 tasks 表（Day6 闭环：Planner → DB → Dashboard）
- 写入 agent_runs 表记录 Agent 决策（可追溯）

2026-09-10 改动（用户反馈「任务没有跟随不同的角色看板走」+「生成今日任务看不明白」）：
1. **赛道感知**：请求可带 `track_key`，Planner 的候选技能收敛到该赛道的
   required_skills —— 在「求职冲刺」视角不会再产出 ROS2/Isaac 这类具身任务，
   在「具身智能」视角才会。产出的任务打上 `track_key`，供看板按视角过滤。
2. **决策透明**：响应不再只回一句 title，而是带回
   `track_key/track_name/skill_level/skill_target/gap/reused/reason` ——
   前端据此渲染"为什么选它、新建还是复用"。复用（幂等命中）与新建
   在响应里可区分，不再都显示"已生成"。
3. 历史遗留：`target_role` 硬编码 "Robot AI Engineer" 曾导致 Planner 一直
   产出具身方向任务，已改为读 target_roles 配置的主攻赛道。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.planner.graph import build_planner_graph
from app.core.capacity import assert_plan_capacity, daily_study_minutes
from app.core.response import ApiResponse, fail, ok
from app.core.target_roles import TECH_BLACKLIST, TARGET_ROLES, TargetRole
from app.db.base import get_db
from app.models.agent_run import AgentRun
from app.models.skill import Skill
from app.models.task import Task

router = APIRouter(prefix="/planner", tags=["planner"])

# 图编译一次复用（无状态）
_planner = build_planner_graph()

# 冻结赛道（长期观察）的单任务时长上限 —— 对应"低强度巩固通道"：
# 具身赛道已 frozen，不该在冲刺期占用整块时间，但可以保持手感。
FROZEN_TRACK_MAX_MINUTES = 45

# 默认目标岗位取自 target_roles 配置的「主攻」赛道。
# 原实现硬编码 "Robot AI Engineer"（具身方向），与 2026-09-10 战略调整
# （llm 主攻 / embodied 冻结）冲突 —— 会让 Planner 持续产出具身方向任务。
# 这里改为读配置，改 target_roles.py 即改默认，前后端不再各存一份过期字面量。
_DEFAULT_TRACK: TargetRole | None = next(
    (r for r in TARGET_ROLES if r.priority == "主攻"), TARGET_ROLES[0] if TARGET_ROLES else None
)
_DEFAULT_TARGET_ROLE: str = _DEFAULT_TRACK.name if _DEFAULT_TRACK else "未设定"


class SkillIn(BaseModel):
    """技能输入项。"""

    name: str
    level: int = Field(ge=0, le=5)
    target: int = Field(ge=0, le=5)


class PlannerRequest(BaseModel):
    """Planner 请求体。"""

    available_minutes: int = Field(default=45, ge=5, le=480)
    target_role: str = Field(default=_DEFAULT_TARGET_ROLE)
    # 赛道：llm / vlm / ai-algo / embodied。不传则由后端取「主攻」赛道，
    # 并据其 required_skills 收敛候选技能（避免跨赛道乱出任务）。
    track_key: str | None = Field(default=None)
    skills: list[SkillIn]
    energy_level: str = Field(default="normal")
    current_focus: str | None = Field(default=None)
    generator: str = Field(default="rule")
    # Day6 新增：是否将生成的任务持久化到 tasks 表
    persist: bool = Field(default=True)
    # V2 Project 模块：关联项目和里程碑
    project_id: int | None = Field(default=None)
    milestone_id: int | None = Field(default=None)


class GeneratedTaskOut(BaseModel):
    """Planner 生成任务响应。

    2026-09-10 起额外携带**决策细节**，让"生成今日任务"这个动作可解释：
    选了哪个技能、它的当前等级与要求等级、缺口多大、属于哪条赛道、
    是新建还是复用了今天已有的任务。
    """

    title: str
    skill: str
    objective: str | None = None
    # 默认 0：黑名单硬拒绝分支不产生任务时长，缺省避免该分支 500（P2 测试实测）。
    duration: int = 0
    difficulty: str | None = None
    acceptance: list[str] = []
    resources: list[str] = []
    status: str = "todo"
    task_id: int | None = None  # 持久化后的任务 ID（persist=False 时为 None）

    # ===== 决策细节（新增）=====
    track_key: str | None = None
    track_name: str | None = None
    track_frozen: bool = False
    skill_level: int | None = None
    skill_target: int | None = None
    gap: int | None = None
    # True = 今天已有同题任务被复用（幂等命中），False = 本次新建
    reused: bool = False
    # 一句话解释为什么选这个技能（直接渲染到前端结果卡）
    reason: str = ""
    # P2：被 D 级技术黑名单拦截的技能名（硬拒绝，不生成发散任务）
    blocked: list[str] = []


def _resolve_track(track_key: str | None) -> TargetRole | None:
    """按 key 取赛道；未指定或未命中则回退「主攻」赛道。"""
    if track_key:
        hit = next((r for r in TARGET_ROLES if r.key == track_key), None)
        if hit is not None:
            return hit
    return _DEFAULT_TRACK


def _scope_skills_to_track(
    db: Session, req: PlannerRequest, track: TargetRole | None
) -> list[SkillIn]:
    """把候选技能收敛到赛道的 required_skills，并与赛道口径对齐。

    为什么必须收敛：旧实现把全部 48 项技能丢给 Planner，它按「最大 gap」
    选技能 —— 于是冲刺 LLM 岗位时会挑出 Sim2Real（gap=4）这类具身技能，
    产出的任务与当前视角完全无关。

    对齐口径：level 取前端传入值（缺则查库，再缺按 0），target 取
    `track.required_level` —— 与 /api/job-hunt 的雷达图**同一套算法**，
    保证「雷达说缺 2 级」与「Planner 说 gap=2」是同一个数。
    """
    if track is None:
        return req.skills

    provided = {s.name: s for s in req.skills}
    scoped: list[SkillIn] = []
    for name in track.required_skills:
        hit = provided.get(name)
        if hit is not None:
            scoped.append(
                SkillIn(name=name, level=hit.level, target=track.required_level)
            )
            continue
        # 前端没传这项技能（例如只传了雷达轴子集）→ 回退查库
        row = db.query(Skill).filter(Skill.name == name).first()
        scoped.append(
            SkillIn(
                name=name,
                level=row.level if row else 0,
                target=track.required_level,
            )
        )
    return scoped


def _persist_task(
    db: Session,
    task_data: dict,
    project_id: int | None,
    milestone_id: int | None,
    track_key: str | None,
) -> tuple[Task, bool]:
    """幂等持久化 Planner 任务。

    历史问题（2026-09-10 审计实测）：原实现无条件 ``db.add(Task(...))``，
    每次点「生成今日任务」都插一条新记录，没有任何去重 ——
    累积出「ROS2 Topic 通信机制实践 × 29」「Python asyncio 异步编程实践 × 27」
    这类重复（dev 库 292 个任务里有大量同题重录）。

    幂等规则：同一天内，若已存在 **相同 (title, skill_name, track_key) 且未完成**
    的任务，直接复用它，不新增。这样反复点击「生成今日任务」不会把任务池撑爆，
    同时保留「跨天重新规划」的正常语义（新的一天可以再产生同题任务）。

    `track_key` 进幂等键：同名技能可能同时属于多条赛道（如 PyTorch 在
    llm / vlm / ai-algo / embodied 都有），不加赛道会把两边的任务误判为重复。

    打标：新建的任务 ``source="planner"`` + ``track_key``。

    Returns:
        (任务实例, 是否新建)。调用方据此区分「新建」与「复用」，
        前端不再把复用也显示成"已生成"。
    """
    title = (task_data.get("title") or "").strip()
    skill = (task_data.get("skill") or "").strip()
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    existing_q = db.query(Task).filter(
        Task.title == title,
        Task.skill_name == skill,
        Task.status != "done",
        Task.created_at >= today_start,
    )
    if track_key is not None:
        existing_q = existing_q.filter(Task.track_key == track_key)
    # 幂等范围必须与请求范围**完全一致**：不带项目的请求只复用"全局任务"，
    # 带项目的请求只复用同项目的任务。
    # 若写成"project_id 非空时才过滤"，不带项目的请求会命中并复用某条
    # milestone 绑定的任务（测试实测到：同一技能同一天因 project_id 不同
    # 合法共存两条，全局请求把它们当成了自己的复用目标）。
    if project_id is None:
        existing_q = existing_q.filter(Task.project_id.is_(None))
    else:
        existing_q = existing_q.filter(Task.project_id == project_id)

    existing = existing_q.first()
    if existing is not None:
        return existing, False

    new_task = Task(
        title=title,
        objective=task_data.get("objective"),
        duration=task_data.get("duration"),
        difficulty=task_data.get("difficulty"),
        status=task_data.get("status", "todo"),
        skill_name=task_data.get("skill"),
        acceptance=task_data.get("acceptance", []),
        resources=task_data.get("resources", []),
        project_id=project_id,
        milestone_id=milestone_id,
        source="planner",
        track_key=track_key,
    )
    db.add(new_task)
    db.flush()  # 取自增 ID
    return new_task, True


@router.post("/generate")
def generate_task(
    req: PlannerRequest, db: Session = Depends(get_db)
) -> ApiResponse[GeneratedTaskOut]:
    """调用 Planner Agent 生成每日核心学习任务。

    Day6 闭环：
      1. 解析赛道 → 收敛候选技能到该赛道的硬性要求
      2. 执行 LangGraph 生成任务（选 gap 最大的技能）
      3. 写入 agent_runs 表（决策可追溯）
      4. 按 persist 选项幂等写入 tasks 表（打 track_key 标）
      5. 返回决策细节，供前端解释"为什么是这条任务"
    """

    # 0. 赛道解析 + 技能收敛
    track = _resolve_track(req.track_key)
    track_key = track.key if track else None
    scoped_skills = _scope_skills_to_track(db, req, track)

    # P2：D 级技术黑名单硬拒绝（v2.0 §19 / docs 决策 6）。
    # 命中黑名单的技能直接剔除出候选，绝不生成对应任务；
    # 若候选全部被拦截，明确返回拒绝文案（不静默跳过、不降级成别的任务）。
    blocked = [s.name for s in scoped_skills if s.name in TECH_BLACKLIST]
    if blocked:
        scoped_skills = [s for s in scoped_skills if s.name not in TECH_BLACKLIST]
    if not scoped_skills:
        return ok(
            GeneratedTaskOut(
                title="",
                skill="",
                reason=(
                    "⛔ 命中 D 级技术（"
                    + "、".join(blocked)
                    + "），30 天窗口内不投入。如确认要学，需二次确认。"
                ),
                blocked=blocked,
            ),
            message="已拦截 D 级技术任务",
        )

    # 冻结赛道走"低强度巩固"：单任务不超过 FROZEN_TRACK_MAX_MINUTES，
    # 避免长期赛道在冲刺期吃掉整块时间。
    available_minutes = req.available_minutes
    if track is not None and track.frozen:
        available_minutes = min(available_minutes, FROZEN_TRACK_MAX_MINUTES)

    # 容量预检（spec §2.4/§5.1）：按实际将要生成的分钟数（冻结赛道已钳制）
    # 对照单日预算，超限**显式拒绝**并给最短可行周期——禁止静默截断。
    # 放在请求校验之后、图执行之前，超限请求不消耗任何生成开销。
    check = assert_plan_capacity(
        planned_minutes=available_minutes,
        available_minutes=daily_study_minutes(),
    )
    if not check["ok"]:
        return fail(check["suggestion"])  # 显式拒绝 + 最短可行周期，禁止静默截断（spec §2.4/§5.1）

    # V2: 解析项目上下文
    project_context = ""
    if req.project_id:
        from app.models.project import Project
        from app.models.milestone import Milestone
        project = db.get(Project, req.project_id)
        if project:
            project_context = f"当前项目：{project.name}（{project.goal}）\n"
            if req.milestone_id:
                milestone = db.get(Milestone, req.milestone_id)
                if milestone:
                    project_context += f"当前里程碑：{milestone.version} {milestone.title}（{milestone.goal}）\n"
                    done_tasks = (
                        db.query(Task)
                        .filter(Task.milestone_id == req.milestone_id, Task.status == "done")
                        .all()
                    )
                    if done_tasks:
                        project_context += "已完成："
                        project_context += "、".join(t.title for t in done_tasks)

    # 1. 组装状态并执行状态图
    state = {
        "available_minutes": available_minutes,
        "target_role": track.name if track else req.target_role,
        "skills": [s.model_dump() for s in scoped_skills],
        "energy_level": req.energy_level,
        "current_focus": req.current_focus,
        "generator": req.generator,
        "project_id": req.project_id,
        "milestone_id": req.milestone_id,
        "project_context": project_context,
        # 赛道信息透传给生成器/日志，便于排查"这条任务为什么长这样"
        "track_key": track_key,
    }
    result = _planner.invoke(state)
    task_data = result.get("task") or {}
    selected_skill = result.get("selected_skill") or task_data.get("skill") or ""

    # 2. 记录 Agent 执行（输入 + 输出 + tracing），便于 Debug / 面试展示
    run_id = str(uuid.uuid4())
    db.add(
        AgentRun(
            id=run_id,
            agent_name="planner",
            input_context=json.dumps(state, ensure_ascii=False),
            output_result=json.dumps(task_data, ensure_ascii=False),
            status="success",
            duration_ms=0,  # 直调 API 不计时，由 Orchestrator/Executor 统一追踪
            trace_id=run_id,
        )
    )

    # 3. 持久化任务到 tasks 表（幂等）
    task_id = None
    reused = False
    if req.persist and task_data:
        new_task, created = _persist_task(
            db, task_data, req.project_id, req.milestone_id, track_key
        )
        task_id = new_task.id
        reused = not created

    db.commit()

    # 4. 组装决策细节：把"为什么选它"讲清楚
    picked = next((s for s in scoped_skills if s.name == selected_skill), None)
    gap_val = None
    if picked is not None:
        gap_val = max(picked.target - picked.level, 0)

    reason_parts: list[str] = []
    if track is not None:
        reason_parts.append(f"当前视角「{track.name}」")
    if picked is not None:
        reason_parts.append(
            f"{picked.name} 缺口最大（{picked.level} → 目标 {picked.target}，差 {gap_val} 级）"
        )
    else:
        reason_parts.append(f"选中技能 {selected_skill}")
    if track is not None and track.frozen:
        reason_parts.append(
            f"该赛道已冻结，仅低强度巩固（≤{FROZEN_TRACK_MAX_MINUTES} 分钟）"
        )
    if reused:
        reason_parts.append("今日已有同题任务，已复用而非新建")
    reason = "；".join(reason_parts) + "。"

    return ok(
        GeneratedTaskOut(
            title=task_data.get("title", ""),
            skill=task_data.get("skill", ""),
            objective=task_data.get("objective"),
            duration=task_data.get("duration", 0),
            difficulty=task_data.get("difficulty"),
            acceptance=task_data.get("acceptance", []),
            resources=task_data.get("resources", []),
            status=task_data.get("status", "todo"),
            task_id=task_id,
            track_key=track_key,
            track_name=track.name if track else None,
            track_frozen=bool(track.frozen) if track else False,
            skill_level=picked.level if picked else None,
            skill_target=picked.target if picked else None,
            gap=gap_val,
            reused=reused,
            reason=reason,
            blocked=blocked,
        ),
        message=f"Planner generated task for {selected_skill}",
    )
