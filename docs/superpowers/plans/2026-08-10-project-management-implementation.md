# Project Management 模块实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补上"项目主轨道"缺失模块，实现 Project → Milestone → Task → Skill Level 的完整闭环。

**Architecture:** 新增 Project + Milestone 两张表，Task 表加 project_id/milestone_id 外键，Planner 接收项目上下文生成关联任务。前端新增 /projects 列表页和 /projects/[id] 详情页（里程碑时间线）。

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic（后端），Next.js 15 + TypeScript + Tailwind（前端），pytest + TestClient（测试）

## Global Constraints

- 所有 API 响应使用 `ApiResponse[T]` 统一包装（`{success, data, message}`）
- 后端 JSON 使用 snake_case，前端类型使用 camelCase，services 层做 DTO 转换
- 后端遵循现有路由模式：`APIRouter(prefix="/xxx")`，单个端点函数，`db: Session = Depends(get_db)`
- 任务关联 project/milestone 为可选外键，**完全兼容旧任务**（project_id=None）
- 前端 Server Component 获取数据，Client Component 处理交互，router.refresh() 刷新
- 测试使用 `from fastapi.testclient import TestClient; from app.main import app`
- TDD：每个 Task 先写测试 → 确认失败 → 写实现 → 确认通过 → commit
- ML/AI 项目不做实验追踪（spec 明确排除）

---

### Task 1: Project + Milestone 数据模型

**Files:**
- Create: `backend/app/models/project.py`
- Create: `backend/app/models/milestone.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/task.py` (add FK fields)
- Modify: `backend/app/schemas/task.py` (add project_id, milestone_id to TaskOut/TaskCreate)
- Modify: `backend/app/db/base.py` (seed a demo project)
- Test: `backend/tests/test_project_models.py`

**Interfaces:**
- Consumes: `app.db.base.Base` (DeclarativeBase), existing `Task` model
- Produces: `Project` model (id, name, goal, description, status, current_version, github_url, readme, sort_order, created_at, updated_at), `Milestone` model (id, project_id FK, version, title, goal, status, sort_order, created_at, updated_at), `Task.project_id` (Integer FK nullable), `Task.milestone_id` (Integer FK nullable)

- [ ] **Step 1: Write model tests**

```python
"""Project + Milestone 模型测试。"""
from app.models.project import Project
from app.models.milestone import Milestone
from app.models.task import Task
from app.db.base import SessionLocal


def test_create_project():
    """创建项目，验证字段写入。"""
    db = SessionLocal()
    try:
        p = Project(
            name="SO101 Embodied AI",
            goal="打造 ROS2 + VLA 真机闭环",
            status="active",
            current_version="V1",
            sort_order=0,
        )
        db.add(p)
        db.commit()
        db.refresh(p)

        assert p.id is not None
        assert p.name == "SO101 Embodied AI"
        assert p.status == "active"
        assert p.current_version == "V1"
    finally:
        db.rollback()
        db.close()


def test_create_milestone():
    """创建里程碑，验证 FK 关联。"""
    db = SessionLocal()
    try:
        p = Project(name="Test Project", goal="Test", status="active",
                     current_version="V0", sort_order=0)
        db.add(p)
        db.commit()
        db.refresh(p)

        m = Milestone(
            project_id=p.id,
            version="V0",
            title="基础控制",
            goal="Python 控制舵机",
            status="in_progress",
            sort_order=0,
        )
        db.add(m)
        db.commit()
        db.refresh(m)

        assert m.id is not None
        assert m.project_id == p.id
        assert m.version == "V0"
    finally:
        db.rollback()
        db.close()


def test_task_with_project_fk():
    """Task 可选关联 Project 和 Milestone。"""
    db = SessionLocal()
    try:
        p = Project(name="P", goal="G", status="active",
                     current_version="V0", sort_order=0)
        db.add(p)
        db.commit()
        db.refresh(p)

        m = Milestone(project_id=p.id, version="V0", title="M",
                       goal="G", status="in_progress", sort_order=0)
        db.add(m)
        db.commit()
        db.refresh(m)

        t = Task(
            title="Test task",
            status="todo",
            project_id=p.id,
            milestone_id=m.id,
        )
        db.add(t)
        db.commit()
        db.refresh(t)

        assert t.project_id == p.id
        assert t.milestone_id == m.id
    finally:
        db.rollback()
        db.close()


def test_task_without_project_works():
    """旧 Task 无 project_id/milestone_id 仍正常工作。"""
    db = SessionLocal()
    try:
        t = Task(title="Old task", status="todo")
        db.add(t)
        db.commit()
        db.refresh(t)
        assert t.id is not None
        assert t.project_id is None
        assert t.milestone_id is None
    finally:
        db.rollback()
        db.close()
```

Run: `pytest backend/tests/test_project_models.py -v`
Expected: FAIL (models not defined)

- [ ] **Step 2: Create Project model**

```python
"""项目模型。对应 spec：项目是主轨道，技能是副产品。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    goal: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    current_version: Mapped[str] = mapped_column(String(20), default="V0", nullable=False)
    github_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    readme: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
```

- [ ] **Step 3: Create Milestone model**

```python
"""里程碑模型。Project 1:N Milestone，每个 Milestone 对应一个版本目标。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    goal: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="locked", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
```

- [ ] **Step 4: Update models/__init__.py**

```python
# 在现有 imports 后追加：
from app.models.project import Project  # noqa: F401
from app.models.milestone import Milestone  # noqa: F401
```

- [ ] **Step 5: Add FK fields to Task model**

In `backend/app/models/task.py`, add after `skill_id`:

```python
# V2 Project 模块：可选关联项目和里程碑
project_id: Mapped[int | None] = mapped_column(
    Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
)
milestone_id: Mapped[int | None] = mapped_column(
    Integer, ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True
)
```

- [ ] **Step 6: Update Task schemas**

In `backend/app/schemas/task.py`:

Add to `TaskOut`:
```python
project_id: int | None = None
milestone_id: int | None = None
```

Add to `TaskCreate`:
```python
project_id: int | None = None
milestone_id: int | None = None
```

- [ ] **Step 7: Add seed project data**

In `backend/app/db/base.py` `_seed_if_empty()`, add after Task seeds:

