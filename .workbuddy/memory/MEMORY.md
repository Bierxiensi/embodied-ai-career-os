# 项目长期记忆 · Embodied AI Career OS（第11版，2026-09-22）

## 战略现状
- v3.2（09-21 用户三裁决）：确认留任 → **当前模式已切 long_term_transition**（active=llm/vlm/phd，frozen=空），job_hunt 为历史。在职转型窗口 2026.09–2027.03；关键节点 2026-12 答辩、PhD 申请季 26秋–27春。
- 赛道：llm 主攻 Post-Training（required_skills 13 项，已补 RAG/Agent Application）；vlm 卡位；ai-algo 保底；embodied frozen。**phd 故意不进 TARGET_ROLES**（博士就绪度=六维研究匹配，归 Phase 1 博士模块），在 long_term active 里仅占位。
- 🔴 long_term 的 frozen_track_keys 必须为空（`test_only_career_mode_switch_changes_the_range` 硬约束）。
- 匹配分**双轨已落地**（v3.2）：match_pct=推进度 + strict_pct/qualified_count/required_count=达标率（api/job_hunt.py roles_out；前端 JobsBoard 赛道卡 + Dashboard KPI 双显）。实测 llm 67%/23%(3/13)、vlm 54%/14%、ai-algo 75%/20%、embodied 38%/0%。
- 内核突击收口 6 考点：KV Cache/FlashAttention/PagedAttention/FSDP-ZeRO/Quantization/MoE → level 3，绑 Mini Post-Training Lab（记于 target_roles.py v3.2 注记）。
- v2.1 净新增四块：**博士模块（Phase 1 已落地 2026-09-21，hy3 会话全栈完成并经审计零回归**：models/phd.py 三表 + 迁移 0021-0023 + 六维引擎 agents/phd/agent.py + /api/phd CRUD+match + 前端 /phd 页；8 导师中 5 个"待确认"占位、deadline 多为空，**真实数据喂入是当前最高优先**）→ **风险雷达+Career ROI（Phase 2 已落地 2026-09-21：core/risk.py 七维 + core/career_roi.py + api/risk.py + 前端 RiskRadar/RoiTaskList；迁移 0024/0025 补 PhDAdvisor.contacted/contact_date）** → 技能依赖图+统一落地页（Phase 3 待做）；90% 能力已存在，**禁止重写**。施工计划 docs/CAREER_OS_V2_DEVELOPMENT_PLAN.md。
- **hy3（低端模型）协作协议（09-21 审计后升级）**：授权 T0-T3 + T4 前端组件(<200行)；T5 架构/口径留高端。其 8 项声称全真、守全部硬规则、能自纠错；流程缺陷=收尾不重启后端/只跑子集测试/日志写错日期。任务包必须附「完成后必做」：重启+curl 新端点、全量 pytest 贴结果、tsc/eslint 贴 RC、日志写当天、git diff --stat 核对范围。审计详情 docs/hy3质量审计与后续规划-2026-09-21.md。

