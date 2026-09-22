# 项目长期记忆 · Embodied AI Career OS（第13版，2026-09-22）

## 战略现状
- v3.2（09-21 用户三裁决）：确认留任 → **当前模式 long_term_transition**（active=llm/vlm/phd，frozen=空）。在职转型窗口 2026.09–2027.03；关键节点 2026-12 答辩、PhD 申请季 26秋–27春。
- 赛道：llm 主攻 Post-Training（required_skills 13 项）；vlm 卡位；ai-algo 保底；embodied frozen。**phd 故意不进 TARGET_ROLES**（博士就绪度=六维研究匹配，归博士模块）。🔴 long_term 的 frozen_track_keys 必须为空（`test_only_career_mode_switch_changes_the_range`）。
- 匹配分**双轨**：match_pct=推进度 + strict_pct/qualified_count/required_count=达标率（api/job_hunt.py roles_out；前端 JobsBoard + Dashboard 双显）。实测 llm 67%/23%(3/13)、vlm 54%/14%、ai-algo 75%/20%、embodied 38%/0%。
- 内核突击收口 6 考点：KV Cache/FlashAttention/PagedAttention/FSDP-ZeRO/Quantization/MoE → level 3，绑 Mini Post-Training Lab。
- v2.1 四块：**Phase 1 博士模块已落地**（models/phd.py 三表 + 迁移 0021-0023 + 六维引擎 + /api/phd CRUD+match + /phd 页）；**Phase 2 风险雷达+Career ROI 已落地**（core/risk.py 七维 + career_roi.py + api/risk.py + RiskRadar/RoiTaskList；迁移 0024/0025=advisor contacted 两列）；**Phase 3 技能依赖图+统一落地页已落地（09-22）**——迁移 0027 `skill_dependency`（52 边）+ skill_profile 六域 + `services/readiness`（就绪度唯一实现，job_hunt/plan/risk/dashboard 共用）+ `/api/transition/dashboard` + /today 收口五区（①职业进度+雷达 ②当前工作 ③学术与博士 ④ROI ⑤Risk）。**Phase 3 收口后 v2.1 四块全齐**。
- **博士录入界面已建好（09-22 用户四裁决①）**：PhDEntryPanel（院校+导师双表单，router.refresh 联动）+ PhDAdvisorBoard 联系标记/删除按钮 + phdService CRUD。**用户自己录真实数据**：北航无联系人、北大过高、倾向北科大等 211；13 所 deadline 待补录。
- **hy3 协作协议**：授权 T0-T3 + T4 前端组件(<200行)；T5 留高端。任务包必附「完成后必做」：重启+curl、全量 pytest、tsc/eslint RC、日志写当天、git diff --stat。详见 docs/hy3质量审计与后续规划-2026-09-21.md。

