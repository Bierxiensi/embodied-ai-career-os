# Embodied AI Career OS v2.1 增量 PRD

> 版本：v2.1（增量，非重写）
> 审计依据：`docs/PROJECT_AUDIT_2026-09-20.md`
> 战略决策：2026-09-20 用户确认"公司愿意留下" → 战略基线从求职冲刺切到「在职转型 + 博士申请」
> 原则继承：`PRD_CAREER_OS_MODES.md` 的"一条业务规则只有一个权威实现 / 配置即约束 / 模式只改展示不改数据 / 不重写已有 Agent 只加薄适配层"

---

## 0. 定位

v2.0 提案中约 80% 的能力已在仓库实现（`target_roles.py` 已是 Post-Training v3.0、`evidence.py` 已做 L1–L4 证据门控、`career_mode` 已实现阶段切换、前端已有 SkillRadar/ProjectProgress/Evidence/Today）。本次是 **v2.1 增量升级**，不是推倒重来。

本次真正要建的只有 4 块净新增：博士模块、风险雷达、Career ROI、技能依赖图 + 统一落地页。外加一个**零代码的战略校准动作**（激活 `long_term_transition` 并定义其赛道策略）。

---

## 1. 战略校准（Phase 0，零代码，最先做）

### 1.1 决策
"公司愿意留下"已确认 → 当前模式从 `job_hunt` 切到 `long_term_transition`。

### 1.2 必须先解决：long_term_transition 是空壳
`services/career_mode/presets.py` 中 `LONG_TERM_TRANSITION` 的 `active_track_keys=()` / `frozen_track_keys=()`，注释明确"首期未定义"。切过去当前等于"无赛道约束"。需先定义其赛道策略：

| 赛道 | long_term_transition 下 | 理由 |
|---|---|---|
| `llm`（Post-Training） | **生效（主线）** | 公司真实业务 = 文档模型后训练，是在职转型核心资本 |
| `vlm` | **生效（桥梁）** | VLM→VLA 的桥，解冻为观察性活跃，不再冻结 |
| `phd` | **新增生效** | 博士申请成为与求职并列的第三主线（见 §3.1） |
| `ai-algo` | **冻结** | 保底不再是主线 |
| `embodied` | **冻结（长期观察）** | VLA/Robot Learning 是 on-job 长期目标，仍展示不每日推 |

> 实现方式：在 `presets.py` 给 `LONG_TERM_TRANSITION` 显式填 `active_track_keys=("llm","vlm","phd")` / `frozen_track_keys=("ai-algo","embodied")`。`phd` 赛道需在 `target_roles.py` 新增一条 `TargetRole(key="phd", ...)`（required_skills = 计算机/控制/AI/机器人相关能力；frozen=False）。

### 1.3 配套校准（不写新功能，只改配置/说明）
- `docs/MY_CONTEXT.md`：截止日期从"2026-10-31 签约"改为"在职转型窗口 2026.09–2027.03"；Goal 增加"博士申请（非全，计算机/控制/具身方向）"。
- `core/target_roles.py`：顶部注释加"2026-09-20 v3.1：因确认留任，新增 phd 赛道，long_term_transition 生效 llm/vlm/phd"。
- `career_goal` 表（如有记录）：更新目标描述/期限（如为空则跳过）。

### 1.4 安全约束（已保证）
模式表不持有任何业务数据引用（`models/career_mode.py`），切换不会删/改/隐历史投递、面试、任务。

---

## 2. 复用清单（已在仓库，禁止重写）

| 能力 | 现成位置 | 复用方式 |
|---|---|---|
| 赛道/岗位画像 | `core/target_roles.py`（v3.0 四赛道 + TECH_BLACKLIST） | 直接改配置，不加平行实现 |
| 技能画像+证据 | `core/skill_profile.py`（49 技能 0–5 级 + target + evidence） | 直接读，新增 `domain` 字段即可 |
| 证据门控等级 | `core/evidence.py`（L1–L4，纯函数） | 即"Evidence Agent"，不新建 |
| 30 天计划 | `core/plan_30d.py` + `agents/planner` + `/today` | 复用 |
| 阶段模式 | `models/career_mode.py` + `services/career_mode` + `api/career_mode.py`（GET /switch /transitions） | 已完整，仅补 long_term 赛道策略 |
| 雷达/进度/证据板 | 前端 `SkillRadarCard`(8轴R1)/`ProjectProgressCard`/`EvidenceBoard`/`ExperimentBoard` + `Today` 页 | 改皮肤/加面板，不重写 |
| 求职闭环 | `JDBoard`/`InterviewBoard`/`ResumeBoard`/`ReportsBoard` + 对应 model/api | 已完工具身智能相关冻结即可 |
| JD 匹配 | `agents/match/engine.py` | 博士匹配复用其相似度思路 |
| 论文 RAG | `research/paper_agent` | 已完成 |