## 硬规则
- 口径同源：services/action_planning/task_scope.py 唯一权威（排除制，禁白名单/禁路由再拼 track_key）；summary 须与列表同源断言。
- 🔴 **数字口径单一真源**（09-22 修）：题库目标只在 `agents/interview/engine.QUESTION_CATEGORY_TARGETS` 手改；`CORE_TARGET`（=核心分类目标和）与 `TARGET_TOTAL`（供 `api/plan.py` 的 `TARGET_QUESTIONS`）**都是派生**。**禁止在别处再写死 150/80** —— 此前 plan.py 另有一份独立 `TARGET_QUESTIONS = 150`，文档还误称"只改一处"。护栏 = `test_p3_question_coverage.py::test_targets_are_single_sourced_and_derived`。
- 🔴 **题库定位已裁决（09-22）：不当 KPI，降级为「存档 + 按需自测」**。用户留任后只需在需要时抽题练手、看学习效果。前端 150 题目标 / 红格缺口 / 核心必达的 KPI 叙事已全部拆除（`4a3982f`）。
- 🔴 **接口"早就存在" ≠ 接口正确**（09-22 血泪）：所有 JSON 端点**必须走 `ok(...)` 包装**，包括**空数据分支**。`apiClient.ts:67` 是 `if (!body.success) throw new ApiError(...)` —— 裸返回 Pydantic 模型（无 `success` 字段）会被判为失败并抛错。`/api/interview/practice/stats` 空库分支就踩了这个坑，因长期无人调用而潜伏，一接前端即让"零练习记录"的新用户整页报错。
- 🔴 **接死代码前必须实测其真实响应形状**（同上）：前后端各有一批"定义了但从未被调用"的函数/端点，其正确性从未被验证。接上前先 curl 一遍真实返回。
- 🔴 测试隔离（09-22 血泪）：`/api/plan/today` **只返回当天**的 artifacts（按 plan_day_id 过滤）。任何"清空某天产出"的 helper **必须显式传 seq**，用不带参数的 `_today()`（=日历当天）去清别的 day 会**静默变成空操作**。当日就因此误报过 `completed_days`。
- 用例**不得依赖墙钟**：`/api/plan/today` 不带参数走日历口径（`_resolve_day_index`），随日期推移会指向未种下的课程日 → fixture 必须动态补种"日历推导当天"（09-22 修好 4 个长期红用例）。
- 🔴 测试不得写开发库（conftest 已指向临时库且会话级守卫拒绝 data/app.db）；pytest 后核对开发库指纹 md5（当前基线 `65f7158f438b37e730bcc3777edbca4d`——09-22 题库种子后；迁移 ADD COLUMN / 种子写入都会改指纹，属正常）。
- 迁移：下一条 **0026**（0016-0025 已用：0021-0023=博士三表，0024-0025=advisor contacted 两列，见 Phase 2 任务包）；单语句；写 SQLite 写法；必跑 tests/test_migration_dialect_compat.py。
- SKILL_PROFILE 是 **SkillProfile 对象列表**——匹配 `.name`，勿当字符串遍历（09-21 修过 engine.py:79 与 interviews.py:242 两处）。
- Pydantic v2 from_attributes + 未 flush ORM → `@field_validator(mode="before")` 回落处理 NULL。
- service 层不透传 payload；apiClient 不做 key 转换，create/patch 显式列 snake_case。
- 护栏测试先剥注释+命中哨兵断言；**重构改名后护栏断言要同步**（resolveTrack→resolvePrimaryTrack，09-21 已同步）。
- 同一文件禁止并行 Edit；改后 Grep 复读落盘。**多会话并行开发常发生，动手前必复读目标文件**（09-21 presets/target_roles/MY_CONTEXT 曾被并发会话更新）。
- 联调一律 127.0.0.1（不用 localhost）；杀进程 `MSYS_NO_PATHCONV=1 taskkill /F /T /PID`；改 ORM/配置后重启后端（无 --reload）。
- .workbuddy/tmp/ 已在 .gitignore。岗位 tier 跟赛道；JobPostingPatch 无 PATCH 路由（改 tier 只能删了重录）。

## 环境 / 门禁
- 后端启动（后台）：`backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000`；本地 SQLite backend/data/app.db。
- pytest：chdir backend + venv python（python -c os.chdir 包一层）；**基线（09-22）= 326 passed / 0 failed / 2 skipped**（321 为口径修复后、326 含新 `test_practice_stats.py` 5 例）。此前长期恒 4 failed（test_plan_api 日期驱动「课程日 Day N 不存在」，N 随日历推进），已于 09-22 连根修掉（见硬规则"用例不得依赖墙钟"）。
- 跑 pytest 最稳姿势：`.workbuddy/tmp/run_pytest.py [目标...]`（managed python 调 venv python，落盘再读，顺带核对开发库指纹；不传目标跑全量）。**Git Bash 缺 mkdir/tail**，别用管道。
- 写后端测试的两个可靠手法（09-22）：①需要"干净库"时用 `contextmanager` 覆盖 `get_db` 指向**临时文件库**并 `Base.metadata.create_all` —— **别用 `sqlite://` 内存库**，TestClient 把同步端点丢线程池，内存库连接不共享、表会"消失"；②在共享隔离库上只做**增量断言** + 自清理，免受同会话其他模块影响。
- 前端门禁 node 直调（npm shim 进 WSL 黑名单）：`node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json` + `node node_modules/eslint/bin/eslint.js <files>`（cwd=frontend；managed node 绝对路径 + python os.chdir 包装）。**next build 本机跑不了（fonts.googleapis.com 不通）→ 验收以 tsc+eslint 双 RC0 为准**；eslint 的 `react-hooks/error-boundaries`（page 的 try/catch 内 JSX）是**全项目基线**（未改页同样报），非回归。
- Git Bash 残缺（ls/head/cd/dirname 缺失）→ 文件操作走 Read/Write/Edit/Glob/Grep，命令用 managed python 绝对路径。
- ⚠️ 本机 urllib/requests 走系统 HTTP 代理 → 打 127.0.0.1:8000 报 **502 Bad Gateway**（并非服务未启动），须 `build_opener(ProxyHandler({}))` 直连；Bash 工具非交互运行会回收 Popen 子进程 → 后端常驻必须 `run_in_background=true` + 包装进程 `Popen(...).wait()`，单跑 `os.execv` 约 8s 即被回收。

