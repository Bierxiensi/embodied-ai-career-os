# 项目体检报告 · Embodied AI Career OS

> 分析日期：2026-09-10｜分析范围：全仓库（backend / frontend / docs / so101 / 根目录）
> 结论一句话：**代码量不小、架构骨架是对的，但项目正处在"学习记录系统"向"求职作战看板"转型的中途，
> 环境冷启动、文档陈旧、画像失真三类问题正在拖它的实际价值。**

---

## 一、规模体检

| 维度 | 实测 | 说明 |
|---|---|---|
| 后端 Python | 16,028 行 / 159 个文件 | 含 30 个测试文件 |
| 前端 TS/TSX | 5,265 行 / 31+14 文件 | 23 个组件，7 个路由 |
| ORM 模型 | 15 个 | Career / Skill / Task / Project / Milestone / JobApplication / Paper 系列等 |
| API 路由 | 14 个 | 统一 `/api` 前缀 |
| Agent 包 | 7 个 | core / supervisor / planner / reviewer / career / research / knowledge + orchestrator |
| 数据库迁移 | 6 个 SQL | **缺 0005**（0001→0002×2→0003→0004→0006） |
| 文档 | 25 个 md，7,555 行 | 其中 `plane.md` 单文件 3,525 行（原始聊天记录） |

## 二、架构现状

```
浏览器 (Next.js 16 / React 19 / Tailwind v4)
   │  /api/* 由 next.config.ts rewrites 代理
   ▼
FastAPI (14 routers)
   ├── 业务层：career / skills / tasks / projects / milestones / dashboard / learning_logs
   ├── 求职层：job_hunt（聚合）/ job_applications（CRUD + 漏斗）   ← 2026-09-09 新增
   ├── Agent 层：agent / planner / reviewer / tools
   ├── 外部层：github（同步 + 分析）/ paper（RAG 检索 + 对比）
   └── 基础设施：LLM Provider（mock/ollama/deepseek/openai_compatible）
                 Reminder 调度器（Server酱 / PushPlus / terminal）
                 SQLAlchemy（SQLite 默认，Docker 注入 PG）
```

**架构上做得对的几件事**（不要动）：

1. **Agent 框架与业务解耦**：`agents/core/`（BaseAgent / AgentState / AgentExecutor / AgentRegistry）
   不感知具体 Agent，Planner / Reviewer 源码零改动就接入了。
2. **失败隔离**：Orchestrator 单 Agent 失败不中断整链，记 `status=failed` 后继续。
3. **Observability 字段独立成列**：`status` / `duration_ms` / `trace_id` 从 JSON 提升为列，可直接 SQL 查。
4. **求职聚合 API 设计正确**：`/api/job-hunt` 一次返回全页数据，避免前端 N+1 拉取。
5. **三赛道配置外置**：`backend/app/core/target_roles.py` 改配置即改策略，不动逻辑。

## 三、功能完成度

| 模块 | 状态 | 证据 |
|---|---|---|
| Phase 1 基础 CRUD + Dashboard | ✅ 完成 | README 仍写 "Planning"，**文档滞后** |
| Phase 2 Week1 多 Agent Runtime | ✅ 完成 | `docs/phase2-week1-summary.md`，7 套件 18 用例 |
| LLM Provider 接入 | ⚠️ 骨架在，**默认 mock** | `LLM_PROVIDER=mock`；不配 key 全部是假输出 |
| Paper RAG / 对比 | ✅ 有实现 | 5 个 e2e 测试，但 `knowledge/` 目录为空 |
| GitHub 同步 | ✅ 有实现 | 含水位线去重、commit_sha 去重 |
| 提醒调度 | ✅ 有实现 | 4 通道，含 stop_scheduler 幂等 |
| 求职作战看板 /jobs | ✅ 刚上线（09-09） | JobsBoard 826 行 + seed 脚本 258 行 |
| 真机闭环（SO101） | 🟡 半成品 | `so101/` 只有 v0_mujoco、v1_ros2 基础 demo，sim2real 未通 |

## 四、问题清单（按严重度）

### 🔴 P0 — 影响"能不能用"

**P0-1 · 冷启动会掉进 Postgres 陷阱**
`start.sh` 在 `.env` 缺失时自动 `cp .env.example .env`，而模板里写的是
`DATABASE_URL=postgresql+.../postgres:5432/career_os`。本地没跑 Docker 时后端直接连不上库，
而代码默认其实是 **SQLite 零配置**（`sqlite:///./data/app.db`）。
→ 修法：模板默认给 SQLite，PG 作为 Docker 覆盖项单独注释说明。

