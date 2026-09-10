# 项目长期记忆 · Embodied AI Career OS

## 项目基础
- **⚠️ 战略主线已于 2026-09-10 转向**：从「具身智能主攻」改为 **LLM 主攻 + VLM 卡位 + AI 算法保底**
  （依据《求职 Agent 开发与运行规范 v2.0》：具身/VLA/ROS2/Isaac/SO101 全部列为 D 级
  "一个月主动不深挖"）。设计文档见 `docs/agent-design/JOB_SEARCH_AGENT_DESIGN.md`。
  **不要再推荐具身方向的学习任务**；`skill_profile.py` 中 D 级技能 target=level（gap 恒 0）。
  优先级锁：求职 > LLM 核心能力 > 项目 > 博士准备 > 具身。
- **类型**：面向算法工程师的"求职作战 Agent 系统"（前身为具身智能职业 OS）
- **技术栈**：Next.js 16（App Router）+ React 19 + TypeScript + Tailwind v4（CSS-first @theme）
- **设计取向**：零第三方 UI 库（全部手写组件）、零图表库（雷达图等纯 SVG）、Geist 字体
- **数据流**：Server Component 拉取 + `router.refresh()` 增量更新
- **后端**：FastAPI 风格（路径 /api/career/... /api/tasks/...），snake_case 存储，
  前端用 adapter 转换为 camelCase
- **数据形态**：Career / Skill / Task（STATUS_CONFIG: todo/doing/done）/ Project / Milestone /
  AgentRunRecord / CommitSuggestion / **JobApplication**（求职投递：applied→screening→interview→offer/rejected）
- **求职作战看板（2026-09-09 新增）**：系统定位从"学习记录"转向"求职进度看板"。
  后端 `/api/job-hunt`（聚合：岗位画像+匹配度/技能缺口/里程碑/周任务/投递漏斗）、
  `/api/job-applications`（CRUD+/stats）；前端 `/jobs` 页（JobsBoard 客户端组件）。
  三赛道配置见 `backend/app/core/target_roles.py`。数据脚本 `backend/scripts/seed_job_hunt.py`（幂等）。
- **真实技能画像单一数据源（2026-09-10 新增）**：`backend/app/core/skill_profile.py`
  —— 改技能等级/证据只改这个文件，改完跑 `python backend/scripts/seed_job_hunt.py` 校准进库
  （`calibrate_skills()` 幂等覆盖已有数据）。`app/db/base.py` 建表种子只是引用它，不要在那里改副本。
  `docs/MY_CONTEXT.md` 只写背景与策略，不写等级。

## 命名与代码规范
- 组件 PascalCase.tsx，一文件一默认导出
- `type Props = {...}` 内联
- 常量 UPPER_SNAKE_CASE（如 `STATUS_CONFIG`、`AGENT_COLORS`）
- 服务层 camelCase；后端 snake_case→camelCase
- 颜色：emerald=成功/当前、sky=规划/Planner、violet=Reviewer、amber=待办/Career、rose=Research/失败
- 卡片样式：白底 + hairline 边框 + 18px 圆角 + 24px padding，无阴影（与 Apple 风格一致）
- 状态徽章：pill 形（radius 999），浅色底 + 深色字

## 设计资产
- **Ardot 画布 fileId 716776328381413**（2026-08-20 设计的完整 dashboard）
  - 27 个设计变量已通过 `apply_variables` 写入
  - 桌面端 1440 + 移动端 390 双版本
  - 验证截图存 `.workbuddy/screenshots/`（desktop-full / mobile-full / radar-card /
    quick-actions / row2-tasks-projects / agent-activity）

## 求职 Agent（Batch 0–4 全链路，2026-09-10 完成）
- 定位：系统从"学习记录"转为"求职作战看板"；v2.0 战略 = LLM 深度主攻 + VLM 轻卡位 +
  AI 算法保底，具身冻结（D 级，`target=level` 使 gap 恒为 0）。
- 四条线 + 页面：岗位池/JD 匹配（`/jd`）→ 简历防虚构（`/resume`）→ 面试弱项回写（`/interview`）
  → 日报周报（`/reports`）。设计文档：`docs/agent-design/JOB_SEARCH_AGENT_DESIGN.md`。
