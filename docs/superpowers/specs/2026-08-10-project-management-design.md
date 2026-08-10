# Project Management 模块设计

> 2026-08-10 · 基于 brainstorming 产出 · 项目主轨道 + 技能副轨道

---

## 一、设计理念

**项目是主轨道，技能是副产品。** 不是"缺什么技能就学什么"，而是"做项目的过程中技能自然升级"。

```
Project → Milestone → Task → GitHub Commit → Skill Level Up
```

技能不是"学"来的，技能是"做项目时顺带刷上去的"。

**核心规则：**
- 没时间做实验 ≠ 翻资料算学习。要么做项目，要么休息。
- 知识片段必须挂在 Milestone 或 Task 下，不允许独立存在。
- 只存链接 + 一句话描述，不存全文笔记。

---

## 二、数据模型

### 2.1 Project 表

```python
class Project(Base):
    __tablename__ = "projects"

    id: int                    # PK
    name: str                  # "SO101 Embodied AI System"
    goal: str                  # 项目一句话目标
    description: str | None    # 详细描述（可选）
    status: str                # active | paused | completed
    current_version: str       # "V1" / "V2" / ...
    github_url: str | None     # 仓库链接
    readme: str | None         # 自动生成的 README（Markdown）
    sort_order: int = 0        # 排序
    created_at: datetime
    updated_at: datetime
```

### 2.2 Milestone 表

```python
class Milestone(Base):
    __tablename__ = "milestones"

    id: int                    # PK
    project_id: int            # FK → projects
    version: str               # "V0" / "V1" / ... / "V6"
    title: str                 # "ROS2 基础控制"
    goal: str                  # 验收标准
    status: str                # locked | in_progress | completed
    sort_order: int            # V0=0, V1=1, ...
    created_at: datetime
    updated_at: datetime
```

### 2.3 Task 表改动

现有 Task 模型新增两个可选外键：

```python
project_id: int | None       # FK → projects
milestone_id: int | None     # FK → milestones
```

向后兼容：不传 project_id 的任务（旧 Task / 手动任务）不受影响。

### 2.4 关系

```
Project 1 ──── N Milestone 1 ──── N Task
  │                                    │
  │                              Skill.evidence
  │                              LearningLog
```

- Milestone 下所有 Task done → Milestone 可标记 done
- 所有 Milestone done → Project 可标记 done → 自动生成 README
- Task 完成后 Reviewer 自动推 evidence 到关联 Skill

---

## 三、API 设计

### 3.1 项目管理

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/projects` | 列表，含 milestone 进度汇总 |
| `POST` | `/api/projects` | 创建 |
| `GET` | `/api/projects/{id}` | 详情（milestones + 完成率） |
| `PATCH` | `/api/projects/{id}` | 更新字段 |
| `DELETE` | `/api/projects/{id}` | 级联删除 milestones |

### 3.2 里程碑管理

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/projects/{id}/milestones` | 创建 milestone |
| `PATCH` | `/api/milestones/{id}` | 更新字段 |
| `DELETE` | `/api/milestones/{id}` | 删除 |
| `POST` | `/api/milestones/{id}/tasks` | Planner 拆 milestone → tasks |

### 3.3 现有端点改动

| 端点 | 改动 |
|------|------|
| `GET /api/dashboard` | 返回新增 `projects` 字段 |
| `POST /api/planner/generate` | 支持可选 `project_id` + `milestone_id` |
| `GET /api/tasks` | 支持 `?project_id=` 过滤 |

---

## 四、前端设计

### 4.1 路由

```
/dashboard          → 修改：新增"项目进度"区域
/projects           → 新增：项目列表
/projects/[id]      → 新增：项目详情（里程碑时间线 + 任务）
```

### 4.2 Dashboard 改动

在 CareerCard 和 SkillOverview 之间插入项目进度卡片，显示活跃项目的进度条 + 当前里程碑。

### 4.3 /projects 页面

项目卡片列表，含进度条、当前版本、下一里程碑。新建项目按钮。

### 4.4 /projects/[id] 页面

里程碑时间线：
- completed → 绿色 ✅
- in_progress → 蓝色 ● 展开显示子任务
- locked → 灰色 🔒

每个里程碑内 task 列表，支持展开/折叠。"从 milestone 生成任务"按钮调 Planner。

项目底部展示关联技能（从 milestones → tasks → skill_name 聚合）。

### 4.5 组件

| 组件 | 类型 | 职责 |
|------|------|------|
| `ProjectCard` | Server | 卡片，进度条 + 里程碑概览 |
| `ProjectList` | Server | 列表容器 |
| `MilestoneTimeline` | Client | 时间线，展开/折叠 |
| `MilestoneItem` | Client | 单条里程碑行 |
| `ProjectProgress` | Client | 进度条组件 |

### 4.6 Planner 改造

传 `project_id` + `milestone_id` 时，prompt 注入项目上下文：

```
当前项目：SO101 Embodied AI System
当前里程碑：V1 ROS2 基础控制（能通过 ROS2 topic 控制 SO101 关节）
已完成任务：publisher ✅, subscriber ✅
剩余任务：launch 文件, TF2 实验
请为下一个子任务生成计划
```

---

## 五、实施范围

### 包含

- Project + Milestone 模型、API、前端
- Task 表 project_id/milestone_id 外键
- Dashboard 项目进度卡片
- Planner 项目上下文注入
- 项目 README 自动生成

### 不包含

- 独立知识库模块（知识片段走 Task.resources）
- 实验追踪（V3+ 再说）
- 刷题/题库模块
- 多用户

---

## 六、不变更的部分

- 现有 Skill / Task / Reviewer / Reminder / GitHub 感知模块保持不动
- 仅 Task 表加两个可选外键，兼容旧数据
- 前端现有组件全部保留

---

## 七、设计决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| 项目 vs 知识库优先级 | 项目优先 | 知识库会变成逃避项目的安全出口 |
| 项目管理 vs 实验追踪 | 项目管理 | 当前阶段 V0-V2 是工程搭建，实验追踪 V3+ 再说 |
| 项目完成确认 | 人工确认 | 所有 task done ≠ 项目真做完 |
| README 生成 | 项目完成时自动生成 | LLM 汇总 milestones + skills |
| 知识存储 | Task.resources 字段 | 只存链接，不建独立知识库 |
| 学习方式 | 要么做实验，要么休息 | 不存在"翻翻资料也算学习" |
