# 任务脚手架系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 V0 验证有效的「Baseline + 必改项 + 物理工作空间」学习模式系统化，落到 Milestone 数据模型 + 幂等任务生成 + 前端展示。

**Architecture:** 智能层与记录层分离——Claude Code（Coach）物理建工作空间、写 baseline、设计必改项，通过 PATCH 回填到 Milestone；后端只做状态追踪（幂等生成、字段登记）；前端展示脚手架并禁用重复生成。修 BUG 1（重复生成同名任务）用后端幂等检查（根因），非前端临时禁用。

**Tech Stack:** FastAPI + SQLAlchemy（JSON 列）+ SQLite / Next.js + TypeScript / pytest TestClient

**Design Spec:** `docs/superpowers/specs/2026-08-13-task-scaffolding-design.md`

## Global Constraints

- 后端所有响应遵循 `ApiResponse<T>` + `ok()` 工厂模式，测试用 `fastapi.testclient.TestClient` 打真实 DB（非 mock）
- 迁移用 `migrations/*.sql` + `run_migration.py`（无 Alembic），幂等靠 `ALTER TABLE ADD COLUMN` + 吞「duplicate column」错误；迁移名（去 `.sql` 后缀）作为 `_migrations_applied` 表主键
- `required_modifications` 存 JSON（SQLAlchemy `JSON` 类型，SQLite 底层 TEXT），结构：`[{title, goal, files, verification}]`
- 前端字段命名：后端 snake_case（`required_modifications`）→ 前端 camelCase（`requiredModifications`），转换只发生在 services 层 DTO 映射
- 幂等策略是后端根因修复（生成前查 `Task.milestone_id` 已有任务则返回），前端按钮禁用只是 UI 反馈，不是正确性依赖
- 提交格式：`type(scope): message`

---

## File Structure

- **`backend/app/models/milestone.py`** — Milestone ORM，加 `workspace` + `required_modifications` 列
- **`backend/migrations/0004_milestone_scaffolding.sql`** — ALTER TABLE 加两列（幂等）
- **`backend/app/schemas/project.py`** — `MilestonePatch` / `MilestoneOut` 加两字段
- **`backend/app/api/milestones.py`** — `generate_tasks_from_milestone` 幂等检查 + 抽 `_task_to_dict`
- **`frontend/src/types/index.ts`** — `Milestone` 加 `workspace` / `requiredModifications` + `RequiredModification` 接口
- **`frontend/src/services/projectService.ts`** — `MilestoneDTO` + `toMilestone` 加字段映射
- **`frontend/src/components/MilestoneTimeline.tsx`** — 按钮幂等状态 + 脚手架详情展示
- **`frontend/src/app/projects/[id]/page.tsx`** — 计算已生成任务的 milestoneId 集合，传给时间线组件

---

### Task 1: Milestone 脚手架字段（模型 + 迁移 + schema）

**Files:**
- Modify: `backend/app/models/milestone.py:7`（import）+ `:23-24` 之后加字段
- Create: `backend/migrations/0004_milestone_scaffolding.sql`
- Modify: `backend/app/schemas/project.py:54-71`
- Test: `backend/tests/test_milestone_scaffolding.py`

**Interfaces:**
- Consumes: `Milestone` ORM（`backend/app/models/milestone.py`）、`MilestonePatch`/`MilestoneOut`（`backend/app/schemas/project.py`）
- Produces: `Milestone.workspace: str | None`、`Milestone.required_modifications: list | None`，前端 Task 3 依赖这两个字段名

- [ ] **Step 1: 写失败的测试**