## 数据与缺陷
- 单一源：skill_profile.py（技能等级/证据）+ target_roles.py（赛道，含 TECH_BLACKLIST/SPRINT 窗口）+ plan_30d.py（课程唯一源，seq 不绑日历）。
- 开发库基线：skills **50** / plan_days 30 / **interview_questions 150（09-22 D2 三连修后：LLM 50 / MM 30 / Project 40 / Coding 30，四类 gap 全 0，覆盖率 core_done=80）** / tasks 23 / job_applications 3（JD#7 华夏泰科 + JD#8 电价预测均 rejected）/ **research_directions 6 / phd_targets 13 / phd_advisors 8（09-21 博士种子）** / practice_records 7（自测答题记录，源 `/api/interview/practice`）。
- 待修：巨型组件（JobsBoard 996 行等 7 个 >400 行）；**硬编码色值**（09-22 实测口径：`frontend/src/**/*.ts(x)` 内 `#hex` 或 `rgb/rgba(` 共 **200 处 / 33 文件**，不含 globals.css；本批已从 QuestionBoard 删掉 4 个 RED/GREEN 常量）；ViewRole 死代码 + SubNav 把视角 trackKey 传给 Planner 写接口（待裁决）。
- ✅ **题库三块已解除阻塞（09-22 用户裁决：不当 KPI，只按需自测）**——不再是待拍板项，不构成阻塞。留档备查：**D1** Project 错挂 **14 道** LLM 内容（脚本 10 道 + 历史 id 74 监控 / 75 A-B / 76 多轮对话 / 110 持续预训练，挪走会让 Project 掉到 26/40）；**D2 三组近重复题**（74↔140 / 75↔141 / 76↔139，与 D1 是同一动作的两面，宜先去重再挪）；**D3** `is_verified` 全库 0（**需闭卷答题，非代码可修**）。若哪天真要动，记住 D1 必须与 targets 同改才不会留缺口。
- 已修（09-21）：job-postings 500（并发会话修）、SKILL_PROFILE 遍历 ×2、viewrole 护栏、dashboardService 边界注释。已修（09-22）：D2 题库脚本三连修（`3d567e8`，core_done 78→80、110→150 题）、`a.md` 入 .gitignore（`03e9ac4`）、**口径单一真源化（E1/E2）+ 文档纠错（E3/E4）+ 测试护栏与隔离修复（E5/E6/E7）→ pytest 首次全绿**、**题库去 KPI 化 + 接入自测学情（`4a3982f`，5 文件：PracticeStatsCard 新增 / QuestionBoard 覆盖率矩阵改中性分布 / questions 页并行拉 stats；含修 `practice/stats` 空库分支漏 `ok()` 包装的真实缺陷 + 新增 `test_practice_stats.py` 5 例）**，详见 docs/口径与题库问题清单-2026-09-22.md。
- 数据缺口：中科院地理所 2 年 5 个月仍不在 resume_facts（9 条）；JD#9 track='agent' 漂移任务。

## 文档索引
- 全量梳理+低端模型任务包（6 个四元组）：docs/项目梳理与迭代指导-2026-09-21.md
- 背景与能力结构：docs/候选人背景分析-2026-09-17.md；产品诊断：docs/产品设计诊断-2026-09-17.md
- v2.1 四件套：docs/CAREER_OS_V2_{INCREMENTAL_PRD,ARCHITECTURE,AGENT_SPEC,DEVELOPMENT_PLAN}.md
- 模式 PRD：docs/PRD_CAREER_OS_MODES.md；实施约束：docs/CODEBUDDY_IMPLEMENTATION_CONSTRAINTS.md / CODEX_MODULAR_DESIGN_STANDARD.md / CODEX_READABILITY_STANDARD.md
- Spec 工作流：docs/superpowers/specs/（审 spec 一律先实测代码/DB，别信 spec 自述）
- **口径与题库问题清单（09-22）**：docs/口径与题库问题清单-2026-09-22.md（E1-E7 已修 / D1-D3 已解除阻塞，留档备查）
