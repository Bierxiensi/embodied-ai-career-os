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

基础系统

Status:

Planning


## Phase 2

Knowledge Agent


## Phase 3

Robot AI Integration


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


## 快速启动

```bash
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