- **实现约定（重要）**：Match / Resume / Interview / Report 四个引擎一律落地为
  `agents/<name>/engine.py` 或 `services/report/engine.py` 的**独立纯规则模块，
  不套 BaseAgent / LangGraph**——核心是确定性聚合与推导，需可单测/可解释/不烧 token。
  设计文档把 Agent 列为 BaseAgent 子类属过度设计，已在设计文档 §0.1.3 记录该"有意偏离"。
  **新增业务 Agent 沿用此模式**；LLM 只做措辞/生成类增量，且产出仍要过规则校验。
- 报告调度：APScheduler 注册 `job_daily_report`(08:30) / `job_weekly_report`(周一 09:00) /
  `job_followup_remind`(10:00)。幂等靠 `ReportLog(kind, period_key)` 唯一约束；
  开关与时间见 `config.py` 的 `REPORT_*` 项。推送通道统一走 `channels.build_channel()`。

## 展示层约定（2026-09-10 阶段 1 定型）
- **雷达图必须"岗位对齐"，不要回到全量技能轴**：旧实现按全 48 技能（排除 2）出 **46 轴**、
  34 项有 gap，形状无语义。现方案：`dashboardService.pickPrimaryTrack()` 选 `TARGET_ROLES`
  中 priority=主攻 的赛道，取其 `required_skills` 出 **8 轴**（`RadarAxis{name,current,required,gap}`）。
  改雷达只改 `SkillRadarCard` + `RadarChart`，**不要再新增第二套实现**
  （历史死组件 `SkillOverview` 就是双实现，已删）。目标态是 R2 域聚合 6 轴（需给技能补 `domain`）。
- **就绪度口径必须与看板同源**：Dashboard 的 readiness = 主攻赛道 `matchPct`，
  **不是** 全技能加权和；`KpiCards` 用 `readinessLabel` 传标签。两处口径不一致会被立刻发现。
- **Planner 目标岗位不要硬编码**：`backend/app/api/planner.py` 的默认值来自
  `TARGET_ROLES` 的「主攻」赛道（`_DEFAULT_TARGET_ROLE`）；前端 `plannerService` 只在
  显式传参时才发 `target_role`。历史上写死 `"Robot AI Engineer"` 导致 Planner 一直产出具身任务。
- 分析文档：`docs/app-mode-and-radar-analysis.md`（模式门控方案 + 阶段 1/2/3 计划，
  阶段 1 已 ✅ 完成）。**模式门控原则：模式只改展示、不改数据，不做两套前端。**

## 环境约定
- **本地开发用 SQLite**（`backend/data/app.db`），Docker Compose 用 PG（compose 内覆盖 DATABASE_URL）。
  不要在没跑 Docker 的机器上填 Postgres 连接串。
- `.env` 由 `backend/app/core/config.py` 顶部 `load_dotenv` 加载（根 `.env` 优先，其次 `backend/.env`，
  不覆盖已存在环境变量 → Docker 注入始终优先）。**早期版本没有 load_dotenv，改 .env 完全不生效**，已修。
- 一键启动：`bash start.sh` / `bash scripts/smoke.sh`(40 项) / `bash stop.sh`；
  后端测试 `cd backend && pytest -q`（157 项，**约 24 分钟**，含慢速集成；
  验证时优先跑定点文件如 `pytest tests/test_report_engine.py -q` + smoke）。
  跑 pytest 需用 `C:\Users\zxy_2\anaconda3\python.exe`（managed python 无 pytest 模块）。

## 关键经验（避坑）
- **Windows 前后端联调一律用 `127.0.0.1`，不要用 `localhost`**：Node 会把 localhost 解析到
  IPv6 `::1`，而 uvicorn 绑 `0.0.0.0`（仅 IPv4）→ Server Component 与 next rewrites 全部
  ECONNREFUSED，页面显示"后端连接失败"。已修 4 处（apiClient.ts / next.config.ts /
  start.sh / smoke.sh），新增代码勿再写 localhost。
- **`.env` 必须靠 `load_dotenv` 才生效**（已在 config.py 加载；早期版本没加载，改了没反应）。
- **Ardot SVG 解析器对退化几何敏感**：纯水平/垂直直线段会因包围盒为 0×N 或 N×0 报
  "degenerate geometry" 错误。**修复：给所有轴线加 1px 偏移**（如 `M180 180L181 40`）。
