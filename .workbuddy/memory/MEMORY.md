# 项目长期记忆 · Embodied AI Career OS（第7版，2026-09-18）

## Spec 工作流
- Spec 落在 `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`；review 落同目录 `YYYY-MM-DD-spec-review.md`。
- ⚠️ 已批准（"状态：已批准"）**不等于已核对代码事实**：2026-09-18 review 两份 spec，Tailwind 那份 4 处前提与仓库不符（Tailwind 早已安装、配置已存在、v4 不写 tailwind.config.ts、无 data-theme），题库那份执行物已存在且有 SyntaxError。**审 spec 一律先实测代码/DB，别信 spec 自述的现状。**

## 战略 / IA
- v2.0：LLM主攻+VLM卡位+AI算法保底；具身/VLA/ROS2/Isaac/SO101 全冻结（target_roles frozen，gap恒0）。
- 平台=30天施工台，判据「我今天该干嘛」；/today 为默认落地页，/dashboard 降二级。GlobalNav 一级 4 项：今日|求职|学习|概览（二级路由 13 个）。
- 求职四线 /jd /resume /interview /reports；引擎一律独立纯规则模块（agents/*/engine.py、services/*/engine.py），不套 BaseAgent/LangGraph；LLM 只做措辞增量。

## 技术栈 / 展示层
- Next16 App Router+React19+TS+Tailwind v4（CSS-first @theme）；FastAPI+SQLAlchemy+SQLite；零第三方 UI/图表库（纯 SVG 雷达）。
- ⚠️ Tailwind v4 现状（2026-09-18 实测）：tailwindcss@4 + @tailwindcss/postcss 已装、postcss.config.mjs 已配、globals.css 首行已 `@import "tailwindcss"`；**无 tailwind.config.\*（v4 就该没有，别新建）**。`@theme inline` 只登记 4 个变量（--color-background/foreground、--font-sans/mono）→ **token 工具类（bg-card/text-ink/rounded-card）根本不生成，全仓库使用 0 次**；默认工具类（flex/text-sm）可用。样式主体是 inline：**59 文件 / 933 处 `style={{}}`**。
- 🔴 迁移 Tailwind 的真实工作只有「把 67 个 token 登记进 `@theme`」，不是"引入 Tailwind"。v4 命名空间坑：`--color-page` 不存在（是 `--color-canvas`）；`--radius-card-lg` 生成 `rounded-card-lg`（改名成 `rounded-card` 要动 37 处引用）；`--font-size-*` 不是 v4 命名空间（应为 `--text-*`）。**变量引用密度**：33 个变量 / 1202 次引用（--color-ink-48 232、--color-ink 105、--radius-pill 104、--color-primary 81、--color-hairline 62、--color-card 58、--radius-item-md 42、--radius-card-lg 37、--color-zinc-100 36、--color-canvas 24）。
- ⚠️ 暗色模式是 `@media (prefers-color-scheme: dark)` 覆盖 `:root`，**全仓库无 `data-theme`**。把 token 移进 `@theme` 后与它的覆盖先后顺序需实测（唯一真实风险点）。
- ⚠️ 硬编码色值迁移会静默改色：TodayBoard 的 `#F5F5F5` ≠ `--color-zinc-100`(#F4F4F5)，GlobalNav 的 `#000000` 无对应 token；而 `#FAFAFB`/`#FEF2F2`/`#FFFFFF` 与 token 精确相等可安全替换。规则=①缺 token→补②近似→人工确认③有意差异→保留+注释。
- 组件 PascalCase.tsx 单默认导出；type Props 内联；常量 UPPER_SNAKE；后端 snake→前端 adapter camel。
- 卡片白底+hairline+18px 圆角+24px padding 无阴影；色 emerald=成功 sky=Planner violet=Reviewer amber=待办 rose=失败；**一律 var(--color-*) 不硬编码 hex**（现状已有 29 文件 81 色值违规，待清）。
- GlobalNav 只在 app/layout.tsx；子页外层 flex flex-1 flex-col，不用 min-h-screen；页头 PageHeader.tsx。
- 雷达取主攻赛道 required_skills 出 8 轴；Dashboard readiness=主攻 matchPct，须与看板同源。

## 数据模型（三正交轴）
- tasks.source(user/seed/planner/test) / track_key(llm/vlm/ai-algo/embodied/NULL) / plan_day_id。
- `GET /api/tasks?track_key=&plan_day_id=&include_untracked=&include_test=&scope=all|current_mode`（默认 all）。
- plan_30d.py 是课程唯一源（PlanDaySeed×30 + RESOURCE_LOCK + SKILL_TO_DAY_SEQ）；改计划=改该文件 + 重跑 scripts/seed_plan_30d.py（--dry-run/--rebind），不做 CRUD 界面。
- PlanDay.seq 是课程序号，**绝不绑日历日期**；/today 同返 seq 与 day_index，滑期只提示不顺延。
- 🆕 迁移 0016-0018 已用，**下一条 0019**。单语句原则（run_migration 按分号裸切）；迁移必须 SQLite+PG 双跑，方言分支收口在 run_migration.translate_sql_for_postgres（精确短语替换+残留检测），新迁移写 SQLite 写法即可，禁 PG 专属语法。迁移改动必跑 tests/test_migration_dialect_compat.py。create_all 的 checkfirst 只判表→新索引必须单独写迁移。

## 环境 / 门禁
- 本地 SQLite backend/data/app.db；Compose 覆盖 DATABASE_URL 用 PG；.env 由 config.py 顶部 load_dotenv（不覆盖已存在环境变量）。
- 启动：后台上 `backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000`，前端 `cd frontend && npx next dev -p 3000`。
- pytest 用 backend/.venv/Scripts/python.exe，**要 chdir backend**（python -c os.chdir 包一层）；全量基线 **277 passed / 4 failed / 2 skipped**；pytest 后必须核对开发库指纹（基线 md5 `8e24ee147c81ff97ed2fc04249e0d70a`）。ruff 未装，静态门禁=py_compile+pytest。
- 前端门禁：`node node_modules/typescript/bin/tsc --noEmit -p <abs tsconfig>` + `node node_modules/eslint/bin/eslint.js --config <abs eslint.config.mjs> <文件>` + `node node_modules/next/dist/bin/next build`（npm shim 会进 WSL 黑名单，用 node 直调；next build 需 cwd=frontend）。改动文件命中既有 eslint 报错时，用 `git show HEAD:<file>` 对临时文件复现自证。
- Git Bash 残缺（cd/ls/wc/tail/dirname 缺失）→ 文件操作走 Read/Write/Edit/Glob/Grep，命令用 managed python 绝对路径；netstat 输出要 decode('gbk')。

## 避坑（硬规则）
- 联调一律 127.0.0.1 不用 localhost（Node→IPv6::1，uvicorn 只绑 IPv4）。杀进程 `MSYS_NO_PATHCONV=1 taskkill /F /T /PID`。
- 改 ORM/schema 后必须重启后端（无 --reload）。
- 🔴 测试不得写开发库：tests/conftest.py 模块级把 DATABASE_URL 指向临时库，session guard 内 init_db()；新增测试不自建临时库、不在 import 期 unlink()；幂等用例用增量断言。
- **口径必须同源**：services/action_planning/task_scope.py 是唯一权威（resolve_task_scope + select_tasks），/api/job-hunt 与 /api/plan/today 只调它，**禁止任何路由/组件再拼 track_key 条件**；/api/tasks?scope=current_mode 亦复用。赛道判定是**排除制**（不可改白名单，会静默隐藏漂移任务，违反 PRD F5.3）；三分类 active/frozen/unclassified 是全函数。
- summary 必须与列表同源（历史 bug：截断到 12 却报 16）→ 加断言 summary.x == len(list)。
- service 层不要透传 payload：apiClient 不做 key 转换，create/patch 必须显式列 snake_case。
- Pydantic v2 from_attributes + 未 flush ORM：列 default 只 INSERT 生效 → @field_validator(mode="before") 回落。
- 源码护栏测试必须先剥注释（否则被注释里引用的旧写法命中→假阳性），并加"命中数非空"哨兵断言。
- 口径验收不许拿开发库切模式（写 is_current + 插 transition → 指纹变）：复制库 + DATABASE_URL 覆盖起临时 uvicorn。
- _JD_ALIASES 是小写子串命中，禁加宽泛别名（裸「对齐」「zero」已误判过）；画像技能名英文、JD 常写中文 →「注意力」「分布式训练」须显式加。匹配分异常低先查 SKILL_PROFILE 是否根本没有该技能（词表盲区）。
- 通用技能不可映射具体课程日（只留 Transformer/Attention/RoPE/SFT/LoRA/QLoRA/vLLM/ViT/CLIP/VLM/Pretraining/Inference Optimization）；宁可少绑不可错绑，规则收紧后必须 --rebind。
- ⚠️同一文件禁止并行 Edit（写盘竞争，先提交者被静默回滚但工具报 success）；怀疑没落盘用 Grep 复读。
- .workbuddy/tmp/ 已在 .gitignore（曾两次被 git add -A 收进仓库）。
- 岗位池 tier 跟随赛道（llm→1/vlm→2/ai-algo→3）；JobPostingPatch 无 PATCH 路由（死导入），改 tier 只能删了重录。

## 真实数据源
- 技能等级/证据单一源 app/core/skill_profile.py（改完跑 scripts/seed_job_hunt.py 校准）；赛道配置 app/core/target_roles.py（含 SPRINT_START=2026-09-10 / SPRINT_END=2026-10-09 / DEFAULT_OFFER_DEADLINE=2026-10-31 / TECH_BLACKLIST）。
- 简历防虚构锚点 resume_facts(9) + /api/resume 诊断；EI 会议严禁虚标 SCI。
- 开发库基线（白名单，2026-09-17 实测）：projects 2 / milestones 12 / job_applications 3 / resume_facts 9 / interview_logs 2 / skills 49 / plan_days 30 / interview_questions 110 / tasks 23。求职现状：JD#7 华夏泰科 + JD#8 电价预测均 **rejected**（09-17 回写），JD#9 大禹节水·Agent 今天新建（track='agent'，不在 TARGET_ROLES → 漂移任务），**零活跃面试流程**。
- ⚠️ 看板匹配分（82-89）是"向目标推进的进度"**非达标**：按 required_level=4 严格口径，llm 13% / vlm 17% / ai-algo 20% 达标。且 target_roles 的 llm required_skills(8) 漏了真实 JD 要的 RAG / Agent Application → 匹配分系统性虚高。分析见 docs/候选人背景分析-2026-09-17.md。

## 阶段模式（career_mode，Milestone A+B 已落地 2026-09-16）
- 模块 services/career_mode/{presets,service}.py + api/career_mode.py + models/career_mode.py；`/api/career-mode`、`/switch`、`/transitions`。当前 job_hunt（deadline 2026-10-31，active llm/vlm/ai-algo，frozen embodied）。
- 不变量：当前模式唯一（部分唯一索引 ux_career_modes_current）/ 切换只写 is_current + 模式历史 / presets 是定义单一来源（启动 sync，不覆盖 is_current）；赛道策略派生自 target_roles.py，禁止再抄清单。
- 契约 schemas/task_scope.py（TaskScopeOut/ScopedTaskRef）+ 前端 services/taskScope.ts 一份搬运；前端只用后端分类，不在 React 重算。
- **ViewRole ≠ CareerMode**：ViewRole 仅为 Dashboard 展示视角（cookie+?role=），**禁止**影响任务请求参数/数据范围/统计。⚠️ 2026-09-17 实测 ViewRole 已成死代码（RoleSwitcher.tsx 无页面引用、dashboard/page.tsx 不收 searchParams、dashboardService 不读 role）。
- 遗留待裁决：SubNav→GenerateTaskButton 仍把视角 trackKey 传给 Planner 生成接口（写操作）。
- 实施约束/规范（验收依据）：docs/CODEBUDDY_IMPLEMENTATION_CONSTRAINTS.md、docs/CODEX_MODULAR_DESIGN_STANDARD.md、docs/CODEX_READABILITY_STANDARD.md、docs/PRD_CAREER_OS_MODES.md；实施顺序 A→B→C→D 不得越级。

## 既有缺陷（勿误判为新增回归）
- 全量 pytest 4 个 test_plan_api 失败：fixture 只播 Day1-2，而"今日"按真实日历推导（09-17=Day8）→ 404。日期驱动，随时间恶化。
- `GET /api/job-postings` 恒 500：schemas/job_posting.py:133 from_rows → JobPostingOut 3 处 list/dict 校验失败（NULL 字段）。
- components/JobsBoard.tsx 996 行、ResumeBoard 647、JDBoard 610、TodayBoard 605、QuestionBoard 511（54 组件中 7 个 >400 行）。
- 🔴 `backend/scripts/seed_questions_v2.py` **已存在但跑不起来**：第 255 行 `（"它"指什么）` 用了 ASCII 双引号 → 字符串提前闭合 → `SyntaxError: invalid syntax (line 255)`，模块无法 import。且它**只写了 38 题（MM10/Project21/Coding7，LLM 0 题）** → 跑完 total=148 而非 150、core=78 而非 80（80 才是有原文依据的硬指标）。另 20 个 skill_name 不在 `SKILL_PROFILE` canonical 名单 → 会让覆盖率矩阵行数 8→36、红格 20→100（假缺口淹没真缺口）。详见 docs/superpowers/specs/2026-09-18-spec-review.md。
