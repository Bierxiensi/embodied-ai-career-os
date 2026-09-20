# Embodied AI Career OS — 项目审计报告（v2.0 增量评估）

> 审计日期：2026-09-20
> 方法：直接读取仓库代码与文档（非凭记忆）。重点核实 `core/skill_profile.py`、`core/target_roles.py`、`core/evidence.py`、`models/career_mode.py`、前端 `src/app` 与 `src/components`。
> 结论先行：**你贴的 v2.0 方案 80% 已在仓库中。** 它不是"重新设计新系统"，而是对已经存在的「Stage Mode + 证据闭环 + Post-Training 战略」做增量扩展。

---

## 0. 一句话结论

1. **战略已对齐**：`target_roles.py` 已经是 Post-Training v3.0（LLM 主攻 → VLM 模型方向 → AI 算法保底 → embodied 冻结），与提案"Post-Training 第一跳、VLM 第二跳、VLA 第三跳"完全一致；路线文档（`路线调整-Post-Training-v3.0.md`、`具身智能在职转型路线图-2026-09-17.md`、`候选人背景分析-2026-09-17.md`）已覆盖岗位论证。
2. **机制已就绪**：`PRD_CAREER_OS_MODES.md` 已设计 `job_hunt` + `long_term_transition` 阶段切换，北极星目标"博士申请/具身智能转型"正是提案的 Academic/Career/Technical 三线合一。`models/career_mode.py` + `services/career_mode` 已落地，只是当前激活的是 `job_hunt`。
3. **真正缺的只有 4 块**：博士模块（无 model/agent/页）、风险雷达（文档设计过未落地）、Career ROI 显式指标、技能依赖图 + 统一落地页。
4. **最该先做的一件事不是写代码**：若"公司愿意留下"成立，正确动作是**激活 `long_term_transition` 模式 + 校准战略假设**，而不是建新架构。提案把"已建"当成"待建"，会诱导过度开发——这正是提案自身警告的"OS 本身变成新主业"风险。

---

## 1. 现状盘点：v2.0 提案模块 → 仓库真实状态（复用，别重写）

| v2.0 提案模块 | 仓库现状 | 复用方式 |
|---|---|---|
| CareerGoal / JobTarget | `models/career.py` (`career_goal`) + `core/target_roles.py`（四赛道，含 frozen） | 直接复用；改战略只改 `target_roles.py` |
| Skill Graph（含证据） | `core/skill_profile.py`（49 项技能，0–5 级 + `target_level` + `evidence`）+ `core/evidence.py`（L1–L4 证据门控推导，返回 `gate_level` + `evidence[]`） | "Evidence Agent" 已落地为纯函数，**不要新建平行 Agent** |
| 30 天计划 / Planner | `core/plan_30d.py`（唯一课程源）+ `agents/planner`（rule_generator / llm_generator）+ 前端 `/today` | 复用 |
| Career / Academic / Technical 三线 | `models/career_mode.py` + `services/career_mode/presets.py`（含 `job_hunt` 与 `long_term_transition`）+ `PRD_CAREER_OS_MODES.md` | 机制已就绪，仅未激活 `long_term_transition` |
| Dashboard | 后端 `/api/dashboard` + 前端 `SkillRadarCard`/`RadarChart`、`ProjectProgressCard`、`EvidenceBoard`、`ExperimentBoard`、`Today` 页 | 复用 / 改皮肤 |
| Agent 体系 | `supervisor`/`planner`/`reviewer`/`career`/`research`/`knowledge` + `agents/match/engine.py`（JD→技能匹配） | 加薄适配层，禁止重写 |
| 求职闭环 | `JDBoard`/`InterviewBoard`/`ResumeBoard`/`ReportsBoard` + `job_posting`/`job_match`/`job_application`/`interview_log` | 已完成 |
| 论文 RAG | `research/paper_agent`（parser/chunker/rag/summarizer）+ `paper`/`paper_chunk` 模型 | 已完成 |

---

## 2. 真正缺的（v2.0 净新增，按优先级排序）

1. **博士模块（最大缺口，唯一"从零"的大块）**
   - 现状：仅有策略文档 `docs/北京在职博士-机器人具身智能.md`、`docs/北京在职博士-易录取版.md`。**无 model、无 agent、无页。**
   - 需新增：`PhDTarget` / `Advisor` / `ResearchDirection` 模型（含 `study_mode` / `admission_type` / `research_match` / `resource_match` / `eligibility` 等字段，不做简单校排名）、种子数据、`PhDAgent`（信息整理 + 匹配，非排名）、Dashboard 面板。
   - 理由：提案要求 10 月建导师库，这是时间敏感项。

