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
- 🔴 测试不得写开发库；pytest 后核对开发库指纹 md5（**当前基线 `fb970ef302689a75677a970fdb7776ec`**——09-22 晚数据手术〔删演示投递/985 目标〕+ 录入王恒后；迁移/种子/用户数据变更改指纹属正常）。
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
- 🔴 **提交纪律（09-22 血泪）**：提交前必 `git status --short` 核对；**只 `git add <显式文件路径>`，禁 `git add -A` / `git add .`**。并发会话常同时改同一仓库，全量 add 会把别人未完成的工作捎带进自己的提交（今日 `2c7b01d`：57 文件混合提交，message 只写了 Phase 3）。若工作区有他人改动，只提交自己的并在 message 注明。

## 环境 / 门禁
- 后端启动（后台）：`backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000`；SQLite backend/data/app.db。
- pytest：chdir backend + venv python；**基线（09-22 晚）= 377 passed / 0 failed / 2 skipped**（374 + `test_p3_target_track_integrity.py` 3 例）。最稳姿势 `.workbuddy/tmp/run_pytest.py [目标...]`（顺带核对开发库指纹）。
  - ⚠️ 全量跑会把 `%TEMP%\pytest-of-*` 的 garbage 累积到 >50 项，触发 safe-delete 护栏使 **pytest exit=1（进度全是点、无 F，纯误报）**；加 `--basetemp=../.workbuddy/tmp/pytest-base` 把临时根挪进工作区即恢复 exit=0。
- 写后端测试两手法：①干净库用 contextmanager 覆盖 get_db 指**临时文件库**（**别用内存库**，TestClient 线程池连接不共享）；②共享隔离库只做增量断言+自清理。
- 前端门禁 node 直调：`node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json` + `node node_modules/eslint/bin/eslint.js <files>`（cwd=frontend，managed node 绝对路径）。**next build/dev 本机都跑不了（fonts.googleapis.com 不通）→ 验收 tsc + eslint「除基线外零新增」**。
  - 基线噪音实测（09-22 晚，`core`/`components` 目录级扫描）：`react-hooks/error-boundaries`（**16 个 page 全命中**，try/catch 里建 JSX 的既定写法）+ `ResumeBoard.tsx:175` 的 **`react-hooks/set-state-in-effect`（error 级）** + 6 个 `no-unused-vars` 警告（ApplicationsBoard/JobsBoard/MilestoneTimeline×2/ReportsBoard×2/TaskList）。**自证手法**：`git show HEAD:<file>` 写临时文件对跑 eslint，问题一一对应即为既有（脚本 `.workbuddy/tmp/head_lint_compare.py`，跑完自清理）。
  - 类型检查兜不住运行时行为时（如"六域雷达真的出 6 根轴"）：单独 `tsc src/services/xxx.ts --outDir` 编译成 JS，再让 node 直吃真实 HTTP 响应跑断言（见 `.workbuddy/tmp/radar_smoke.js`）。
