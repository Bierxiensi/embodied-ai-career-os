# Embodied AI Career OS v1.0

## AI驱动的具身智能职业成长操作系统


## 项目定位

Embodied AI Career OS 是一个 AI Agent 驱动的个人职业成长系统。

目标：

帮助软件工程师、AI工程师完成：

传统软件开发
        ↓
AI Agent Engineer
        ↓
Robot AI Engineer


通过：

- 技能图谱
- AI学习规划
- 知识管理
- 项目管理
- 能力评估

建立个人成长闭环。


---

# 核心理念


不是：

记录学习笔记


而是：

管理能力成长。


系统回答三个问题：

1. 我距离目标岗位还有多少差距？

2. 今天应该学习什么？

3. 我的能力是否真的提升？


---

# Target


目标岗位：

Robot AI Engineer


目标能力：

- AI Agent
- Robotics
- ROS2
- Isaac
- VLA
- Robot Learning


---

# Tech Stack


## Frontend

- Next.js
- React
- TypeScript
- Tailwind


## Backend

- FastAPI
- Python
- SQLAlchemy


## AI

- LangGraph
- LLM API
- RAG


## Database

- PostgreSQL
- ChromaDB


## Deployment

- Docker Compose


---

# Project Status


## Phase 1

基础系统（Career / Skill / Task CRUD + Dashboard + 学习闭环）

Status:

Done

数据源说明：技能与职业目标的真实画像集中在
`backend/app/core/skill_profile.py` 与 `backend/app/core/target_roles.py`，
改这两个文件即可，无需改业务代码。


## Phase 2

Knowledge Agent

Status:

Week 1 完成（Multi-Agent Runtime：core / supervisor / career / research / orchestrator）


## Phase 3

Robot AI Integration

Status:

进行中（LLM Provider 骨架已就绪，默认 mock；SO101 真机 sim2real 未打通）


---

# Development Philosophy


Keep simple.

Build fast.

Use AI agents.

Avoid over engineering.


---

# Development Environment


## 前置要求

- Docker
- Docker Compose


## 快速启动（推荐：一键脚本）

```bash
bash start.sh            # 自动补 .env / 建 venv / 装依赖，并启动前后端
bash scripts/smoke.sh    # 冒烟验证：健康检查 + 核心 API + 页面可访问性
bash stop.sh             # 停止服务并释放 8000 / 3000 端口
```

数据库：本地开发默认 **SQLite**（`backend/data/app.db`，零配置）；
Docker Compose 场景由 `docker-compose.yml` 覆盖为 PostgreSQL。
`start.sh` 生成的 `.env` 直接可用，不要在没跑 Docker 的机器上填 Postgres 连接串。

首次执行会自动安装依赖（约 2-5 分钟）。启动后访问：

- Dashboard: http://localhost:3000/dashboard
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health
- 数据库检查: http://localhost:8000/health/db

日志位于 `.workbuddy/logs/backend.log` 与 `.workbuddy/logs/frontend.log`。

## Docker 方式

```bash
cp .env.example .env
docker compose up --build
```

访问：

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- 健康检查: http://localhost:8000/health


## 本地开发（不使用 Docker）

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```


## 目录结构

- `frontend/` — Next.js 前端
- `backend/` — FastAPI 后端
- `agents/` — LangGraph Agent（Phase 1 Day5 填充）
- `database/` — 数据库迁移脚本（Phase 1 Day2 填充）
- `knowledge/` — 知识库资源（Phase 2 填充）
- `deploy/` — 部署配置（后续阶段填充）
- `docs/` — 项目文档
- `scripts/` — 运维脚本（`smoke.sh` 冒烟测试）

脚本约定：`start.sh` 具备环境自愈能力（`.env` / `.venv` / `node_modules`
缺失时自动补齐），换机或新克隆仓库直接执行 `bash start.sh` 即可。