**P0-2 · 用户画像数据与真人脱节**
`docs/MY_CONTEXT.md` 写的是「6.5 年前端 / WebGIS 背景、目标 30k、ROS2 ★☆☆☆☆」，
而真实现状是 Agent 应用工程师、期望 36–42K、9-24 离职、SO101 已跑通 ACT 训练与推理。
求职看板的匹配度是 `Σmin(实际等级, 要求等级) / Σ要求等级`——**输入失真则整块看板结论失真**。
→ 修法：以 `target_roles.py` 为准重填 Skill 表等级，或先跑 `seed_job_hunt.py` 再逐项校正。

**P0-3 · 环境完全未初始化**
当前无 `node_modules`、无 `backend/.venv`、无 `.env`、无 `data/`。
首次 `bash start.sh` 需要 2–5 分钟装依赖，且依赖网络。

### 🟡 P1 — 影响"维护成本"

**P1-1 · `JobsBoard.tsx` 826 行单体客户端组件**
一次 commit 塞入 1,977 行前端代码，该组件同时承担：倒计时、岗位匹配、技能缺口、里程碑、
周任务、投递漏斗、新增/流转/删除。建议拆为 `JobHero` / `RoleMatchPanel` / `ApplicationFunnel` / `ApplicationTable` 四个。

**P1-2 · 文档冗余且互相矛盾**
- `docs/plane.md` 3,525 行原始聊天记录，应归档到 `docs/archive/`；
- `README.md` 的 Phase 状态仍停在 "Planning"；
- `DEVELOPMENT_PLAN.md` / `PRD.md` / `PHASE2...` / `PHASE3...` 内容重叠。

**P1-3 · 空目录占位**
`agents/`、`database/`、`deploy/`、`knowledge/` 四个空目录，README 声称后续填充。
要么填内容，要么删掉避免误导。

**P1-4 · 迁移编号断裂**
缺 `0005`，且 `0002` 有两个并行文件（papers / project_management）。需在 `run_migration.py`
补断言或补号，避免后续顺序歧义。

### 🟢 P2 — 卫生问题

- 根目录 `literacy-workspace.html`（44KB「宝宝识字启蒙台」）**明显是别的项目串进来的文件**，建议移出。
- 根目录 `dashboard.html`（45KB）是 Ardot 设计稿产出的静态原型，已被 Next.js 实现取代，建议归档到 `docs/design/`。
- `backend/app/core/config.py` 里 `github_owner` 硬编码兜底 `prideandprejudice`，建议改从 env 强制读取或留空。
- 早期分析文档提到的 P0 bug（QuickActions 死链、SubNav 日期重复、AgentActivity 死代码）**已修复**，
  可标记 `docs/agent-ui-improvement-analysis.md` 为已闭环。

## 五、与求职目标的对齐度

用户现状：9-24 离职、10 月底前需落定、期望 36–42K。项目三赛道配置本身是合理的：

| 赛道 | 定位 | 薪资 | 当前主要缺口 |
|---|---|---|---|
| embodied 具身/VLA | 主攻 | 36–45K | Sim2Real、Isaac、VLA 需真机证据 |
| robot-software ROS2+AI | 折中 | 30–38K | MoveIt2、C++ |
| agent 应用/LLM | 保底 | 30–40K | 基本达标，用于快速拿面试 |

**关键判断**：这个项目对你的求职有两重价值，但目前只兑现了一重。

1. ✅ **作为工具**：`/jobs` 看板能管投递漏斗、倒计时、里程碑——这部分刚做好，能用。
2. ❌ **作为作品集证据**：面试官不会因为"你写了个管理自己学习的 CRUD"加分，
   但会因为「Multi-Agent Runtime + 可观测 trace + RAG + 真机 SO101 闭环」加分。
   目前第 2 点的核心证据（sim2real）**还缺**，`so101/` 只到 ROS2 基础 demo。

## 六、建议的下一步（按性价比排序）

| 优先级 | 动作 | 预计 | 收益 |
|---|---|---|---|
| 1 | 修 P0-1（`.env.example` 默认 SQLite）+ 跑通一次 `bash start.sh && bash scripts/smoke.sh` | 20 分钟 | 项目随时可启动、可演示 |
| 2 | 跑 `backend/scripts/seed_job_hunt.py`，校正 Skill 等级与真实画像 | 30 分钟 | 看板结论可信 |
| 3 | 把 SO101 sim2real 做成可展示结果（成功率数据 + 视频/截图） | 1–2 周 | 直接补上主攻赛道最大缺口 |
| 4 | 拆 `JobsBoard.tsx` + 归档 `plane.md` 等文档 | 半天 | 维护成本下降，面试时可讲架构 |
| 5 | 接真实 LLM Provider（当前 mock 输出无法演示 Agent 能力） | 1 小时 | 演示时 Agent 是真跑的 |

---

## 七、修复进度（2026-09-10 已处理）

### P0-1 已修 —— 数据库配置链路