- Git Bash 残缺（ls/head/cd/dirname/mkdir/tail/**sleep** 缺失）→ 文件操作走 Read/Write/Edit/Glob/Grep，命令用 managed python 绝对路径。
- ⚠️ 本机走系统代理 → 打 127.0.0.1:8000 须 `build_opener(ProxyHandler({}))` 直连；后端常驻必须 `run_in_background=true` + `Popen(...).wait()` 包装（单跑 os.execv 约 8s 被回收）。

## 数据与缺陷
- 单一源：skill_profile.py + target_roles.py + plan_30d.py（seq 不绑日历）；**skill_graph.py 的 SKILL_EDGES（52 边）是依赖图单一真源**（投影进 skill_dependency 表，禁止反向从表推）；**transition_context.py 是答辩日/导师窗口/在职事实单一真源**（core/risk.py 也用它）。
- 开发库基线：skills 50（43 标六域 / 7 未标=冻结具身）/ skill_dependency 52 / plan_days 30 / **interview_questions 147（09-22 D1/D2 手术：删近重复 74/75/76 + 11 道 LLM 内容题 Project→LLM；终态 LLM 61/MM 30/Project 26/Coding 30，gap 全 0；备份 app.db.bak-20260922-d1）** / tasks 23 / **job_applications 3（09-22 晚清理：id 8-11 经用户确认是演示数据已删，余 3 条真实：华夏泰科/电价预测J10856 均 rejected、大禹节水 applied）** / research_directions 6 / **phd_targets 8（09-22 晚瘦身：删 985 五所 北大/清华/人大×2/北理工；余 211×4 北邮/中石大/北科大/北交大 + 市属 北信科 + 中科院 国科大自动化所 + 985 北航本校〔有意保留：本校通道〕。**⚠️ deadline 仍多为 NULL 或已过期，须用户补录 2027 周期**）** / **phd_advisors 5（4 条占位 + 王恒〔北科大真实导师，09-22 录入，match 89 分/A 级〕；contacted 全 0）** / practice_records 7 / quiz_session_questions 表已建（空表）。
- ✅ 09-22 四裁决已落地：①博士录入界面（用户自录数据）；②死接口 getQuestionSources/getRecommendations 前后端全删；③ViewRole 整体删除（lib/viewRole.ts 删、护栏改为"不得复活"断言）；④D1/D2 题库手术一次性完成。
- ✅ 09-22 Phase 3 已落地：技能依赖图（迁移 0027 + 种子脚本 + 18 例护栏）+ 统一落地页五区（today 页四路并行取数；`test_transition_dashboard` 19 例，核心是 `test_readiness_is_identical_to_job_hunt` 断言落地页与求职看板逐字同源）。
- 🔴 **剩余缺陷全清单（v3 实测口径，2026-09-22 傍晚）**——v1 的 D1-D10 中 D1/D2/D3/D4/D9/D10 已全部偿清：
  - **D5** 中科院地理所 2 年 5 个月不在 `resume_facts`（`db/base.py` 种子缺该段）→ 需用户提供事实
  - **D6** ✅ **已封口（09-22 晚实测：缺陷早已不存在**——job_postings 8 条 track 全合法、tasks 零漂移**）**；已补护栏 `tests/test_p3_target_track_integrity.py`（赛道集合哨兵 + 岗位 track + 任务 track_key 三层断言）。**教训：缺陷清单本身也会过时，护栏比清单可靠。**
  - **D7** 巨型组件 **8 个 >400 行**：JobsBoard 708 / QuestionBoard 678 / ResumeBoard 647 / JDBoard 610 / TodayBoard 605 / ApplicationsBoard 452 / PlanBoard 425 / ReportsBoard 424
  - **D8** 硬编码色值：**180 处 / 32 文件**，其中 **95 处已令牌化（09-22 晚，25 文件，同值替换=浅色零变化）**；余 **85 处无令牌**（见 X5）
  - **X1** 博士库时间维度失效（deadline 全过期）→ 用户补数据 + 前端区分"已过期/未录入"两态
  - **X2** ✅ 已修：`career-os-milestone` skill 过时（基线 326→374、旧指纹、node 22.12→22.22.2-3、ViewRole 整节改为"已删除存证"）
  - **X3** 提交卫生：今日 `2c7b01d` 是 **57 文件 / +5078 行**的混合提交（并发会话把另一会话的四裁决工作一并 `git add -A` 捎带，message 只写 Phase 3）→ 纪律：**提交前必 `git status --short` 核对，只 add 显式文件路径，禁 `git add -A` / `git add .`**
  - **X4** 🔴 **六维匹配引擎奖励数据缺失（09-22 晚实测发现，未修，待用户裁决）**：`agents/phd/agent.py:_timeline_score` 对 `deadline is None` 返回 **70**，而"已过期"只给 **20** → **越不录截止日，排名越靠前**。实测对照：北邮（录了、已过期）timeline=20，王恒（未录）timeline=70。建议修法 `None → 50` + 输出 gap"截止日未录入"。**另一发现：六维中 geo/publication/in_service 三维在同池候选里近乎恒定（全北京、全 none），0.40 权重是常量 → 实际只有 direction_fit(0.30)+tier(0.15) 在排序**。
  - **X5** 色值债务的真实结构：180 处里只有 95 处有对应令牌；剩 85 处是项目**从未定义**的 Tailwind 原色（`#3b82f6`/`#ef4444`/`#22c55e`/`#6b7280`/`#e5e7eb` 等）→ 属"设计系统扩容"而非"清偿债务"，**不可派低端模型硬替换**（会诱导自造令牌）
  - **D3** `is_verified` 全库 0（需用户闭卷答题，非代码可修）
- 历史执行记录（E1-E7 口径修复、题库去 KPI 化 `4a3982f`、小测验接通 D4 等）详见 docs/口径与题库问题清单-2026-09-22.md 与 docs/项目梳理与迭代指导-2026-09-22.md §四。

## 文档索引
- 全量梳理+任务包：docs/项目梳理与迭代指导-2026-09-21.md（v1，含 6 个四元组任务包）
- 09-22 梳理 v2 + 四裁决执行结果：docs/项目梳理与迭代指导-2026-09-22.md
- **⭐ 09-22 梳理 v3（最新，实测快照 + 剩余工作派发包）**：docs/项目梳理与迭代指导-2026-09-22-v3.md —— 定位：v2.1 四块收口后，边际价值转向「真数据 / 技术债 / 协作卫生」三条腿；含 D5-D8+X1-X3 全清单、P0-P3 路线、3 个可直接下发的四元组任务包、防坑清单 11-13 条
- 背景与能力结构：docs/候选人背景分析-2026-09-17.md；产品诊断：docs/产品设计诊断-2026-09-17.md
- v2.1 四件套：docs/CAREER_OS_V2_{INCREMENTAL_PRD,ARCHITECTURE,AGENT_SPEC,DEVELOPMENT_PLAN}.md
- 模式 PRD：docs/PRD_CAREER_OS_MODES.md；实施约束：docs/CODEBUDDY_IMPLEMENTATION_CONSTRAINTS.md / CODEX_MODULAR_DESIGN_STANDARD.md / CODEX_READABILITY_STANDARD.md
- 口径与题库问题清单（09-22）：docs/口径与题库问题清单-2026-09-22.md（E1-E7/D1-D4 全收口，留档备查）
- Spec 工作流：docs/superpowers/specs/（审 spec 一律先实测代码/DB，别信 spec 自述）