```python
# backend/tests/test_milestone_scaffolding.py
"""Milestone 脚手架字段测试：workspace + required_modifications。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _create_project(name="Scaffold Test"):
    resp = client.post("/api/projects", json={
        "name": name, "goal": "TG", "status": "active", "current_version": "V0",
    })
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


def test_patch_and_read_scaffolding_fields():
    """PATCH 写 workspace + required_modifications，GET 能读回。"""
    pid = _create_project()
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V1", "title": "ROS2 基础", "goal": "topic 通信",
        "status": "in_progress", "sort_order": 1,
    })
    mid = resp.json()["data"]["id"]

    mods = [
        {"title": "加 launch 文件", "goal": "理解 node 编排",
         "files": ["launch.py"], "verification": "ros2 launch ..."},
    ]

    resp = client.patch(f"/api/milestones/{mid}", json={
        "workspace": "so101/v1_ros2/",
        "required_modifications": mods,
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["workspace"] == "so101/v1_ros2/"
    assert data["required_modifications"] == mods

    # GET 项目详情能读回
    resp = client.get(f"/api/projects/{pid}")
    m = [x for x in resp.json()["data"]["milestones"] if x["id"] == mid][0]
    assert m["workspace"] == "so101/v1_ros2/"
    assert m["required_modifications"][0]["title"] == "加 launch 文件"


def test_scaffolding_fields_default_none():
    """未设置时，workspace/required_modifications 默认为 None。"""
    pid = _create_project()
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V1", "title": "M", "goal": "G",
        "status": "in_progress", "sort_order": 1,
    })
    data = resp.json()["data"]
    assert data["workspace"] is None
    assert data["required_modifications"] is None
```

- [ ] **Step 2: 跑测试验证失败（RED）**

Run: `cd backend && python -m pytest tests/test_milestone_scaffolding.py -v`
Expected: `test_patch_and_read_scaffolding_fields` FAIL（`KeyError: 'workspace'` 或 `AssertionError`，因为 `MilestoneOut` 还没有该字段）

- [ ] **Step 3: 改模型 + schema + 迁移**

改 `backend/app/models/milestone.py:7`，`JSON` 加进 import：

```python
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
```

在 `backend/app/models/milestone.py:23-24`（`sort_order` 之后、`created_at` 之前）加两字段：

```python
    workspace: Mapped[str | None] = mapped_column(String(200), nullable=True)
    required_modifications: Mapped[list | None] = mapped_column(JSON, nullable=True)
```

创建 `backend/migrations/0004_milestone_scaffolding.sql`：

```sql
-- V2.1 Task Scaffolding: Add workspace + required_modifications to milestones
-- workspace: 物理工作空间路径（Claude Code 写 baseline 时落盘，后端只存路径）
-- required_modifications: 必改项清单（JSON 数组）

ALTER TABLE milestones ADD COLUMN workspace VARCHAR(200);
ALTER TABLE milestones ADD COLUMN required_modifications JSON;
```

改 `backend/app/schemas/project.py`，`MilestonePatch` 加两个可选字段：

```python
class MilestonePatch(BaseModel):
    version: str | None = None
    title: str | None = None
    goal: str | None = None
    status: str | None = None
    sort_order: int | None = None
    workspace: str | None = None
    required_modifications: list | None = None
```

`MilestoneOut` 加两个字段：

```python
class MilestoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    version: str
    title: str
    goal: str
    status: str
    sort_order: int
    workspace: str | None = None
    required_modifications: list | None = None
```

- [ ] **Step 4: 跑迁移**

Run: `cd backend && python migrations/run_migration.py --only 0004`
Expected: `✓ 应用迁移: 0004_milestone_scaffolding.sql`（或「跳过迁移（已应用）」如果 create_all 已建带字段的表）

- [ ] **Step 5: 跑测试验证通过（GREEN）**

Run: `cd backend && python -m pytest tests/test_milestone_scaffolding.py -v`
Expected: 2/2 PASS

- [ ] **Step 6: 跑全量测试确认无回归**

Run: `cd backend && python -m pytest tests/ -v`
Expected: 全部 existing + new 通过

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/milestone.py backend/app/schemas/project.py \
  backend/migrations/0004_milestone_scaffolding.sql backend/tests/test_milestone_scaffolding.py