## 硬规则
- 口径同源：services/action_planning/task_scope.py 唯一权威（排除制，禁白名单/禁路由再拼 track_key）。
- 🔴 **数字口径单一真源**：题库目标只手改 `agents/interview/engine.QUESTION_CATEGORY_TARGETS`（现 {LLM:61, MM:30, Project:26, Coding:30}，**描述性分布，非 KPI**）；CORE_TARGET/TARGET_TOTAL/plan.py 的 TARGET_QUESTIONS 全派生。护栏 `test_targets_are_single_sourced_and_derived`。
- 🔴 **接口"早就存在"≠接口正确**：所有 JSON 端点必须走 `ok(...)` 包装**包括空数据分支**（apiClient.ts:67 无 success 即抛错）。**接死代码前必须实测真实响应形状**——前端 getQuestionSources 指向的后端端点曾经从未存在（09-22 已连前端带后端一起删）。
- 🔴 测试隔离：`/api/plan/today` 只返回当天 artifacts；清空 helper 必须显式传 seq，不带参数的 `_today()` 清别的 day 会静默空操作。用例**不得依赖墙钟**（fixture 动态补种日历推导当天）。
- 🔴 测试不得写开发库；pytest 后核对开发库指纹 md5（**当前基线 `d033d6320d41f3c8088e5ad42f18017b`**——09-22 迁移 0027 落库后；迁移/种子写入改指纹属正常）。
- 🔴 **共享测试库会被同会话其他用例改**：依赖"库即种子态"的绝对锚点（如 llm 67%/23%）必须自己防污染，或让改库的用例自清理。实证：`test_e2e_v2_learning_loop` 的 reviewer 晋级把 DPO 1→2 不还原 → 锚点假失败 69!=67。定位手法：临时 pytest 插件在 `pytest_runtest_teardown` 逐用例比对表快照并打印 diff（`.workbuddy/tmp/detect_leak.py`）。
- 迁移：下一条 **0028**；单语句 SQLite 写法；必跑 test_migration_dialect_compat.py（按迁移文件参数化，新增迁移+1 用例属正常）。
- SKILL_PROFILE 是 **SkillProfile 对象列表**——匹配 `.name`，勿当字符串遍历。
- Pydantic v2 from_attributes + 未 flush ORM → `@field_validator(mode="before")` 回落 NULL。
- service 层不透传 payload；apiClient 不做 key 转换，create/patch 显式列 snake_case。
- 🔴 **回查原则**：题目发给用户前被改写/生成的流程，判分必须用**发出去的那一份**（quiz_session_questions 表，迁移 0026）；对外声明的题型必须与实际渲染一致，做不到就降级 open。
- 护栏测试先剥注释+命中哨兵断言；**重构改名后护栏断言要同步**。
- 同一文件禁止并行 Edit；改后 Grep 复读落盘。**多会话并行开发常发生，动手前必复读目标文件**。
- 联调一律 127.0.0.1；杀进程 `MSYS_NO_PATHCONV=1 taskkill /F /T /PID`；改 ORM/配置后重启后端（无 --reload）。
- .workbuddy/tmp/ 已在 .gitignore。岗位 tier 跟赛道；JobPostingPatch 无 PATCH 路由（改 tier 只能删了重录）。

## 环境 / 门禁
- 后端启动（后台）：`backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000`；SQLite backend/data/app.db。
- pytest：chdir backend + venv python；**基线（09-22 Phase 3 后）= 374 passed / 0 failed / 2 skipped**。最稳姿势 `.workbuddy/tmp/run_pytest.py [目标...]`（顺带核对开发库指纹）。
  - ⚠️ 全量跑会把 `%TEMP%\pytest-of-*` 的 garbage 累积到 >50 项，触发 safe-delete 护栏使 **pytest exit=1（进度全是点、无 F，纯误报）**；加 `--basetemp=../.workbuddy/tmp/pytest-base` 把临时根挪进工作区即恢复 exit=0。
- 写后端测试两手法：①干净库用 contextmanager 覆盖 get_db 指**临时文件库**（**别用内存库**，TestClient 线程池连接不共享）；②共享隔离库只做增量断言+自清理。
- 前端门禁 node 直调：`node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json` + `node node_modules/eslint/bin/eslint.js <files>`（cwd=frontend，managed node 绝对路径）。**next build/dev 本机都跑不了（fonts.googleapis.com 不通）→ 验收 tsc + eslint「除基线外零新增」**。
  - 基线噪音只有两类：`react-hooks/error-boundaries`（**16 个 page 全命中**，try/catch 里建 JSX 的既定写法，非回归）+ `components/Dashboard.tsx` 的 `skills` prop 未使用（历史既有）。除这两类外出现任何规则即为回归。
  - 类型检查兜不住运行时行为时（如"六域雷达真的出 6 根轴"）：单独 `tsc src/services/xxx.ts --outDir` 编译成 JS，再让 node 直吃真实 HTTP 响应跑断言（见 `.workbuddy/tmp/radar_smoke.js`）。
