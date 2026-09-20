# Embodied AI Career OS v2.1 Agent 体系规格

> 配套：`CAREER_OS_V2_INCREMENTAL_PRD.md` / `CAREER_OS_V2_ARCHITECTURE.md`
> 核心纪律：**v2.0 提案里 90% 的"新 Agent"命名都能映射到现有薄封装，禁止新建平行 Agent 体系。**

---

## 0. 现有 Agent 体系（已实现，复用）

| Agent | 位置 | 职责 | v2.1 复用为 |
|---|---|---|---|
| Supervisor | `agents/supervisor` | 多 Agent 调度 | 顶层路由不变 |
| Planner | `agents/planner`（rule/llm generator） | 生成学习任务 | 接 ROI 排序（§3） |
| Career | `agents/career`（graph/nodes/state） | 岗位分析 / Skill Gap / 路线 | 接 long_term 赛道策略 |
| Reviewer | `agents/reviewer` | 能力评估 | 不变 |
| Research | `agents/research` | 论文调研 | 博士文献调研复用 |
| Knowledge | `agents/knowledge` | 知识管理 | 不变 |
| Match | `agents/match/engine.py` | JD→技能匹配 | **博士匹配直接复用** |
| Evidence（函数） | `core/evidence.py` | L1–L4 证据门控 | 即"Evidence Agent"（纯函数） |

---

## 1. v2.0 提案 Agent → v2.1 实际落点映射

| 提案命名 | v2.1 落点 | 是否新代码 |
|---|---|---|
| CareerStrategistAgent | 现有 `career` agent + `career_mode` 策略；不新建设 | 否（加薄适配） |
| SkillGapAgent | `career` agent 的 nodes（已算 gap） | 否 |
| EvidenceAgent | `core/evidence.py` | 否（已存在） |
| ProjectAgent | `agents/planner` 扩展：从 goal/gap/resource 推荐 P01/P02/P03 | 部分（新增推荐逻辑，复用 Project 模型） |
| PhDAgent | **新增** `agents/phd/agent.py`（薄封装，规则可跑） | 是 |
| RiskAgent | **新增** `core/risk.py`（纯函数，无 LangGraph 必要） | 是（函数非 Agent） |
| OpportunityAgent | 升级 `planner` + `career_roi.py` 的跨赛道任务排序 | 部分 |

> 结论：**真正需要新建代码的 Agent 只有 `PhDAgent` 一个**。其余都是现有模块的薄适配或纯函数。这直接规避了提案自身警告的"又写了 3 个月 OS"风险。

---

## 2. PhDAgent 规格（唯一净新增 Agent）

### 2.1 定位
信息整理 + 匹配，**不做校排名**。输入：导师/方向原始信息；输出：结构化 `Advisor` + 六维 `match_json`。

### 2.2 接口
```
class PhDAgent(BaseAgent):
    name = "phd"
    # 复用 build graph 模式（与 CareerAgent 一致），或直接暴露纯函数
    def analyze_advisor(self, advisor_raw, user_profile) -> match_json
    def recommend_targets(self, db) -> list[PhDTargetOut]   # 按 research/topic/resource 加权
```

### 2.3 匹配算法（六维，复用 match/engine）
- `research_match`：导师 `research_directions` 与用户目标方向（VLM/VLA/Robot Learning）重合度
- `technical_match`：方向所需技能 vs `skill_profile` 现有 level
- `academic_match`：用户学历（北航非全硕士）与项目招生要求契合
- `topic_match`：导师论文关键词 vs 用户研究兴趣
- `resource_match`：导师是否有机器人/机械臂平台（具身相关性）
- `eligibility`：非全/申请-考核/英语/科研要求是否达标（0/1 或 0–1）
- `overall = Σ(w_i · dim_i)`，权重配置化（默认 research 0.3 / resource 0.25 / eligibility 0.2 / 其余均分）。

### 2.4 LLM 可选
LLM 未配置时走规则（关键词重合）；配置后可做导师方向一句话摘要。**前端标注"规则建议"**。

---

## 3. Career ROI 接入 Planner（OpportunityAgent 实质）

### 3.1 计算（`core/career_roi.py`）
```
score(task) = (skill_delta × goal_relevance × evidence_value × real_project_value) / time_cost
```
- `skill_delta`：任务覆盖技能的 (target-level) 之和归一
- `goal_relevance`：技能是否属于当前模式 active 赛道 required_skills
- `evidence_value`：任务产物类型（code/experiment > note）权重
- `real_project_value`：是否绑定公司项目/博士/硕士（bool→0/1）
- `time_cost`：预估小时数

### 3.2 接入
`/today` 聚合在现有 Planner 输出外，叠加 `roi_ranked_tasks`（取 Top 5），前端 `RoiTaskList` 渲染。规则即可跑，不依赖 LLM。

---

## 4. RiskAgent（实为 `core/risk.py` 纯函数）

七维风险，每维输出 `level ∈ {green, yellow, red}` + `reason`：
- `company`：产品商业化信号（手动/外部输入字段）
- `career`：active 赛道 gap 是否收敛
- `academic`：距 2026-12 答辩倒计时 + 是否有答辩材料任务
- `phd`：是否在 11 月前开始联系 advisor（contacted 计数）
- `skill`：active 赛道最低技能等级
- `financial`：在职=green（硬编码或从配置读）
- `execution`：**连续 N 天无 experiment/code artifact → red**（最关键的"怕不够狠"检测器）

接 `/today` 顶部 + Dashboard。无状态、可单测。

---

## 5. 路由升级（Career Router）

现有：`Intent` → `Supervisor` → `{career, planner, reviewer, research, knowledge}`。
v2.1 仅新增 `phd` 分支与 `risk`/`roi` 作为 `/today` 聚合的辅助计算（非独立路由节点）。**不重构现有路由**，只在 `Supervisor` 的可用 Agent 注册里加 `phd`。

---

## 6. 不可逾越的线
- 不新建平行 Agent 体系（除 PhDAgent）。
- 所有"智能建议"在 LLM 未配置时仍可运行，且页面标注"规则建议"（继承 `PRD_CAREER_OS_MODES.md` §6）。
- 模式/ROI/风险只改展示不改数据。