git commit -m "feat(backend): add workspace + required_modifications to milestone"
```

---

### Task 2: 幂等生成任务（修 BUG 1）

**Files:**
- Modify: `backend/app/api/milestones.py:116-161`
- Test: `backend/tests/test_milestones_api.py`（追加一个测试函数）

**Interfaces:**
- Consumes: `Task.milestone_id`（现有字段）、`_decompose_milestone`（现有，签名不变）
- Produces: `_task_to_dict(t: Task) -> dict` 帮助函数，幂等分支复用

- [ ] **Step 1: 写失败的测试**

在 `backend/tests/test_milestones_api.py` 末尾追加：

```python
def test_generate_tasks_idempotent():
    """第二次生成任务应返回已有任务，不重复创建（BUG 1 回归测试）。"""
    pid = _create_project("Idempotent Test")
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V1", "title": "ROS2 基础", "goal": "topic 通信 + publisher/subscriber",
        "status": "in_progress", "sort_order": 1,
    })
    mid = resp.json()["data"]["id"]

    payload = {
        "available_minutes": 120,
        "skills": [{"name": "ROS2", "level": 1, "target": 4}],
    }
    r1 = client.post(f"/api/milestones/{mid}/tasks", json=payload)
    assert r1.status_code == 200
    ids1 = [t["id"] for t in r1.json()["data"]]

    r2 = client.post(f"/api/milestones/{mid}/tasks", json=payload)
    assert r2.status_code == 200
    ids2 = [t["id"] for t in r2.json()["data"]]

    # 幂等：返回的任务 id 完全一致，未新建
    assert len(ids1) > 0
    assert ids1 == ids2
```

- [ ] **Step 2: 跑测试验证失败（RED）**

Run: `cd backend && python -m pytest tests/test_milestones_api.py::test_generate_tasks_idempotent -v`
Expected: FAIL（第二次调用会重新 `db.add` 生成新 id，`ids1 == ids2` 断言失败）

- [ ] **Step 3: 实现幂等 + 抽帮助函数**

改 `backend/app/api/milestones.py`，在 `generate_tasks_from_milestone` 上方加帮助函数：

```python
def _task_to_dict(t: Task) -> dict:
    """Task ORM → 生成任务返回 dict（幂等分支与新建分支共用）。"""
    return {
        "id": t.id,
        "title": t.title,
        "objective": t.objective,
        "duration": t.duration,
        "difficulty": t.difficulty,
        "status": t.status,
        "skill_name": t.skill_name,
        "project_id": t.project_id,
        "milestone_id": t.milestone_id,
    }