| 改动 | 文件 |
|---|---|
| 默认改为 SQLite，PG 仅留给 docker compose | `.env.example` |
| 启动时加载根 `.env` / `backend/.env`（不覆盖 Docker 注入值） | `backend/app/core/config.py` |
| 新增 `python-dotenv>=1.0` 依赖 | `backend/requirements.txt` |

**顺带查出一个更严重的问题**：原来 `.env` 根本没被加载——`start.sh` 只负责 `cp`，
后端全程用 `os.getenv` + 默认值，也没有 `load_dotenv`。也就是说**改 `.env` 的
`LLM_PROVIDER` / `GITHUB_TOKEN` 对本地进程完全不生效**。现在修好了。

### P0-0（新发现，比原 P0-1 更致命）—— 所有 SSR 页面都连不上后端

启动前端实测 `/jobs` 时页面显示"后端连接失败"，但后端明明在跑。
根因：

```
node -e "fetch('http://localhost:8000/health')"   → ECONNREFUSED
node -e "fetch('http://127.0.0.1:8000/health')"   → 200
```

**Windows 上 Node 把 `localhost` 解析到 IPv6 `::1`，而 uvicorn 绑 `0.0.0.0` 只覆盖 IPv4。**
Server Component 与 next rewrites 代理都由 Node 发起请求，于是全军覆没。

| 改动 | 文件 |
|---|---|
| SSR 取数兜底地址改 `127.0.0.1` | `frontend/src/lib/apiClient.ts` |
| rewrites 代理目标改 `127.0.0.1` | `frontend/next.config.ts` |
| 启动前端时注入的 `BACKEND_URL` 改 `127.0.0.1` | `start.sh`（2 处） |
| 冒烟测试改 `127.0.0.1`，并新增求职 API 与 `/jobs` 降级检测 | `scripts/smoke.sh` |

### P0-2 已修 —— 技能画像校准

| 改动 | 文件 |
|---|---|
| 新建真实技能画像**单一数据源**（16 项，含 evidence） | `backend/app/core/skill_profile.py` |
| 建表种子改为引用画像，不再维护副本 | `backend/app/db/base.py` |
| 新增 `calibrate_skills()`：幂等覆盖已有技能的等级/证据 | `backend/scripts/seed_job_hunt.py` |
| 重写为真实背景（Agent 工程师 / 36–42K / SO101 现状） | `docs/MY_CONTEXT.md` |

### 校准后的看板实测

```
career: Robot AI Engineer（具身/机器人方向） | 薪资目标 40000 | 截止 2026-10-31 | 剩余 51 天

 主攻 | 具身智能 / VLA 算法工程师        匹配度  38% | 36-45K
 折中 | 机器人软件工程师（ROS2 + AI）     匹配度  55% | 30-38K
 保底 | Agent 应用 / LLM 算法工程师       匹配度  88% | 30-40K

技能缺口 top：MoveIt2(0→4)、Sim2Real(0→4)、Isaac(1→4)、VLA(1→4)、ROS2(2→4)
求职项目：求职冲刺 · 2026 Q4 | 里程碑 0/5 | 任务 7（doing 2 / todo 4 / done 1）
投递漏斗：4 条 | applied 1 / screening 1 / interview 1 / rejected 1 | 响应率 50%
```

**读法**：保底盘 88% 意味着 Agent 方向现在就能打；主攻盘 38% 且缺口集中在
Sim2Real / MoveIt2 / Isaac / VLA——这四个里，Sim2Real 是唯一能在一个月内靠
SO101 真机实验补出可展示证据的。

### 端到端验证

```
GET /health                     → {"status":"ok",...}
GET /health/db                  → {"db":"ok"}          （SQLite 生效）
GET /api/job-hunt               → 200，见上
GET /api/job-applications/stats → 200，漏斗统计正确
```

`bash scripts/smoke.sh` 全量冒烟：**20 项全部通过**
（后端 8 个业务 API + 求职 2 个 API + /dashboard /projects /agents /jobs 四个页面 +
/jobs 数据渲染正常 + 种子数据 15 项技能）。

`cd backend && pytest -q`：**112 passed**。

---

## 附：关键文件索引

| 用途 | 路径 |
|---|---|
| 后端入口 | `backend/app/main.py` |
| 三赛道配置 | `backend/app/core/target_roles.py` |
| **真实技能画像（改等级改这里）** | `backend/app/core/skill_profile.py` |
| 求职聚合 API | `backend/app/api/job_hunt.py` |
| 求职数据脚本 | `backend/scripts/seed_job_hunt.py` |
| 求职看板前端 | `frontend/src/components/JobsBoard.tsx` |
| Agent 框架 | `backend/app/agents/core/` |
| 一键启动 | `start.sh` / `stop.sh` / `scripts/smoke.sh` |
| 架构文档 | `docs/agent-system.md` |
