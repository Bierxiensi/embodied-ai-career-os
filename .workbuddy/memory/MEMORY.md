# 项目长期记忆 · Embodied AI Career OS（第9版，2026-09-21）

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
- pytest：chdir backend + venv python（python -c os.chdir 包一层）；**基线 = 恒 4 failed（仅 test_plan_api 日期驱动「课程日 Day N 不存在」，N 随日历推进；临时库只种 day 1/2/3）/ 2 skipped**；09-21 Phase 2 后实测 316 passed（新增 test_risk/test_career_roi）。
- 前端门禁 node 直调（npm shim 进 WSL 黑名单）：`node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json` + `node node_modules/eslint/bin/eslint.js <files>`（cwd=frontend；managed node 绝对路径 + python os.chdir 包装）。**next build 本机跑不了（fonts.googleapis.com 不通）→ 验收以 tsc+eslint 双 RC0 为准**；eslint 的 `react-hooks/error-boundaries`（page 的 try/catch 内 JSX）是**全项目基线**（未改页同样报），非回归。
- Git Bash 残缺（ls/head/cd/dirname 缺失）→ 文件操作走 Read/Write/Edit/Glob/Grep，命令用 managed python 绝对路径。
- ⚠️ 本机 urllib/requests 走系统 HTTP 代理 → 打 127.0.0.1:8000 报 **502 Bad Gateway**（并非服务未启动），须 `build_opener(ProxyHandler({}))` 直连；Bash 工具非交互运行会回收 Popen 子进程 → 后端常驻必须 `run_in_background=true` + 包装进程 `Popen(...).wait()`，单跑 `os.execv` 约 8s 即被回收。

## 数据与缺陷
- 单一源：skill_profile.py（技能等级/证据）+ target_roles.py（赛道，含 TECH_BLACKLIST/SPRINT 窗口）+ plan_30d.py（课程唯一源，seq 不绑日历）。
- 开发库基线：skills **50** / plan_days 30 / **interview_questions 150（09-22 D2 三连修后：LLM 50 / MM 30 / Project 40 / Coding 30，四类 gap 全 0，覆盖率 core_done=80）** / tasks 23 / job_applications 3（JD#7 华夏泰科 + JD#8 电价预测均 rejected）/ **research_directions 6 / phd_targets 13 / phd_advisors 8（09-21 博士种子）**。
- 待修：巨型组件（JobsBoard 996 行等 7 个 >400 行）；81 处硬编码色值；ViewRole 死代码 + SubNav 把视角 trackKey 传给 Planner 写接口（待裁决）。**🔴 D2 题库三连修已于 09-22 完成**（commit `3d567e8`）；其**第二批**（Project 重划分类：10 道 LLM 理论题→LLM，见 spec-review §1.4/§B4）仍待做——注意该步会把 core_done 推到 90 且 Project 落到 30/40，前置是先定 17 个新技能归属（现按 B 路线改挂已有 canonical 技能）。
- 已修（09-21）：job-postings 500（并发会话修）、SKILL_PROFILE 遍历 ×2、viewrole 护栏、dashboardService 边界注释。已修（09-22）：D2 题库脚本三连修（`3d567e8`，core_done 78→80、110→150 题）、`a.md` 入 .gitignore（`03e9ac4`）。
- 数据缺口：中科院地理所 2 年 5 个月仍不在 resume_facts（9 条）；JD#9 track='agent' 漂移任务。

## 文档索引
- 全量梳理+低端模型任务包（6 个四元组）：docs/项目梳理与迭代指导-2026-09-21.md
- 背景与能力结构：docs/候选人背景分析-2026-09-17.md；产品诊断：docs/产品设计诊断-2026-09-17.md
- v2.1 四件套：docs/CAREER_OS_V2_{INCREMENTAL_PRD,ARCHITECTURE,AGENT_SPEC,DEVELOPMENT_PLAN}.md
- 模式 PRD：docs/PRD_CAREER_OS_MODES.md；实施约束：docs/CODEBUDDY_IMPLEMENTATION_CONSTRAINTS.md / CODEX_MODULAR_DESIGN_STANDARD.md / CODEX_READABILITY_STANDARD.md
- Spec 工作流：docs/superpowers/specs/（审 spec 一律先实测代码/DB，别信 spec 自述）