- 设计变量已就位，下次实现代码时直接引用 `var(--color-canvas)` 等 token，不要再硬编码 hex。
- **`stop.sh` 的 Windows 杀进程（2026-09-10 修复）**：Git Bash 的 `kill <winPID>` 对原生进程
  **静默返回 0 却不生效**，`kill ... || taskkill ...` 的兜底因此永不触发（表现为打印"✓ 已停止"
  但 netstat 显示 PID 照旧）。现改为 Windows 走 `MSYS_NO_PATHCONV=1 taskkill /F /T /PID`，
  且 kill 后复检端口，失败即报错。同理：Git Bash 里不要用 `taskkill //F`（斜杠会被改写）。
- **启动后端的可靠方式**：`start.sh` 的 Windows detach（PowerShell `Start-Process -WindowStyle
  Hidden`）在"用后台任务直接运行 start.sh"时会随任务回收而退出。要在会话内验证，直接后台跑
  `backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000`。
- **🔴 测试不得写开发库（2026-09-10 已修复，仍为硬约束）**：`backend/tests/` 曾长期
  **没有 `conftest.py`**，多数测试 `TestClient(app)` 直连开发库 `data/app.db`，
  一度把 dev 库灌成 **214 个项目（真实仅 2 个）、178 里程碑、393 agent_runs、292 任务**。
  **现已落实 `tests/conftest.py`**：模块级把 `DATABASE_URL` 指向
  `tempfile.mkdtemp("career-os-tests-")` 下的临时库，session guard 内**直接调 `init_db()`**
  （不能依赖 TestClient 的 lifespan —— 模块级 `client = TestClient(app)` 不进 `with` 时 lifespan 不触发）。
  **新增测试一律不自建临时库、不在 import 期做 `unlink()`**（删除失败会中断 pytest 收集阶段）；
  依赖实时后端 :8000 的脚本放 `collect_ignore`。
  验收门 = 跑完全量 `pytest` 后 `md5sum -c` 开发库指纹不变。
- **Pydantic v2 `from_attributes` + 未 flush 的 ORM 实例**：SQLAlchemy 列 `default` 只在 INSERT
  时生效，内存对象属性是 `None`，`ProjectOut.model_validate(orm)` 会报 `source: string_type`。
  **修法**：给字段加 `@field_validator(<field>, mode="before")` 回落默认值（见 `schemas/project.py` /
  `schemas/task.py` 的 `_default_source`）。给 ORM 加列 + 加进 Out schema 时必检这一条。
- **数据库现状基线（2026-09-10 清理后）**：`projects` 2 / `milestones` 12 / `tasks` 18 /
  `agent_runs` 6–9。真实业务表 = `job_applications`(4) / `resume_facts`(9) /
  `interview_logs`(1) / `career_goal` / `projects#1 SO101 Embodied AI System`。
  清理脏数据时以上为白名单，**一律不动**。
- **双角色切换已落地（2026-09-10）**：视角 = URL `?role=` + cookie `view_role`
  （`lib/viewRole.ts` 定义 `VIEW_ROLE_COOKIE` / `viewRoleHref` / `normalizeViewRole`），
  由 Server Component 读 —— **不用 localStorage**（读不到且会闪烁/水合不一致）。
  `/dashboard` → LLM 主攻 8 轴 75%；`/dashboard?role=embodied` → 具身 6 轴 38%。
  切换**只改"看什么"，不改数据**，绝不 fork 两套前端。
- **⚠️ 同一文件禁止并行 Edit**：docstring 与 print 两处并行编辑会竞争写盘，
  后提交者按旧快照整体覆盖 → 先提交的那处被**静默回滚**（本次 3 个文件命中，工具仍报 success）。
  同文件多处修改必须**串行**。
- **赛道数据已够用，切换视角是纯前端活**：`/api/job-hunt → target_roles` 返回 4 条赛道
  （llm 75% / vlm 58% / ai-algo 75% / embodied 38%，字段 snake_case `match_pct`）。
  做"双角色切换"只需改 `dashboardService.pickPrimaryTrack()` 按 `?role=` 选赛道，
  `SkillRadarCard` 无需改动（已支持任意 `axes[]`）。

## 2026-09-10 下午 增补：视角-任务打通 / 布局收敛 / Planner 可解释

- **`GlobalNav` 只允许出现在 `app/layout.tsx`（架构约束）**：此前 7 个页面各自渲染，
  `/projects` 漏了 → 全站唯一没有顶栏的页面，且自带 `zinc-50/dark:bg-black` 调色板。
  **新增页面一律不渲染 GlobalNav，外层用 `flex flex-1 flex-col`，不要 `min-h-screen`**；
  页头统一用 `components/PageHeader.tsx`。