```python
# V2 Project 种子
from app.models.project import Project  # noqa: F811
from app.models.milestone import Milestone  # noqa: F811

if db.query(Project).count() == 0:
    p = Project(
        name="SO101 Embodied AI System",
        goal="打造 ROS2 + VLA 驱动的具身智能真机闭环系统",
        description="从 Python 控制 → ROS2 → MoveIt2 → ACT → SmolVLA → Isaac Lab → Sim2Real",
        status="active",
        current_version="V1",
        sort_order=0,
    )
    db.add(p)
    db.flush()

    milestones = [
        Milestone(project_id=p.id, version="V0", title="Python 基础控制",
                  goal="Python 直接控制 SO101 舵机转动", status="completed", sort_order=0),
        Milestone(project_id=p.id, version="V1", title="ROS2 基础控制",
                  goal="通过 ROS2 topic 控制 SO101 关节", status="in_progress", sort_order=1),
        Milestone(project_id=p.id, version="V2", title="MoveIt2 集成",
                  goal="MoveIt2 运动规划 + 执行", status="locked", sort_order=2),
        Milestone(project_id=p.id, version="V3", title="ACT 模仿学习",
                  goal="ACT 训练 + 泛化实验", status="locked", sort_order=3),
        Milestone(project_id=p.id, version="V4", title="SmolVLA 接入",
                  goal="SmolVLA 推理 + 真机测试", status="locked", sort_order=4),
        Milestone(project_id=p.id, version="V5", title="Isaac Lab 仿真",
                  goal="仿真环境搭建 + 合成数据生成", status="locked", sort_order=5),
        Milestone(project_id=p.id, version="V6", title="Sim2Real 闭环",
                  goal="仿真训练 → 真机部署 → 评估完整闭环", status="locked", sort_order=6),
    ]
    for m in milestones:
        db.add(m)
```

- [ ] **Step 8: Run tests**

Run: `pytest backend/tests/test_project_models.py -v`
Expected: 4/4 PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/project.py backend/app/models/milestone.py backend/app/models/__init__.py backend/app/models/task.py backend/app/schemas/task.py backend/app/db/base.py backend/tests/test_project_models.py
git commit -m "feat(db): add Project + Milestone models with Task FK"
```

---

### Task 2: Project + Milestone Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/project.py`
- Create: `backend/tests/test_project_schemas.py`

**Interfaces:**
- Consumes: `Project` ORM model (Task 1), `Milestone` ORM model (Task 1)
- Produces: `ProjectOut`, `ProjectCreate`, `ProjectPatch`, `MilestoneOut`, `MilestoneCreate`, `MilestonePatch` Pydantic models

- [ ] **Step 1: Write schema tests**

```python
"""Project + Milestone Schema 测试。"""
from app.schemas.project import (
    ProjectOut, ProjectCreate, ProjectPatch,
    MilestoneOut, MilestoneCreate, MilestonePatch,
)


def test_project_create_validation():
    """ProjectCreate 字段校验。"""
    p = ProjectCreate(name="Test", goal="Goal", status="active", current_version="V0")
    assert p.name == "Test"
    assert p.status == "active"
    # sort_order 默认 0
    assert p.sort_order == 0


def test_project_patch_partial():
    """ProjectPatch 排除未设字段。"""
    p = ProjectPatch(status="paused")
    data = p.model_dump(exclude_unset=True)
    assert data == {"status": "paused"}
    assert "name" not in data


def test_project_out_from_attributes():
    """ProjectOut 从 ORM 对象构造。"""
    from app.models.project import Project
    orm = Project(id=1, name="P", goal="G", status="active",
                   current_version="V1", sort_order=0)
    out = ProjectOut.model_validate(orm)
    assert out.id == 1
    assert out.status == "active"


def test_milestone_out():
    """MilestoneOut 基础字段。"""
    from app.models.milestone import Milestone
    orm = Milestone(id=1, project_id=1, version="V0", title="M",
                     goal="G", status="in_progress", sort_order=0)
    out = MilestoneOut.model_validate(orm)
    assert out.version == "V0"
    assert out.project_id == 1
```

Run: `pytest backend/tests/test_project_schemas.py -v`
Expected: FAIL (schemas not defined)

- [ ] **Step 2: Create schemas**

```python
"""Project + Milestone Pydantic 请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ---- Project ----

class ProjectCreate(BaseModel):
    name: str
    goal: str
    description: str | None = None
    status: str = "active"
    current_version: str = "V0"
    github_url: str | None = None
    sort_order: int = 0


class ProjectPatch(BaseModel):
    name: str | None = None
    goal: str | None = None
    description: str | None = None
    status: str | None = None
    current_version: str | None = None
    github_url: str | None = None
    sort_order: int | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    goal: str
    description: str | None = None
    status: str
    current_version: str
    github_url: str | None = None
    readme: str | None = None
    sort_order: int


# ---- Milestone ----

class MilestoneCreate(BaseModel):
    version: str
    title: str
    goal: str
    status: str = "locked"
    sort_order: int = 0


class MilestonePatch(BaseModel):
    version: str | None = None
    title: str | None = None
    goal: str | None = None
    status: str | None = None
    sort_order: int | None = None


class MilestoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    version: str
    title: str
    goal: str
    status: str
    sort_order: int
```

- [ ] **Step 3: Run tests**

Run: `pytest backend/tests/test_project_schemas.py -v`
Expected: 4/4 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/project.py backend/tests/test_project_schemas.py
git commit -m "feat(schema): add Project + Milestone Pydantic schemas"
```

---

### Task 3: Project CRUD API

**Files:**
- Create: `backend/app/api/projects.py`
- Modify: `backend/app/main.py` (register router)
- Test: `backend/tests/test_projects_api.py`

**Interfaces:**
- Consumes: `Project` ORM, `ProjectOut/Create/Patch` schemas (Task 1, 2), `ApiResponse/ok` from `app.core.response`
- Produces: `GET /api/projects`, `POST /api/projects`, `GET /api/projects/{id}`, `PATCH /api/projects/{id}`, `DELETE /api/projects/{id}`

- [ ] **Step 1: Write API tests**

```python
"""Project API 测试。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_projects():
    """GET /api/projects 返回项目列表。"""
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_create_project():
    """POST /api/projects 创建项目。"""
    resp = client.post("/api/projects", json={
        "name": "Test Project",
        "goal": "Test goal",
        "status": "active",
        "current_version": "V0",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["name"] == "Test Project"
    return data["data"]["id"]


def test_get_project():
    """GET /api/projects/{id} 返回项目详情。"""
    pid = test_create_project()
    resp = client.get(f"/api/projects/{pid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["id"] == pid
    # 应包含 milestones 字段
    assert "milestones" in data["data"]


def test_patch_project():
    """PATCH /api/projects/{id} 更新项目。"""
    pid = test_create_project()
    resp = client.patch(f"/api/projects/{pid}", json={"status": "paused"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["status"] == "paused"


def test_delete_project():
    """DELETE /api/projects/{id} 删除项目。"""
    pid = test_create_project()
    resp = client.delete(f"/api/projects/{pid}")
    assert resp.status_code == 200
    # 确认已删除
    resp = client.get(f"/api/projects/{pid}")
    assert resp.status_code == 404
```

Run: `pytest backend/tests/test_projects_api.py -v`
Expected: FAIL (endpoint not found)

- [ ] **Step 2: Create projects API**

```python
"""Project API 路由。GET 列表 + POST 创建 + GET 详情 + PATCH 更新 + DELETE 删除。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.project import Project
from app.models.milestone import Milestone
from app.schemas.project import ProjectCreate, ProjectOut, ProjectPatch, MilestoneOut

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
def list_projects(db: Session = Depends(get_db)) -> ApiResponse[list[ProjectOut]]:
    """获取全部项目，按 sort_order 排序。"""
    projects = db.query(Project).order_by(Project.sort_order).all()
    return ok([ProjectOut.model_validate(p) for p in projects])


