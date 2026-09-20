# Embodied AI Career OS v2.1 施工计划（Phase / Day 级）

> 配套：PRD / ARCHITECTURE / AGENT_SPEC
> 原则：小步实施、每 Phase 可独立验收、不一次实现整个 v2.1。
> 风格：每个 Day 给"目标 / 改动文件 / 验收 / 可直接复制给实施的 Prompt"。

---

## Phase 0 — 战略校准（零代码，0.5 天）
**目标**：确认"留下"后把系统切到长期转型基线。
- Day 0.1 改 `services/career_mode/presets.py`：`LONG_TERM_TRANSITION` 填 `active_track_keys=("llm","vlm","phd")` / `frozen_track_keys=("ai-algo","embodied")`；`core/target_roles.py` 新增 `TargetRole(key="phd", ...)`。
- Day 0.2 改 `docs/MY_CONTEXT.md` 截止日期与目标；`target_roles.py` 顶部加 v3.1 注记。
- 验收：`POST /api/career-mode/switch {mode_key:"long_term_transition"}` 成功；`GET /api/career-mode` 返回新模式；历史求职数据完整。
- **实施 Prompt**：「在 presets.py 给 LONG_TERM_TRANSITION 定义赛道策略（llm/vlm/phd 生效，ai-algo/embodied 冻结），并在 target_roles.py 新增 phd 赛道（计算机/控制/AI/机器人方向，frozen=False）。不要动其他逻辑，跑 pytest 验证。」

---

## Phase 1 — 博士模块（2–3 天，时间敏感）
**目标**：可录入/查看导师库、计算匹配度、看联系倒计时。
- Day 1.1 `models/phd.py`（PhDTarget/Advisor/ResearchDirection）+ 迁移（SQLite+PG 双跑）。
- Day 1.2 `schemas/phd.py` + `api/phd.py`（targets/advisors CRUD + `/match`）。
- Day 1.3 `agents/phd/agent.py`：六维匹配，复用 `agents/match/engine.py`。
- Day 1.4 种子：从 `docs/北京在职博士-*.md` 抽初始数据，写 `scripts/seed_phd.py`。
- Day 1.5 前端 `src/app/phd/page.tsx` + `PhDAdvisorBoard.tsx` + `phdService.ts`。
- 验收：建库后 `/api/phd/advisors` 返回带 `match_json`；页面展示匹配度+倒计时；`pytest` + `tsc` + `next build` 通过。
- **实施 Prompt**：「新增博士模块：models/phd.py 三张表 + 迁移 + schemas + api/phd.py（CRUD 与 /match）+ agents/phd/agent.py 六维匹配（复用 agents/match/engine.py）+ scripts/seed_phd.py（从 docs/北京在职博士-*.md 抽取初始院校/导师）+ 前端 phd 页。所有写接口 Pydantic 入参 + 测试。」

---

## Phase 2 — 风险雷达 + Career ROI（1.5–2 天）
**目标**：`/today` 顶部七维风险 + 今日最高 ROI 任务。
- Day 2.1 `core/risk.py`（七维纯函数，含 execution 连续无实验检测）。
- Day 2.2 `core/career_roi.py`（ROI 公式纯函数）。
- Day 2.3 `api/risk.py` + 改 `planner`/today 聚合（加 `roi_ranked_tasks` / `risk` 字段）。
- Day 2.4 前端 `RiskRadar.tsx`（SVG）+ `RoiTaskList.tsx` + 接入 `today/page.tsx`。
- 验收：无 experiment 连续 7 天时 execution=red；`/today` 任务按 ROI 排序。
- **实施 Prompt**：「新增 core/risk.py（七维风险评估纯函数，execution 维检测近 7 天无 experiment/code artifact）与 core/career_roi.py（ROI=技能增量×目标相关性×证据×真实项目÷时间）。在 /today 聚合中附加 risk 与 roi_ranked_tasks（Top5）。前端加 RiskRadar(SVG) 与 RoiTaskList 组件并接入 today 页。规则可跑，LLM 未配置不报错。」

---

## Phase 3 — 技能依赖图 + 统一落地页（2 天）
**目标**：SkillRadar 支持 R2 域聚合；收口 Career Transition Dashboard。
- Day 3.1 `models/skill_graph.py`（skill_dependency）+ `skill_profile` 加 `domain` 字段 + 迁移 + 种子依赖边（PyTorch→Transformer→Attention 等）。
- Day 3.2 SkillRadar 支持 R2（域聚合，long_term 模式）；R1 保持（job_hunt）。
- Day 3.3 统一 `today/page.tsx`：职业进度 + 当前工作 + 学术(硕士/博士) + ROI 任务 + Risk（即 v2.0 §33 mockup）。
- 验收：long_term 模式看 R2 六域雷达；落地页五区齐全；口径一致性（readiness 同步）。
- **实施 Prompt**：「新增 skill_dependency 表与 skill_profile.domain 字段（6 域：LLM基础/微调对齐/推理工程/多模态/工程交付/科研底座）+ 种子依赖边。SkillRadarCard 支持 R2 域聚合（long_term 模式）与 R1 岗位对齐（job_hunt）。把 today 页收口为 Career Transition Dashboard：职业进度+工作+学术(硕士答辩/博士)+ROI任务+Risk。确保 readiness 口径随模式同步。」

---

## Phase 4 — Project Agent / Opportunity Engine 升级（1.5 天，可选）
**目标**：从 goal/gap/resource 推荐 P01/P02/P03 项目。
- Day 4.1 在 `agents/planner` 加 `recommend_projects()`：输入 active 赛道 gap + 公司资源 + 博士/硕士进度，输出 Top3 项目（如 P01 企业文档 SFT、P02 Mini-VLM、P03 SO101 VLA）。
- Day 4.2 前端在落地页加"推荐项目"卡（复用 ProjectProgressCard）。
- 验收：返回项目带优先级理由；不重复造 Project 模型（复用现有）。
- **实施 Prompt**：「在 agents/planner 增加 recommend_projects()：基于当前模式 active 赛道技能缺口、公司真实项目资源、博士/硕士进度，输出 Top3 推荐项目（P01 企业文档后训练 / P02 Mini-VLM / P03 SO101 VLA），每项带优先级理由。复用现有 Project 模型，不新建。」

---

## 总预算与护栏
- 代码开发预算：每 Phase 独立可交付；**单日不超过 4–6 小时 OS 开发**，其余投入真实转型（继承提案 §27 的 OS Development Budget）。
- 门禁：每 Phase 末跑 `pytest`（后端）+ `tsc --noEmit` + `eslint` + `next build`（前端）+ 迁移双跑测试。
- 回滚：每 Phase 一个 git commit；迁移写 SQLite 写法 + `tests/test_migration_dialect_compat.py`。
- 禁止：推倒技术栈、重写已有 Agent（除 PhDAgent）、建两套前端、接无证据 LLM 决策。