2. **风险雷达 Risk Radar**
   - 现状：`docs/app-mode-and-radar-analysis.md` 设计过，但未落地为模块。
   - 需新增：计算 Company / Career / Academic / PhD / Skill / Financial / Execution 七维风险，接 `/today` 顶部展示。Execution Risk 尤其关键（提案你自己说"怕不够狠"）。

3. **Career ROI 显式指标**
   - 现状：`agents/planner` 是规则/LLM 生成任务，没有"技能增量 × 目标相关性 × 证据价值 × 真实项目价值 ÷ 时间成本"的显式打分。
   - 需新增：`career_roi` 计算函数，并入 `/today` 任务排序，使"今天最高 ROI 任务"成为系统输出而非感觉。

4. **技能依赖图**
   - 现状：`skill_profile.py` 是扁平列表，无依赖边；`models/skill.py` 是 DB 实体但无 `skill_dependency` 关系。
   - 需新增：`skill_dependency` 表（`parent_skill → child_skill`），支撑"离目标岗位多远"的图计算（提案的 PyTorch→Transformer→Attention 树）。

5. **统一落地页 Career Transition Dashboard**
   - 现状：现有 `Today` + `SkillRadar` + `ProjectProgress` + `Evidence` 已分散存在。
   - 需收口为 Command Center：职业进度（Post-Training/VLM/VLA/Embodied AI）+ 当前工作 + 学术进度 + 博士面板 + 今日最高 ROI 任务。即提案 §33 的 mockup。

---

## 3. 战略对齐确认（提案前提 vs 代码现状的冲突）

- ✅ 路线方向：提案"Post-Training 第一跳、VLM 第二跳、VLA 第三跳" = 仓库 `target_roles.py` v3.0。**无需改战略方向。**
- ⚠️ **关键冲突**：提案新增变量"公司愿意留下"，但代码当前假设是 `DEFAULT_OFFER_DEADLINE="2026-10-31"`、赛道激活 `llm/vlm/ai-algo`、frozen `embodied`，且 `MY_CONTEXT.md` 写明"2026-09-24 离职交接完成"。
- ✅ 代码已为"留下"预留解法：`long_term_transition` 模式（北极星 = 博士申请/具身转型）。正确动作＝**激活该模式 + 校准 `MY_CONTEXT`/`career_goal` 截止日期为"在职转型窗口 2026.09–2027.03"**，而非新建架构。

---

## 4. 技术债 / 不要动（防过度开发）

- `database/` 目录**为空**（`.gitkeep` 仅有）。迁移实际位置需核实（`backend/app/db` 或 alembic/seed），应在 README 修正或补迁移索引。
- 旧文档（`TECH_DESIGN.md`、`PRD.md`）可能已过期，**改前先核对代码**，别信文档自述。
- 禁止推倒 Next.js / FastAPI / LangGraph 技术栈；禁止重写已有 Agent（`PRD_CAREER_OS_MODES.md §6` 非目标明确禁止"重构所有已有 Agent，只允许加薄适配层"）。
- 前端用 `src/` 目录 + App Router；新页面放 `src/app/<route>/page.tsx`，组件放 `src/components`。
- 提案里的 `CareerStrategistAgent` / `SkillGapAgent` / `ProjectAgent` / `EvidenceAgent` / `PhDAgent` / `RiskAgent` / `OpportunityAgent` 命名，**绝大多数能映射到现有 `career` agent + `evidence.py` + `planner` + `match/engine` 的薄封装**，不应新建平行 Agent 体系（否则变成提案警告的"又写了 3 个月 OS")。

---

## 5. 推荐落地顺序（v2.0 实为 v2.1 增量）

- **Phase 0（今天，零代码）**：确认"公司留下" → 激活 `career_mode=long_term_transition`；更新 `MY_CONTEXT.md` 与 `career_goal` 截止日期；校准 `target_roles.py` 的"留下"假设（如 GPU/训练权限）。
- **Phase 1（博士模块）**：model + 种子 + `PhDAgent` + Dashboard 面板。时间敏感（10 月建导师库）。
- **Phase 2**：Risk Radar + Career ROI 接入 `/today`。
- **Phase 3**：技能依赖图 + 统一 Career Transition Dashboard 落地页。
- **Phase 4**：Project Agent / Opportunity Engine 升级（P01/P02/P03 推荐）。

---

## 6. 给实施者的直接指令

别让 WorkBuddy 一次性实现整个 v2.0。先做 Phase 0（切模式，零代码，需你确认"留下"事实），再做 Phase 1（博士模块）——这是提案里唯一真正从零的大块，且时间敏感。其余全部在现有骨架上增量加薄层。提案 90% 的"新模块"已在仓库，重写它们 = 制造技术债。