@router.post("")
def create_project(
    payload: ProjectCreate, db: Session = Depends(get_db)
) -> ApiResponse[ProjectOut]:
    """创建项目。"""
    p = Project(
        name=payload.name,
        goal=payload.goal,
        description=payload.description,
        status=payload.status,
        current_version=payload.current_version,
        github_url=payload.github_url,
        sort_order=payload.sort_order,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return ok(ProjectOut.model_validate(p), message="Project created")


@router.get("/{project_id}")
def get_project(
    project_id: int, db: Session = Depends(get_db)
) -> ApiResponse[dict]:
    """获取项目详情，含 milestones 列表和完成率。"""
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Project not found")

    milestones = (
        db.query(Milestone)
        .filter(Milestone.project_id == project_id)
        .order_by(Milestone.sort_order)
        .all()
    )

    total = len(milestones)
    completed = sum(1 for m in milestones if m.status == "completed")
    progress_pct = round(completed / total * 100) if total > 0 else 0

    return ok({
        **ProjectOut.model_validate(p).model_dump(),
        "milestones": [MilestoneOut.model_validate(m).model_dump() for m in milestones],
        "milestone_total": total,
        "milestone_completed": completed,
        "progress_pct": progress_pct,
    })


@router.patch("/{project_id}")
def patch_project(
    project_id: int, payload: ProjectPatch, db: Session = Depends(get_db)
) -> ApiResponse[ProjectOut]:
    """更新项目字段。"""
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Project not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(p, field, value)

    db.commit()
    db.refresh(p)
    return ok(ProjectOut.model_validate(p), message="Project updated")


@router.delete("/{project_id}")
def delete_project(
    project_id: int, db: Session = Depends(get_db)
) -> ApiResponse[None]:
    """删除项目（级联删除 milestones）。"""
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(p)
    db.commit()
    return ok(message="Project deleted")
```

- [ ] **Step 3: Register router in main.py**

In `backend/app/main.py`, add:

```python
from app.api.projects import router as projects_router
# ...
app.include_router(projects_router, prefix=api_prefix)
```

- [ ] **Step 4: Run tests**

Run: `pytest backend/tests/test_projects_api.py -v`
Expected: 5/5 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/projects.py backend/app/main.py backend/tests/test_projects_api.py
git commit -m "feat(api): add Project CRUD endpoints"
```

---

### Task 4: Milestone CRUD API + 任务生成

**Files:**
- Create: `backend/app/api/milestones.py`
- Modify: `backend/app/main.py` (register router)
- Test: `backend/tests/test_milestones_api.py`

**Interfaces:**
- Consumes: `Project` ORM, `Milestone` ORM, `MilestoneOut/Create/Patch` schemas (Task 1, 2), Planner Agent (Task 5 will enhance)
- Produces: `POST /api/projects/{id}/milestones`, `PATCH /api/milestones/{id}`, `DELETE /api/milestones/{id}`, `POST /api/milestones/{id}/tasks`

- [ ] **Step 1: Write API tests**

```python
"""Milestone API 测试。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def _create_project():
    resp = client.post("/api/projects", json={
        "name": "M Test Project", "goal": "TG", "status": "active", "current_version": "V0",
    })
    return resp.json()["data"]["id"]


def test_create_milestone():
    """POST /api/projects/{id}/milestones 创建里程碑。"""
    pid = _create_project()
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V1", "title": "ROS2 Control", "goal": "topic 通信",
        "status": "in_progress", "sort_order": 1,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["title"] == "ROS2 Control"


def test_patch_milestone():
    """PATCH /api/milestones/{id} 更新里程碑。"""
    pid = _create_project()
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V1", "title": "M", "goal": "G", "status": "in_progress", "sort_order": 1,
    })
    mid = resp.json()["data"]["id"]

    resp = client.patch(f"/api/milestones/{mid}", json={"status": "completed"})
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "completed"


def test_delete_milestone():
    """DELETE /api/milestones/{id} 删除里程碑。"""
    pid = _create_project()
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V1", "title": "M", "goal": "G", "status": "in_progress", "sort_order": 1,
    })
    mid = resp.json()["data"]["id"]

    resp = client.delete(f"/api/milestones/{mid}")
    assert resp.status_code == 200
    # 确认已删除
    resp = client.get(f"/api/milestones/{mid}")
    assert resp.status_code == 404


def test_generate_tasks_from_milestone():
    """POST /api/milestones/{id}/tasks 调用 Planner 生成任务。"""
    pid = _create_project()
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V1", "title": "ROS2 基础", "goal": "topic 通信 + publisher/subscriber",
        "status": "in_progress", "sort_order": 1,
    })
    mid = resp.json()["data"]["id"]

    resp = client.post(f"/api/milestones/{mid}/tasks", json={
        "available_minutes": 120,
        "skills": [
            {"name": "ROS2", "level": 1, "target": 4},
            {"name": "Python", "level": 4, "target": 5},
        ],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    # 应返回生成的任务列表
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0
```

Run: `pytest backend/tests/test_milestones_api.py -v`
Expected: FAIL (endpoint not found)

- [ ] **Step 2: Create milestones API**

```python
"""Milestone API 路由。CRUD + 从 milestone 生成关联任务。"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.planner.graph import build_planner_graph
from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.agent_run import AgentRun
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.task import Task
from app.schemas.project import MilestoneCreate, MilestoneOut, MilestonePatch

router = APIRouter(tags=["milestones"])
_planner = build_planner_graph()


# ---- Milestone CRUD ----

@router.post("/projects/{project_id}/milestones")
def create_milestone(
    project_id: int,
    payload: MilestoneCreate,
    db: Session = Depends(get_db),
) -> ApiResponse[MilestoneOut]:
    """在项目下创建里程碑。"""
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Project not found")

    m = Milestone(
        project_id=project_id,
        version=payload.version,
        title=payload.title,
        goal=payload.goal,
        status=payload.status,
        sort_order=payload.sort_order,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return ok(MilestoneOut.model_validate(m), message="Milestone created")


@router.patch("/milestones/{milestone_id}")
def patch_milestone(
    milestone_id: int,
    payload: MilestonePatch,
    db: Session = Depends(get_db),
) -> ApiResponse[MilestoneOut]:
    """更新里程碑。自动传播完成状态：若里程碑标记 completed，可解锁下一个 locked 里程碑。"""
    m = db.get(Milestone, milestone_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Milestone not found")

    old_status = m.status
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(m, field, value)

    # 自动传播：completed → 解锁下一个 locked 里程碑
    if "status" in payload.model_dump(exclude_unset=True) and payload.status == "completed" and old_status != "completed":
        next_m = (
            db.query(Milestone)
            .filter(
                Milestone.project_id == m.project_id,
                Milestone.sort_order > m.sort_order,
                Milestone.status == "locked",
            )
            .order_by(Milestone.sort_order)
            .first()
        )
        if next_m:
            next_m.status = "in_progress"
            # 同步更新 project.current_version
            project = db.get(Project, m.project_id)
            if project:
                project.current_version = next_m.version

    db.commit()
    db.refresh(m)
    return ok(MilestoneOut.model_validate(m), message="Milestone updated")


@router.delete("/milestones/{milestone_id}")
def delete_milestone(
    milestone_id: int, db: Session = Depends(get_db)
) -> ApiResponse[None]:
    """删除里程碑。"""
    m = db.get(Milestone, milestone_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Milestone not found")

    db.delete(m)
    db.commit()
    return ok(message="Milestone deleted")


# ---- 从里程碑生成任务 ----

class SkillIn(BaseModel):
    name: str
    level: int = Field(ge=0, le=5)
    target: int = Field(ge=0, le=5)


class GenerateTasksRequest(BaseModel):
    available_minutes: int = Field(default=120, ge=5, le=480)
    skills: list[SkillIn]
    generator: str = "rule"


@router.post("/milestones/{milestone_id}/tasks")
def generate_tasks_from_milestone(
    milestone_id: int,
    req: GenerateTasksRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[list[dict]]:
    """从里程碑调用 Planner 拆解生成任务。
    
    按里程碑 goal 拆 2-5 个子任务，每个任务自动关联 project_id + milestone_id。
    """
    m = db.get(Milestone, milestone_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Milestone not found")

    # 根据里程碑 goal 拆分任务
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
        created.append({
            "id": t.id,
            "title": t.title,
            "objective": t.objective,
            "duration": t.duration,
            "difficulty": t.difficulty,
            "status": t.status,
            "skill_name": t.skill_name,
            "project_id": t.project_id,
            "milestone_id": t.milestone_id,
        })

    db.commit()
    return ok(created, message=f"Generated {len(created)} tasks from milestone")


def _decompose_milestone(goal: str, available_minutes: int) -> list[dict]:
    """将里程碑 goal 拆解为 2-5 个子任务。"""
    # 基于关键词拆解，后续 LLM 替代
    if "topic" in goal.lower() or "ros2" in goal.lower():
        tasks = [
            {"title": f"{goal} - Publisher 节点", "objective": "创建 publisher 发布数据",
             "duration": min(40, available_minutes // 3), "difficulty": "beginner",
             "skill": "ROS2"},
            {"title": f"{goal} - Subscriber 节点", "objective": "创建 subscriber 接收数据",
             "duration": min(40, available_minutes // 3), "difficulty": "beginner",
             "skill": "ROS2"},
            {"title": f"{goal} - Launch 文件", "objective": "创建 launch 文件启动多节点",
             "duration": min(30, available_minutes // 4), "difficulty": "beginner",
             "skill": "ROS2"},
        ]
    elif "moveit" in goal.lower():
        tasks = [
            {"title": f"{goal} - URDF 建模", "objective": "创建 SO101 URDF 模型",
             "duration": min(45, available_minutes // 3), "difficulty": "intermediate",
             "skill": "ROS2"},
            {"title": f"{goal} - MoveIt 配置", "objective": "配置 MoveIt2 运动规划",
             "duration": min(45, available_minutes // 3), "difficulty": "intermediate",
             "skill": "ROS2"},
            {"title": f"{goal} - 真机执行", "objective": "MoveIt 规划 → SO101 执行",
             "duration": min(30, available_minutes // 4), "difficulty": "intermediate",
             "skill": "ROS2"},
        ]
    else:
        per_task = max(20, available_minutes // 3)
        tasks = [
            {"title": f"{goal} - 第1步", "objective": goal,
             "duration": per_task, "difficulty": "beginner"},
            {"title": f"{goal} - 第2步", "objective": goal,
             "duration": per_task, "difficulty": "beginner"},
        ]
    return tasks
```

- [ ] **Step 3: Register milestones router in main.py**

```python
from app.api.milestones import router as milestones_router
# ...
app.include_router(milestones_router, prefix=api_prefix)
```

- [ ] **Step 4: Run tests**

Run: `pytest backend/tests/test_milestones_api.py -v`
Expected: 4/4 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/milestones.py backend/app/main.py backend/tests/test_milestones_api.py
git commit -m "feat(api): add Milestone CRUD + task generation endpoints"
```

---

### Task 5: Task API 扩展 + Dashboard 聚合

**Files:**
- Modify: `backend/app/api/tasks.py` (filter by project_id)
- Modify: `backend/app/services/dashboard.py` (NEW — extract dashboard aggregation from frontend calls)
- Modify: `backend/app/main.py` (register dashboard endpoint, or modify existing)
- Test: `backend/tests/test_dashboard_projects.py`

**Interfaces:**
- Consumes: Project/Milestone/Task ORM, GET /api/tasks existing
- Produces: `GET /api/tasks?project_id=` query param, `GET /api/dashboard` returns `projects` field

- [ ] **Step 1: Write tests**

```python
"""Dashboard 项目聚合测试。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_tasks_filter_by_project():
    """GET /api/tasks?project_id= 过滤项目关联任务。"""
    # 创建项目
    resp = client.post("/api/projects", json={
        "name": "Filter Test", "goal": "G", "status": "active", "current_version": "V0",
    })
    pid = resp.json()["data"]["id"]
    
    # 创建里程碑
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V0", "title": "M", "goal": "G", "status": "in_progress", "sort_order": 0,
    })
    mid = resp.json()["data"]["id"]
    
    # 从里程碑生成任务
    resp = client.post(f"/api/milestones/{mid}/tasks", json={
        "available_minutes": 60,
        "skills": [{"name": "Python", "level": 4, "target": 5}],
    })
    assert resp.status_code == 200
    
    # 按 project_id 过滤
    resp = client.get(f"/api/tasks?project_id={pid}")
    assert resp.status_code == 200
    tasks = resp.json()["data"]
    for t in tasks:
        assert t.get("project_id") == pid or t.get("project_id") is None


def test_dashboard_includes_projects():
    """GET /api/dashboard 返回中包含 projects 字段。"""
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    # 新字段 projects
    assert "projects" in data["data"]
    projects = data["data"]["projects"]
    assert isinstance(projects, list)
    # 每个项目应有进度信息
    if projects:
        p = projects[0]
        assert "progress_pct" in p
        assert "milestone_total" in p
```

Run: `pytest backend/tests/test_dashboard_projects.py -v`
Expected: FAIL (endpoints not modified yet)

- [ ] **Step 2: Add project_id filter to tasks API**

In `backend/app/api/tasks.py`, modify `list_tasks`:

```python
@router.get("")
def list_tasks(
    project_id: int | None = None,
    db: Session = Depends(get_db),
) -> ApiResponse[list[TaskOut]]:
    """获取任务列表。支持按项目过滤。"""
    q = db.query(Task)
    if project_id is not None:
        q = q.filter(Task.project_id == project_id)
    tasks = q.order_by(Task.created_at.desc()).all()
    return ok([TaskOut.model_validate(t) for t in tasks])
```

- [ ] **Step 3: Create dashboard aggregation endpoint**

Create `backend/app/api/dashboard.py`:

```python
"""Dashboard 聚合端点。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.career import Career
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.skill import Skill
from app.models.task import Task
from app.schemas.project import MilestoneOut, ProjectOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(db: Session = Depends(get_db)) -> ApiResponse[dict]:
    """聚合 Dashboard 所需全部数据。"""
    # Projects
    projects = db.query(Project).order_by(Project.sort_order).all()
    projects_data = []
    for p in projects:
        milestones = (
            db.query(Milestone)
            .filter(Milestone.project_id == p.id)
            .order_by(Milestone.sort_order)
            .all()
        )
        total = len(milestones)
        completed = sum(1 for m in milestones if m.status == "completed")
        progress_pct = round(completed / total * 100) if total > 0 else 0

        projects_data.append({
            **ProjectOut.model_validate(p).model_dump(),
            "milestones": [MilestoneOut.model_validate(m).model_dump() for m in milestones],
            "milestone_total": total,
            "milestone_completed": completed,
            "progress_pct": progress_pct,
        })

    return ok({
        "projects": projects_data,
    })
```

- [ ] **Step 4: Register dashboard router**

In `backend/app/main.py`:

```python
from app.api.dashboard import router as dashboard_router
# ...
app.include_router(dashboard_router, prefix=api_prefix)
```

- [ ] **Step 5: Run tests**

Run: `pytest backend/tests/test_dashboard_projects.py -v`
Expected: 2/2 PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/tasks.py backend/app/api/dashboard.py backend/app/main.py backend/tests/test_dashboard_projects.py
git commit -m "feat(api): add task project filter + dashboard project aggregation"
```

---

### Task 6: Planner 项目上下文注入

**Files:**
- Modify: `backend/app/agents/planner/state.py` (add project_context, project_id, milestone_id)
- Modify: `backend/app/api/planner.py` (accept + pass project context)
- Modify: `backend/app/agents/planner/generators/llm_generator.py` (inject project context into prompt)
- Test: `backend/tests/test_planner_project_context.py`

**Interfaces:**
- Consumes: PlannerState, PlannerRequest, LLMGenerator
- Produces: Enhanced PlannerRequest with optional project_id/milestone_id, LLM prompt with project context

- [ ] **Step 1: Write test**

```python
"""Planner 项目上下文测试。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_planner_with_project_context():
    """Planner 接收 project_id + milestone_id 生成任务。"""
    # 创建项目 + 里程碑
    resp = client.post("/api/projects", json={
        "name": "Planner Test", "goal": "Test", "status": "active", "current_version": "V0",
    })
    pid = resp.json()["data"]["id"]
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V0", "title": "ROS2", "goal": "topic 通信",
        "status": "in_progress", "sort_order": 0,
    })
    mid = resp.json()["data"]["id"]

    # Planner 带 project 上下文
    resp = client.post("/api/planner/generate", json={
        "available_minutes": 40,
        "skills": [{"name": "ROS2", "level": 1, "target": 4}],
        "generator": "rule",
        "persist": True,
        "project_id": pid,
        "milestone_id": mid,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    task = data["data"]
    assert task["title"]  # 应有内容


def test_planner_without_project_context():
    """Planner 无 project 上下文仍正常工作（兼容旧调用）。"""
    resp = client.post("/api/planner/generate", json={
        "available_minutes": 30,
        "skills": [{"name": "Python", "level": 4, "target": 5}],
        "generator": "rule",
        "persist": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["title"]
```

Run: `pytest backend/tests/test_planner_project_context.py -v`
Expected: FAIL (project_id not yet accepted)

- [ ] **Step 2: Add project_context to PlannerState**

In `backend/app/agents/planner/state.py`, add to `PlannerState`:

```python
# ===== V2 Project 上下文 =====
project_id: int | None       # 关联项目 ID
milestone_id: int | None     # 关联里程碑 ID
project_context: str         # 项目上下文文本（注入 prompt）
```

- [ ] **Step 3: Update PlannerRequest**

In `backend/app/api/planner.py`, add to `PlannerRequest`:

```python
project_id: int | None = Field(default=None)
milestone_id: int | None = Field(default=None)
```

Add to the `state` dict in `generate_task`:

```python
"project_id": req.project_id,
"milestone_id": req.milestone_id,
```

Add project context resolution before invoking planner:

```python
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
                # 查询已完成任务
                done_tasks = (
                    db.query(Task)
                    .filter(Task.milestone_id == req.milestone_id, Task.status == "done")
                    .all()
                )
                if done_tasks:
                    project_context += "已完成："
                    project_context += "、".join(t.title for t in done_tasks)

state["project_context"] = project_context
```

Update Task persistence to include project_id/milestone_id:

```python
if req.persist and task_data:
    new_task = Task(
        # ... existing fields ...
        project_id=req.project_id,
        milestone_id=req.milestone_id,
    )
```

- [ ] **Step 4: Inject project context in LLM generator**

In `backend/app/agents/planner/generators/llm_generator.py`, in the `_build_prompt` method, add before the existing prompt:

```python
# V2: 注入项目上下文
project_context = state.get("project_context", "")
if project_context:
    parts.insert(0, f"你正在帮助用户完成以下项目：\n{project_context}")
```

- [ ] **Step 5: Run tests**

Run: `pytest backend/tests/test_planner_project_context.py -v`
Expected: 2/2 PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/planner/state.py backend/app/api/planner.py backend/app/agents/planner/generators/llm_generator.py backend/tests/test_planner_project_context.py
git commit -m "feat(planner): add project context injection for milestone-aware task generation"
```

---

### Task 7: Frontend Types + Services

**Files:**
- Modify: `frontend/src/types/index.ts` (add Project, Milestone interfaces)
- Create: `frontend/src/services/projectService.ts`
- Modify: `frontend/src/services/dashboardService.ts` (add projects to DashboardData)

**Interfaces:**
- Consumes: GET/POST/PATCH/DELETE /api/projects, GET /api/dashboard
- Produces: `Project`, `Milestone` TypeScript interfaces, `projectService` object, updated `DashboardData` with projects

- [ ] **Step 1: Add types**

In `frontend/src/types/index.ts`, add after `CommitSuggestion`:

```typescript
// ===== V2: Project Management =====

export interface Milestone {
  id: string;
  projectId: string;
  version: string;
  title: string;
  goal: string;
  status: "locked" | "in_progress" | "completed";
  sortOrder: number;
}

export interface Project {
  id: string;
  name: string;
  goal: string;
  description: string | null;
  status: "active" | "paused" | "completed";
  currentVersion: string;
  githubUrl: string | null;
  readme: string | null;
  sortOrder: number;
  milestones: Milestone[];
  milestoneTotal: number;
  milestoneCompleted: number;
  progressPct: number;
}
```

- [ ] **Step 2: Create projectService**

```typescript
/** 项目服务层。 */

import { apiClient } from "@/lib/apiClient";
import type { Milestone, Project } from "@/types";

/** 后端 Project 响应（snake_case）。 */
interface ProjectDTO {
  id: number;
  name: string;
  goal: string;
  description: string | null;
  status: string;
  current_version: string;
  github_url: string | null;
  readme: string | null;
  sort_order: number;
  milestones?: MilestoneDTO[];
  milestone_total?: number;
  milestone_completed?: number;
  progress_pct?: number;
}

interface MilestoneDTO {
  id: number;
  project_id: number;
  version: string;
  title: string;
  goal: string;
  status: string;
  sort_order: number;
}

interface MilestoneCreateDTO {
  version: string;
  title: string;
  goal: string;
  status: string;
  sort_order: number;
}

function toProject(dto: ProjectDTO): Project {
  return {
    id: String(dto.id),
    name: dto.name,
    goal: dto.goal,
    description: dto.description,
    status: dto.status as Project["status"],
    currentVersion: dto.current_version,
    githubUrl: dto.github_url,
    readme: dto.readme,
    sortOrder: dto.sort_order,
    milestones: (dto.milestones || []).map(toMilestone),
    milestoneTotal: dto.milestone_total || 0,
    milestoneCompleted: dto.milestone_completed || 0,
    progressPct: dto.progress_pct || 0,
  };
}

function toMilestone(dto: MilestoneDTO): Milestone {
  return {
    id: String(dto.id),
    projectId: String(dto.project_id),
    version: dto.version,
    title: dto.title,
    goal: dto.goal,
    status: dto.status as Milestone["status"],
    sortOrder: dto.sort_order,
  };
}

export const projectService = {
  list: async (): Promise<Project[]> => {
    const dtos = await apiClient.get<ProjectDTO[]>("/api/projects");
    return dtos.map(toProject);
  },

  get: async (id: string): Promise<Project> => {
    const dto = await apiClient.get<ProjectDTO>(`/api/projects/${id}`);
    return toProject(dto);
  },

  create: async (data: {
    name: string; goal: string; status?: string;
    current_version?: string; description?: string; github_url?: string;
  }): Promise<Project> => {
    const dto = await apiClient.post<ProjectDTO>("/api/projects", data);
    return toProject(dto);
  },

  patch: async (id: string, data: Record<string, unknown>): Promise<Project> => {
    const dto = await apiClient.patch<ProjectDTO>(`/api/projects/${id}`, data);
    return toProject(dto);
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete<null>(`/api/projects/${id}`);
  },

  createMilestone: async (projectId: string, data: MilestoneCreateDTO): Promise<Milestone> => {
    const dto = await apiClient.post<MilestoneDTO>(
      `/api/projects/${projectId}/milestones`, data
    );
    return toMilestone(dto);
  },

  patchMilestone: async (id: string, data: Record<string, unknown>): Promise<Milestone> => {
    const dto = await apiClient.patch<MilestoneDTO>(`/api/milestones/${id}`, data);
    return toMilestone(dto);
  },

  deleteMilestone: async (id: string): Promise<void> => {
    await apiClient.delete<null>(`/api/milestones/${id}`);
  },

  generateTasks: async (milestoneId: string, data: {
    available_minutes: number;
    skills: Array<{ name: string; level: number; target: number }>;
  }): Promise<unknown[]> => {
    return apiClient.post(`/api/milestones/${milestoneId}/tasks`, data);
  },
};
```

Note: `apiClient.delete` is not in the current apiClient. Add it in Step 3.

- [ ] **Step 3: Add delete method to apiClient**

In `frontend/src/lib/apiClient.ts`, add to `apiClient`:

```typescript
delete: <T>(url: string) =>
  request<T>(url, { method: "DELETE" }),
```

- [ ] **Step 4: Update DashboardData**

In `frontend/src/services/dashboardService.ts`, add import:

```typescript
import type { Project } from "@/types";
import { projectService } from "./projectService";
```

Add `projects` to `DashboardData`:

```typescript
export interface DashboardData {
  // ... existing fields ...
  projects: Project[];
}
```

Update `getDashboardData`:

```typescript
const [career, skills, tasks, agentActivity, projects] = await Promise.all([
  getCareer(),
  getSkills(),
  getTasks(),
  getAgentRuns(undefined, 10),
  projectService.list(),
]);

return {
  // ... existing fields ...
  projects,
};
```

Update `Dashboard` component props to accept `projects`:

```typescript
type Props = {
  // ... existing ...
  projects: Project[];
};
```

Update the page.tsx to pass `projects`:

```typescript
<Dashboard
  // ... existing props ...
  projects={data.projects}
/>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/services/projectService.ts frontend/src/lib/apiClient.ts frontend/src/services/dashboardService.ts frontend/src/components/Dashboard.tsx frontend/src/app/dashboard/page.tsx
git commit -m "feat(frontend): add Project types, service, and dashboard integration"
```

---

### Task 8: Frontend Pages + Components

**Files:**
- Create: `frontend/src/components/ProjectProgress.tsx`
- Create: `frontend/src/components/ProjectCard.tsx`
- Create: `frontend/src/components/MilestoneTimeline.tsx`
- Create: `frontend/src/app/projects/page.tsx`
- Create: `frontend/src/app/projects/[id]/page.tsx`
- Modify: `frontend/src/components/Dashboard.tsx` (render ProjectProgress)

**Interfaces:**
- Consumes: `Project`, `Milestone` types, `projectService`
- Produces: `/projects` list page, `/projects/[id]` detail page, Dashboard project progress section

- [ ] **Step 1: Create ProjectProgress (Dashboard card)**

```typescript
// frontend/src/components/ProjectProgress.tsx
"use client";

import type { Project } from "@/types";
import Link from "next/link";

export default function ProjectProgress({ projects }: { projects: Project[] }) {
  if (projects.length === 0) return null;

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
          项目进度
        </h2>
        <Link
          href="/projects"
          className="text-xs text-blue-600 hover:underline dark:text-blue-400"
        >
          查看全部 →
        </Link>
      </div>
      <div className="space-y-3">
        {projects.slice(0, 2).map((p) => (
          <Link
            key={p.id}
            href={`/projects/${p.id}`}
            className="block rounded-xl border border-zinc-200 bg-white p-4 hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-950 dark:hover:border-zinc-700 transition-colors"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {p.name}
              </span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${
                  p.status === "active"
                    ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                    : p.status === "paused"
                    ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                    : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
                }`}
              >
                {p.status === "active" ? "进行中" : p.status === "paused" ? "已暂停" : "已完成"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all"
                  style={{ width: `${p.progressPct}%` }}
                />
              </div>
              <span className="text-xs text-zinc-500 dark:text-zinc-400 min-w-[3ch] text-right">
                {p.progressPct}%
              </span>
            </div>
            <p className="mt-1.5 text-xs text-zinc-500 dark:text-zinc-400">
              {p.currentVersion}:{" "}
              {p.milestones.find((m) => m.status === "in_progress")?.title ||
                p.milestones.find((m) => m.status === "locked")?.title ||
                "全部完成"}
            </p>
          </Link>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Create ProjectCard**

```typescript
// frontend/src/components/ProjectCard.tsx
import type { Project } from "@/types";
import Link from "next/link";

const statusLabel: Record<string, string> = {
  active: "进行中",
  paused: "已暂停",
  completed: "已完成",
};

export default function ProjectCard({ project }: { project: Project }) {
  return (
    <Link
      href={`/projects/${project.id}`}
      className="block rounded-2xl border border-zinc-200 bg-white p-6 hover:shadow-md transition-shadow dark:border-zinc-800 dark:bg-zinc-950"
    >
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            {project.name}
          </h3>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            {project.goal}
          </p>
        </div>
        <span className="text-xs px-2 py-1 rounded-full bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
          {statusLabel[project.status] || project.status}
        </span>
      </div>

      <div className="mt-4 flex items-center gap-2">
        <div className="flex-1 h-2 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 rounded-full transition-all"
            style={{ width: `${project.progressPct}%` }}
          />
        </div>
        <span className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
          {project.progressPct}%
        </span>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {project.milestones.slice(0, 6).map((m) => (
          <span
            key={m.id}
            className={`text-xs px-1.5 py-0.5 rounded ${
              m.status === "completed"
                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                : m.status === "in_progress"
                ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                : "bg-zinc-100 text-zinc-400 dark:bg-zinc-800 dark:text-zinc-500"
            }`}
          >
            {m.version}
          </m>
        ))}
      </div>
    </Link>
  );
}
```

- [ ] **Step 3: Create /projects list page**

```typescript
// frontend/src/app/projects/page.tsx
import ProjectCard from "@/components/ProjectCard";
import { projectService } from "@/services/projectService";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function ProjectsPage() {
  const projects = await projectService.list();

  return (
    <main className="min-h-full bg-zinc-50 dark:bg-black">
      <div className="mx-auto max-w-3xl px-6 py-10">
        <header className="mb-8 flex items-center justify-between">
          <div>
            <Link
              href="/dashboard"
              className="text-xs text-zinc-400 hover:text-zinc-600 dark:text-zinc-600 dark:hover:text-zinc-400"
            >
              ← Dashboard
            </Link>
            <h1 className="mt-1 text-2xl font-bold text-zinc-900 dark:text-zinc-100">
              项目实践
            </h1>
          </div>
        </header>

        {projects.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-zinc-300 p-12 text-center dark:border-zinc-700">
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              还没有项目。在 plane.md 中定义你的 SO101 路线，然后来这里创建第一个项目。
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {projects.map((p) => (
              <ProjectCard key={p.id} project={p} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
```

- [ ] **Step 4: Create MilestoneTimeline component**

```typescript
// frontend/src/components/MilestoneTimeline.tsx
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

export default function MilestoneTimeline({
  milestones,
  projectId,
  skills,
}: {
  milestones: Milestone[];
  projectId: string;
  skills: { name: string; level: number; target: number }[];
}) {
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
      m.status === "in_progress" ? "completed" : m.status === "completed" ? "in_progress" : m.status;
    await projectService.patchMilestone(m.id, { status: nextStatus });
    router.refresh();
  };

  return (
    <div className="space-y-1">
      {milestones.map((m) => (
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
                onClick={() => handleToggleStatus(m)}
                className="text-lg cursor-pointer"
                title={m.status === "in_progress" ? "标记完成" : "标记进行中"}
              >
                {statusIcon[m.status] || "⬜"}
              </button>
              <div>
                <span className={`text-sm font-medium ${statusColor[m.status] || ""}`}>
                  {m.version}: {m.title}
                </span>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                  {m.goal}
                </p>
              </div>
            </div>
            {m.status === "in_progress" && (
              <button
                onClick={() => handleGenerateTasks(m.id)}
                disabled={generating === m.id}
                className="text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {generating === m.id ? "生成中..." : "生成任务"}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Create /projects/[id] detail page**

```typescript
// frontend/src/app/projects/[id]/page.tsx
import MilestoneTimeline from "@/components/MilestoneTimeline";
import { projectService } from "@/services/projectService";
import { getSkills } from "@/services/skillService";
import { getTasks } from "@/services/taskService";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [project, skills, allTasks] = await Promise.all([
    projectService.get(id),
    getSkills(),
    getTasks(),
  ]);

  const projectTasks = allTasks.filter((t) => t.projectId === id);

  return (
    <main className="min-h-full bg-zinc-50 dark:bg-black">
      <div className="mx-auto max-w-3xl px-6 py-10">
        <header className="mb-8">
          <Link
            href="/projects"
            className="text-xs text-zinc-400 hover:text-zinc-600 dark:text-zinc-600 dark:hover:text-zinc-400"
          >
            ← 项目列表
          </Link>
          <div className="mt-2 flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                {project.name}
              </h1>
              <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                {project.goal}
              </p>
            </div>
            <span
              className={`text-xs px-2 py-1 rounded-full ${
                project.status === "active"
                  ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                  : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
              }`}
            >
              {project.status === "active" ? "进行中" : project.status}
            </span>
          </div>

          {/* 进度条 */}
          <div className="mt-4 flex items-center gap-3">
            <div className="flex-1 h-2 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all"
                style={{ width: `${project.progressPct}%` }}
              />
            </div>
            <span className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
              {project.progressPct}% ({project.milestoneCompleted}/{project.milestoneTotal})
            </span>
          </div>
        </header>

        {/* 里程碑时间线 */}
        <section>
          <h2 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200 mb-4">
            里程碑
          </h2>
          <MilestoneTimeline
            milestones={project.milestones}
            projectId={id}
            skills={skills.map((s) => ({ name: s.name, level: s.level, target: s.targetLevel }))}
          />
        </section>

        {/* 关联任务 */}
        {projectTasks.length > 0 && (
          <section className="mt-8">
            <h2 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200 mb-3">
              关联任务
            </h2>
            <div className="space-y-2">
              {projectTasks.map((t) => (
                <div
                  key={t.id}
                  className="flex items-center gap-3 rounded-lg border border-zinc-200 p-3 dark:border-zinc-800"
                >
                  <span
                    className={`text-xs px-1.5 py-0.5 rounded ${
                      t.status === "done"
                        ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                        : t.status === "doing"
                        ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                        : "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
                    }`}
                  >
                    {t.status === "done" ? "✓" : t.status === "doing" ? "●" : "○"}
                  </span>
                  <span className="text-sm text-zinc-700 dark:text-zinc-300">
                    {t.title}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
```

- [ ] **Step 6: Add ProjectProgress to Dashboard**

In `frontend/src/components/Dashboard.tsx`, add import and render after CareerCard:

```typescript
import ProjectProgress from "./ProjectProgress";

// In the JSX, after <CareerCard career={career} />:
<CareerCard career={career} />

{/* V2: 项目进度卡片 */}
<div className="mt-6">
  <ProjectProgress projects={projects} />
</div>
```

The `projects` prop was already added to the Props type in Task 7 Step 4.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ProjectProgress.tsx frontend/src/components/ProjectCard.tsx frontend/src/components/MilestoneTimeline.tsx frontend/src/app/projects/page.tsx frontend/src/app/projects/ frontend/src/components/Dashboard.tsx
git commit -m "feat(frontend): add Project pages, timeline, and Dashboard integration"
```

---

### Task 9: E2E Integration Test

**Files:**
- Create: `backend/tests/test_e2e_project_workflow.py`

- [ ] **Step 1: Write E2E test**

```python
"""Project Management E2E 测试：项目创建 → 里程碑 → 生成任务 → 完成任务 → 技能升级。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_full_project_workflow():
    """完整项目工作流：创建项目 → 创建里程碑 → 生成任务 → 验证关联。"""
    # 1. 创建项目
    resp = client.post("/api/projects", json={
        "name": "E2E SO101",
        "goal": "端到端测试项目",
        "status": "active",
        "current_version": "V0",
    })
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    # 2. 创建里程碑
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V0", "title": "基础控制",
        "goal": "Python 控制舵机", "status": "in_progress", "sort_order": 0,
    })
    assert resp.status_code == 200
    mid = resp.json()["data"]["id"]

    # 3. 从里程碑生成任务
    resp = client.post(f"/api/milestones/{mid}/tasks", json={
        "available_minutes": 60,
        "skills": [
            {"name": "Python", "level": 4, "target": 5},
            {"name": "ROS2", "level": 1, "target": 4},
        ],
    })
    assert resp.status_code == 200
    tasks = resp.json()["data"]
    assert len(tasks) > 0

    # 4. 验证任务关联了项目和里程碑
    task_id = tasks[0]["id"]
    resp = client.get(f"/api/tasks?project_id={pid}")
    assert resp.status_code == 200
    project_tasks = resp.json()["data"]
    task_ids = [t["id"] for t in project_tasks]
    assert task_id in task_ids

    # 5. 完成一个任务
    resp = client.patch(f"/api/tasks/{task_id}/status", json={"status": "done"})
    assert resp.status_code == 200

    # 6. 验证里程碑完成
    resp = client.patch(f"/api/milestones/{mid}", json={"status": "completed"})
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "completed"


def test_project_in_dashboard():
    """Dashboard 返回项目数据。"""
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "projects" in data
    assert isinstance(data["projects"], list)
```

Run: `pytest backend/tests/test_e2e_project_workflow.py -v`
Expected: 2/2 PASS

- [ ] **Step 2: Commit**

```bash
git add backend/tests/test_e2e_project_workflow.py
git commit -m "test(e2e): add project workflow end-to-end test"
```

---

### Task 10: README 自动生成（项目完成时）

**Files:**
- Modify: `backend/app/api/projects.py` (on status→completed, generate README)
- Test: `backend/tests/test_project_readme.py`

- [ ] **Step 1: Write test**

```python
"""Project README 自动生成测试。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_readme_generated_on_completion():
    """项目标记 completed 时自动生成 README。"""
    # 创建项目并完成所有里程碑
    resp = client.post("/api/projects", json={
        "name": "README Test", "goal": "Test README gen",
        "status": "active", "current_version": "V0",
    })
    pid = resp.json()["data"]["id"]

    # 创建并完成一个里程碑
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V0", "title": "唯一里程碑",
        "goal": "完成测试", "status": "in_progress", "sort_order": 0,
    })
    mid = resp.json()["data"]["id"]
    client.patch(f"/api/milestones/{mid}", json={"status": "completed"})

    # 标记项目完成
    resp = client.patch(f"/api/projects/{pid}", json={"status": "completed"})
    assert resp.status_code == 200
    data = resp.json()["data"]

    # 应自动生成 README
    assert data["readme"] is not None
    assert len(data["readme"]) > 0
    assert "README Test" in data["readme"]
```

Run: `pytest backend/tests/test_project_readme.py -v`
Expected: FAIL (README generation not yet implemented)

- [ ] **Step 2: Add README generation to patch_project**

In `backend/app/api/projects.py`, add after `patch_project` field updates:

```python
# 项目标记完成时自动生成 README
if "status" in payload.model_dump(exclude_unset=True) and payload.status == "completed":
    import json
    from app.models.milestone import Milestone

    milestones = (
        db.query(Milestone)
        .filter(Milestone.project_id == project_id)
        .order_by(Milestone.sort_order)
        .all()
    )

    # 收集关联技能
    skills_set: set[str] = set()
    for m in milestones:
        tasks = db.query(Task).filter(Task.milestone_id == m.id).all()
        for t in tasks:
            if t.skill_name:
                skills_set.add(t.skill_name)

    # 构建 README
    lines = [
        f"# {p.name}",
        "",
        f"> {p.goal}",
        "",
        "## 里程碑",
        "",
    ]
    for m in milestones:
        status_icon = "✅" if m.status == "completed" else "⬜"
        lines.append(f"- {status_icon} **{m.version}**: {m.title} — {m.goal}")

    lines.extend([
        "",
        "## 涉及技能",
        "",
    ])
    for skill in sorted(skills_set):
        lines.append(f"- {skill}")

    lines.extend([
        "",
        "---",
        f"*由 Embodied AI Career OS 自动生成*",
    ])

    p.readme = "\n".join(lines)
```

- [ ] **Step 3: Run tests**

Run: `pytest backend/tests/test_project_readme.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/projects.py backend/tests/test_project_readme.py
git commit -m "feat(project): auto-generate README on project completion"
```