- Git Bash 残缺（ls/head/cd/dirname/mkdir/tail/**sleep** 缺失）→ 文件操作走 Read/Write/Edit/Glob/Grep，命令用 managed python 绝对路径。
- ⚠️ 本机走系统代理 → 打 127.0.0.1:8000 须 `build_opener(ProxyHandler({}))` 直连；后端常驻必须 `run_in_background=true` + `Popen(...).wait()` 包装（单跑 os.execv 约 8s 被回收）。

## 数据与缺陷
- 单一源：skill_profile.py + target_roles.py + plan_30d.py（seq 不绑日历）；**skill_graph.py 的 SKILL_EDGES（52 边）是依赖图单一真源**（投影进 skill_dependency 表，禁止反向从表推）；**transition_context.py 是答辩日/导师窗口/在职事实单一真源**（core/risk.py 也用它）。
- 开发库基线：skills 50（43 标六域 / 7 未标=冻结具身）/ skill_dependency 52 / plan_days 30 / **interview_questions 147（09-22 D1/D2 手术：删近重复 74/75/76 + 11 道 LLM 内容题 Project→LLM；终态 LLM 61/MM 30/Project 26/Coding 30，gap 全 0；备份 app.db.bak-20260922-d1）** / tasks 23 / job_applications 3 / research_directions 6 / phd_targets 13 / phd_advisors 8 / practice_records 7 / quiz_session_questions 表已建（空表）。
- ✅ 09-22 四裁决已落地：①博士录入界面（用户自录数据）；②死接口 getQuestionSources/getRecommendations 前后端全删；③ViewRole 整体删除（lib/viewRole.ts 删、护栏改为"不得复活"断言）；④D1/D2 题库手术一次性完成。
- ✅ 09-22 Phase 3 已落地：技能依赖图（迁移 0027 + 种子脚本 + 18 例护栏）+ 统一落地页五区（today 页四路并行取数；`test_transition_dashboard` 19 例，核心是 `test_readiness_is_identical_to_job_hunt` 断言落地页与求职看板逐字同源）。
- 待修：巨型组件（JobsBoard 708 行 / QuestionBoard 678 / ResumeBoard 647 / JDBoard 610 / TodayBoard 605 等仍 >400 行）；硬编码色值（09-22 口径 200 处/33 文件，已清 QuestionBoard 4 处 + PhDAdvisorBoard ~12 处；Phase 3 顺手修 `RoiTaskList` 的**未定义令牌** `var(--radius-card)` → `var(--radius-item-md)`）；D3 is_verified 全库 0（需用户闭卷答题，非代码可修）。
- 数据缺口：中科院地理所 2 年 5 个月仍不在 resume_facts（9 条）；JD#9 track='agent' 漂移任务。
- 历史执行记录（E1-E7 口径修复、题库去 KPI 化 `4a3982f`、小测验接通 D4 等）详见 docs/口径与题库问题清单-2026-09-22.md 与 docs/项目梳理与迭代指导-2026-09-22.md §四。

## 文档索引
- 全量梳理+任务包：docs/项目梳理与迭代指导-2026-09-21.md（v1，含 6 个四元组任务包）
- **09-22 梳理 v2 + 四裁决执行结果**：docs/项目梳理与迭代指导-2026-09-22.md
- 背景与能力结构：docs/候选人背景分析-2026-09-17.md；产品诊断：docs/产品设计诊断-2026-09-17.md
- v2.1 四件套：docs/CAREER_OS_V2_{INCREMENTAL_PRD,ARCHITECTURE,AGENT_SPEC,DEVELOPMENT_PLAN}.md
- 模式 PRD：docs/PRD_CAREER_OS_MODES.md；实施约束：docs/CODEBUDDY_IMPLEMENTATION_CONSTRAINTS.md / CODEX_MODULAR_DESIGN_STANDARD.md / CODEX_READABILITY_STANDARD.md
- 口径与题库问题清单（09-22）：docs/口径与题库问题清单-2026-09-22.md（E1-E7/D1-D4 全收口，留档备查）
- Spec 工作流：docs/superpowers/specs/（审 spec 一律先实测代码/DB，别信 spec 自述）