- **任务-赛道模型**：`tasks.track_key`（迁移 0008）与 `source` 正交 —— `source` 说"谁写的"
  （user/seed/planner/test），`track_key` 说"属于哪条赛道"。
  `GET /api/tasks?track_key=X[&include_untracked=true][&include_test=true]`。
  `include_untracked=true` → `track_key == X OR track_key IS NULL`（兼容历史无标签任务）。
  赛道判定口径统一在 `app/core/target_roles.py`，**声明顺序优先**（PyTorch/Python/DL 归 llm）。
  回填工具：`backend/scripts/backfill_task_track.py`（默认 dry-run，`--apply` 自动备份）。
- **Planner 必须按赛道取技能**：`_scope_skills_to_track()` 把候选限制在赛道 `required_skills`，
  避免"在 LLM 视角生成具身任务"。冻结赛道（`embodied`）有
  `FROZEN_TRACK_MAX_MINUTES = 45` 低强度上限。响应体携带全部决策字段
  （`track_key/track_name/track_frozen/skill_level/skill_target/gap/reused/reason`）
  供前端 `PlannerResultCard` 渲染"为什么是这条"。
- **Planner 幂等作用域**：`_persist_task` 在 `project_id is None` 时**必须**加
  `Task.project_id.is_(None)`，否则全局请求会错误复用某个里程碑绑定的任务。
- **迁移 SQL 硬规则（`run_migration.py`）**：按 `;` 裸切分、不识别注释、多语句同事务全量回滚。
  → 注释里**禁止出现分号**；一条迁移只做一件事（加索引请单独一条）。
- **测试写法**：涉及幂等的用例一律用**增量断言**（记录调用前后 count），
  不要断言绝对行数 —— 共享临时库下会受其他用例污染（表现为单跑过、全量挂）。
  `list_projects` 现已返回完整 `milestones[]`（卡片要显示"当前里程碑"），不再是纯 stats。

## 2026-09-10 晚 增补：平台定位转向「施工执行台」

- **平台定位定调（文档 `docs/platform-direction-30day.md`）**：从"状态看板/展示台"转向
  "30 天施工执行台"。判据一句话：**顶栏 8 个入口里有没有一个回答"我今天该干什么"**。
  改造后 IA = `今日 / 施工 / 项目 / 题库 / 求职▾ / 复盘 / Agent`；
  `/dashboard` 降为二级"我的水平"页（不删），**`/today` 成为默认落地页**。
- **硬约束（写进项目宪法级别）**：单周平台工时 ≤ 2 个晚上。学习平台的失败模式是
  "时间花在建设平台上而不是学习上"。超预算时优先砍 P4（求职包装）再砍 P3（题库）。
- **两个正交轴的新成员**：`tasks.plan_day_id`（属于课程第几天）与既有 `tasks.track_key`
  （属于哪条赛道）正交。**Day 序号绝不与日历日期绑定** —— `PlanDay.seq` 是不可变脊梁，
  `DayProgress.calendar_date` 可移动；滑期只提示不自动顺延（否则 30 天变 45 天）。
- **每日四件套契约**：`artifacts.kind ∈ {code, note, questions, commit}`；
  其中 `questions`（当天题库新增 ≥5，可数）与 `commit`（GitHub 按日期归集，全自动）
  可自动核验 —— 这是"完成"有约束力的前提，纯手工勾选会失效。
- **技能晋级改为 evidence-gated**：L1 需 note、L2 需 code+commit、L3 需 Experiment、
  L4 需对比实验+复现报告。技能等级不再是自评，而是从证据推导。
- **题目口径**：累计目标 150（每天 5×30），核心必达 80（50 LLM + 30 VLM）。
- **约束机制要硬**：`TECH_BLACKLIST`（已定义 12 项）必须接 Planner 硬拒绝；
  新增 `RESOURCE_LOCK` 锁 5 类资源，防"课程收藏"式发散。
- **不做清单**（防平台自身发散）：新 Agent、D 级技术功能、资源收藏库、移动端/多用户、
  监控大屏、PlanDay 的 CRUD 界面（用「计划文件 + 幂等种子脚本」，同 `target_roles.py` 模式）。