---

## 3. 净新增模块（v2.1 真正要建）

### 3.1 博士模块 PhD（最高优先级，时间敏感）
**10 月必须建导师库**，是唯一真正从零的大块。

- **模型**（新增 `models/phd.py`）：
  - `PhDTarget`：`university` / `school` / `department` / `program` / `study_mode`(全日制/非全) / `admission_type`(申请-考核/统考) / `requirements` / `deadline` / `note`
  - `Advisor`：`phd_target_id` / `name` / `lab` / `research_directions`(JSON) / `robotics_resources`(bool/JSON) / `contacted`(bool) / `contact_date` / `match_json`(见下)
  - `ResearchDirection`：`name` / `category`(计算机/控制/自动化/AI/机器人) / `related_skills`(JSON) / `embodied_relevance`(0–5)
- **匹配（不做校排名，做多维）**：`match_json` 拆 `research_match` / `technical_match` / `academic_match` / `topic_match` / `resource_match` / `eligibility`，每维 0–1，加权得 `overall`。复用 `agents/match/engine.py` 的关键词/向量相似度。
- **Agent**：`agents/phd/agent.py`（薄封装，规则即可跑，标注"规则建议"；可选接 LLM 做导师方向摘要）。
- **种子**：从 `docs/北京在职博士-机器人具身智能.md` / `北京在职博士-易录取版.md` 抽取初始院校/方向/导师候选入 `PhDTarget` / `Advisor`。
- **前端**：新增 `src/app/phd/page.tsx` + `PhDBoard` 组件（导师库进度、匹配度、联系倒计时、材料清单）。

### 3.2 风险雷达 Risk Radar
- 复用 `docs/app-mode-and-radar-analysis.md` 的设计意图，落为模块 `core/risk.py`（纯函数，规则驱动）。
- 七维：`company` / `career` / `academic` / `phd` / `skill` / `financial` / `execution`。
- 示例规则：`execution` = 近 7 天无 `Experiment`/`DayArtifact(code)` → 风险↑；`academic` = 距 2026-12 答辩 < 90 天且无"答辩材料"任务 → 风险↑；`phd` = 11 月前无 `Advisor.contacted` → 风险↑。
- 接入 `/today` 顶部 + Dashboard。

### 3.3 Career ROI 显式指标
- 公式：`roi = (skill_delta × goal_relevance × evidence_value × real_project_value) / time_cost`，各维归一 0–1。
- 落地 `core/career_roi.py` 纯函数；并入 `/today` 任务排序，使"今日最高 ROI 任务"成为系统输出而非感觉。
- 权重可配置（默认 skill_delta 0.3 / goal_relevance 0.3 / evidence 0.2 / real_project 0.2）。

### 3.4 技能依赖图 + 统一落地页
- `skill_dependency` 表（`parent_skill` → `child_skill`）；`skill_profile` 加可选 `domain` 枚举（LLM基础/微调对齐/推理工程/多模态/工程交付/科研底座）支撑 R2 域聚合雷达。
- 统一 **Career Transition Dashboard**：收口 `Today` + `SkillRadar`(R1求职/R2域聚合随模式) + `ProjectProgress` + 学术进度(硕士答辩倒计时/博士) + 博士面板 + ROI 任务。即 v2.0 提案 §33 mockup。

---

## 4. 非目标（本期不做）
- 不推倒 Next.js / FastAPI / LangGraph；不重写已有 Agent（只加薄适配层）。
- 不做多用户/账号体系；不自动投递/联系外部平台。
- 不接"无证据、不可解释"的 LLM 自动决策（核心页面 LLM 未配置时仍可完整工作）。
- 不建"两套前端"——只做模式门控。

---

## 5. 验收（产品层）
1. 切换 `long_term_transition` 后，历史求职数据完整保留、前端不崩、导航展示新模式与目标。
2. `phd` 赛道生效，`/today` 在 long_term 模式下不再只推求职任务，出现博士/Post-Training/硕士任务。
3. 博士面板可展示种子导师、匹配度、联系倒计时。
4. Risk Radar 七维在 `/today` 顶部可见，无 experiment 时 execution 风险正确升级。
5. `/today` 任务按 Career ROI 排序，"今日最高 ROI 任务"为系统输出。
6. 统一落地页聚合职业/工作/学术/博士/ROI 五区。