```

改 `generate_tasks_from_milestone` 主体（`backend/app/api/milestones.py:126-161`）：

```python
    m = db.get(Milestone, milestone_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Milestone not found")

    # 幂等：该里程碑已生成过任务 → 直接返回已有，不重复创建
    existing = (
        db.query(Task)
        .filter(Task.milestone_id == milestone_id)
        .order_by(Task.id)
        .all()
    )
    if existing:
        return ok(
            [_task_to_dict(t) for t in existing],
            message="该里程碑已生成过任务",
        )

    milestone_tasks = _decompose_milestone(m.goal, req.available_minutes)

    created = []
    for task_input in milestone_tasks:
        t = Task(
            title=task_input["title"],
            objective=task_input.get("objective"),
            duration=task_input.get("duration"),
            difficulty=task_input.get("difficulty", "beginner"),
            status="todo",
            skill_name=task_input.get("skill"),
            acceptance=task_input.get("acceptance", []),
            resources=task_input.get("resources", []),
            project_id=m.project_id,
            milestone_id=milestone_id,
        )
        db.add(t)
        db.flush()
        created.append(_task_to_dict(t))

    db.commit()
    return ok(created, message=f"Generated {len(created)} tasks from milestone")
```

（关键变化：开头插入幂等检查，末尾 `created.append({...})` 的 10 行手写 dict 替换为 `created.append(_task_to_dict(t))`。）

- [ ] **Step 4: 跑测试验证通过（GREEN）**

Run: `cd backend && python -m pytest tests/test_milestones_api.py -v`
Expected: `test_generate_tasks_idempotent` PASS + 现有 `test_generate_tasks_from_milestone` 等全部 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/milestones.py backend/tests/test_milestones_api.py
git commit -m "fix(backend): make generate_tasks idempotent (dedupe same-named tasks)"
```

---

### Task 3: 前端脚手架展示 + 按钮幂等

**Files:**
- Modify: `frontend/src/types/index.ts:135-143`（Milestone）+ 加 `RequiredModification` 接口
- Modify: `frontend/src/services/projectService.ts:22-50`
- Modify: `frontend/src/components/MilestoneTimeline.tsx`
- Modify: `frontend/src/app/projects/[id]/page.tsx:71-79`

**Interfaces:**
- Consumes: 后端 `MilestoneOut` 的 `workspace`/`required_modifications`（Task 1 产出，snake_case）；`Task.milestoneId`（现有 `taskService.ts` 已映射）
- Produces: `Milestone.workspace?: string | null`、`Milestone.requiredModifications?: RequiredModification[]`、`RequiredModification` 接口

> 本项目前端无自动化测试框架，Task 3 用「启动 + 手动验收」替代测试。后端行为已由 Task 1/2 测试覆盖，前端只做展示与 UI 状态。

- [ ] **Step 1: 扩展类型**

改 `frontend/src/types/index.ts`，在 `Milestone` 接口前加 `RequiredModification` 接口，并扩展 `Milestone`：

```typescript
export interface RequiredModification {
  title: string;
  goal: string;
  files: string[];
  verification: string;
}

export interface Milestone {
  id: string;
  projectId: string;
  version: string;
  title: string;
  goal: string;
  status: "locked" | "in_progress" | "completed";
  sortOrder: number;
  workspace?: string | null;
  requiredModifications?: RequiredModification[];
}
```

- [ ] **Step 2: 扩展 DTO 映射**

改 `frontend/src/services/projectService.ts`，`MilestoneDTO` 加两字段：

```typescript
interface MilestoneDTO {
  id: number;
  project_id: number;
  version: string;
  title: string;
  goal: string;
  status: string;
  sort_order: number;
  workspace?: string | null;
  required_modifications?: Array<{
    title: string; goal: string; files: string[]; verification: string;
  }> | null;
}
```

`toMilestone` 加两字段：

```typescript
function toMilestone(dto: MilestoneDTO): Milestone {
  return {
    id: String(dto.id),
    projectId: String(dto.project_id),
    version: dto.version,
    title: dto.title,
    goal: dto.goal,
    status: dto.status as Milestone["status"],
    sortOrder: dto.sort_order,
    workspace: dto.workspace ?? null,
    requiredModifications: dto.required_modifications ?? undefined,
  };
}
```

- [ ] **Step 3: 时间线组件按钮幂等 + 脚手架详情**

改 `frontend/src/components/MilestoneTimeline.tsx`。Props 加 `generatedMilestoneIds`，`handleGenerateTasks` 后 `router.refresh()` 会重新拉取 tasks：

```tsx
"use client";

import type { Milestone, Skill } from "@/types";
import { projectService } from "@/services/projectService";
import { useRouter } from "next/navigation";
import { useState } from "react";

const statusIcon: Record<string, string> = {
  completed: "✅",
  in_progress: "●",
  locked: "🔒",
};

const statusColor: Record<string, string> = {
  completed: "text-green-600 dark:text-green-400",
  in_progress: "text-blue-600 dark:text-blue-400",
  locked: "text-zinc-400 dark:text-zinc-500",
};

type Props = {
  milestones: Milestone[];
  projectId: string;
  skills: { name: string; level: number; target: number }[];
  generatedMilestoneIds: string[];
};

export default function MilestoneTimeline({
  milestones,
  projectId,
  skills,
  generatedMilestoneIds,
}: Props) {
  const router = useRouter();
  const [generating, setGenerating] = useState<string | null>(null);

  const handleGenerateTasks = async (milestoneId: string) => {
    setGenerating(milestoneId);
    try {
      await projectService.generateTasks(milestoneId, {
        available_minutes: 120,
        skills,
      });
      router.refresh();
    } finally {
      setGenerating(null);
    }
  };

  const handleToggleStatus = async (m: Milestone) => {
    const nextStatus =
      m.status === "locked"
        ? "in_progress"
        : m.status === "in_progress"
        ? "completed"
        : m.status === "completed"
        ? "in_progress"
        : m.status;
    await projectService.patchMilestone(m.id, { status: nextStatus });
    router.refresh();
  };

  return (
    <div className="space-y-1">
      {milestones.map((m) => {
        const hasTasks = generatedMilestoneIds.includes(m.id);
        return (
          <div
            key={m.id}
            className={`rounded-lg border p-4 ${
              m.status === "in_progress"
                ? "border-blue-200 bg-blue-50/50 dark:border-blue-900 dark:bg-blue-950/20"
                : "border-zinc-200 dark:border-zinc-800"
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => handleToggleStatus(m)}
                  className="text-lg cursor-pointer"
                  title={
                    m.status === "locked"
                      ? "解锁开始"
                      : m.status === "in_progress"
                      ? "标记完成"
                      : "重新打开"
                  }
                >
                  {statusIcon[m.status] || "⬜"}
                </button>
                <div>
                  <span
                    className={`text-sm font-medium ${statusColor[m.status] || ""}`}
                  >
                    {m.version}: {m.title}
                  </span>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                    {m.goal}
                  </p>
                </div>
              </div>
              {m.status === "in_progress" && (
                <button
                  type="button"
                  onClick={() => handleGenerateTasks(m.id)}
                  disabled={generating === m.id || hasTasks}
                  className="text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {generating === m.id
                    ? "生成中..."
                    : hasTasks
                    ? "任务已生成"
                    : "生成任务"}
                </button>
              )}
            </div>

            {/* 脚手架详情：workspace 路径 + 必改项清单 */}
            {(m.workspace || (m.requiredModifications?.length ?? 0) > 0) && (
              <div className="mt-3 border-t border-zinc-100 dark:border-zinc-800 pt-3 space-y-3">
                {m.workspace && (
                  <div className="text-xs font-mono text-zinc-600 dark:text-zinc-400">
                    📁 {m.workspace}
                  </div>
                )}
                {m.requiredModifications && m.requiredModifications.length > 0 && (
                  <ul className="space-y-2">
                    {m.requiredModifications.map((mod, i) => (
                      <li
                        key={i}
                        className="rounded-lg bg-white/60 dark:bg-zinc-900/40 p-2.5"
                      >
                        <div className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                          ✏️ 必改项 {i + 1}: {mod.title}
                        </div>
                        <div className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                          {mod.goal}
                        </div>
                        <code className="block text-[11px] font-mono text-blue-600 dark:text-blue-400 mt-1.5 bg-zinc-50 dark:bg-zinc-800 rounded px-1.5 py-1">
                          {mod.verification}
                        </code>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: 详情页传入已生成任务的 milestoneId 集合**

改 `frontend/src/app/projects/[id]/page.tsx:71-79`，给 `MilestoneTimeline` 传 `generatedMilestoneIds`：

```tsx
          <MilestoneTimeline
            milestones={project.milestones}
            projectId={id}
            skills={skills.map((s) => ({
              name: s.name,
              level: s.level,
              target: s.targetLevel,
            }))}
            generatedMilestoneIds={allTasks
              .map((t) => t.milestoneId)
              .filter((x): x is string => x != null)}
          />
```

- [ ] **Step 5: 手动验收**

启动后端（如未运行）：

```bash
cd backend && python -m uvicorn app.main:app --reload --port 8000
```

启动前端：

```bash
cd frontend && npm run dev
```

访问 `http://localhost:3000/projects/1`，确认：

1. **按钮幂等**：in_progress 里程碑首次点「生成任务」→ 生成后按钮变「任务已生成」并禁用，再点无反应（后端幂等兜底）
2. **脚手架展示**：有 `workspace`/`requiredModifications` 的里程碑（用 Task 1 的 PATCH 写入或用 Claude Code 回填后）显示 📁 路径 + 必改项清单（title + goal + verification 命令）
3. **无脚手架时**：无 `workspace`/`requiredModifications` 的里程碑不显示额外区域，界面无回归

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/services/projectService.ts \
  frontend/src/components/MilestoneTimeline.tsx "frontend/src/app/projects/[id]/page.tsx"
git commit -m "feat(frontend): show milestone scaffolding + disable regenerate button"
```

---

## 完成标准

- [x] `Milestone` 有 `workspace` + `required_modifications` 字段，可 PATCH 写入、GET 读回
- [x] `migrations/0004_milestone_scaffolding.sql` 幂等应用成功
- [x] 点「生成任务」第二次不重复创建同名任务（后端幂等，`ids1 == ids2`）
- [x] 前端里程碑卡片显示 workspace 路径 + 必改项清单（title/goal/verification）
- [x] 已生成任务的里程碑按钮变「任务已生成」并禁用
- [x] `pytest tests/test_milestone_scaffolding.py` 2/2 通过
- [x] `pytest tests/test_milestones_api.py` 全部通过（含幂等回归测试）
- [x] 全量后端测试无回归
- [x] 前端手动验收通过（按钮幂等 + 脚手架展示）
