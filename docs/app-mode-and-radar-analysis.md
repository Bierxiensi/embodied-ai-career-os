# 把「职业规划 / 求职」做成可选项 —— 可行性分析与方案

> 分析日期：2026-09-10 ｜ 分析对象：Embodied AI Career OS（Next.js 16 + FastAPI）
> 触发问题：能否把职业规划/求职设计成可选项，从而展示不同界面？例如雷达图现在密密麻麻。

---

## 一、结论先行

**可行，而且这正是当前系统的自然演进方向。但不要做成"两套系统"，要做成"一套系统的模块门控"。**

三条判断：

1. **边界已经干净** —— 批次 0–4（岗位池→简历→面试→日报）全部是**纯增量**：只加模型/路由/页面，
   没有改动框架层。求职线在代码里是一个**可剥离的集合**，不是散落的补丁。
2. **"模式"不是新需求，而是收口手段** —— 系统里**已经并存两套互相矛盾的叙事**（见 §三），
   现在的问题不是"要不要选"，而是"不选就会一直打架"。
3. **雷达图与模式天然耦合** —— 雷达"密密麻麻"的根因是**轴数 = 全量技能数（46）**，
   而这 46 项里混着已冻结的具身技能。**模式决定该画哪张雷达**，两件事应当一起解决。

---

## 二、当前系统设计的真实结构（耦合面盘点）

| 层 | 通用底座（学习/成长 OS） | 求职专属（Batch 0–4） | 科研线（半通用） |
|---|---|---|---|
| **模型（21 张）** | career / skill / task / project / milestone / learning_log / agent_run / commit_suggestion / activity_draft / skill_assessment（**10**） | job_application / job_posting / job_match / resume_fact / resume_version / interview_log / interview_question / report_log（**8**） | paper / paper_chunk / paper_chunk_embedding（**3**） |
| **API 路由（19 个）** | career / skills / tasks / tools / planner / learning_logs / reviewer / agent / github / paper / projects / milestones / dashboard（**13**） | job_applications / job_hunt / job_postings / resume / interviews / reports（**6**） | （paper 计入通用列） |
| **前端页面（8 个）** | /dashboard · /projects · /agents（**3**） | /jobs · /jd · /resume · /interview · /reports（**5**） | — |
| **配置** | `skill_profile.py`（48 技能） | `target_roles.py`（TARGET_ROLES / TECH_BLACKLIST / SPRINT 窗口） | — |

**量化**：求职专属占 **8/21 模型（38%）**、**6/19 路由（32%）**、**5/8 页面（63%）**。
页面层占比最高 —— 这正是"界面看起来全是求职"的原因。

**关键结论**：耦合是**单向**的 —— 求职线依赖通用底座（技能/任务/投递），
通用底座不依赖求职线。所以门控求职线**不需要动底座**，风险低。

---

## 三、核心发现：已经有**两套叙事在打架**

这是本次分析最重要的发现，比"要不要做模式"更根本：

| 位置 | 现在说的话 | 属于哪套叙事 |
|---|---|---|
| `components/Dashboard.tsx` | `PHASE 2 · WEEK 1 · MULTI-AGENT` | 旧（8 月） |
| `components/Dashboard.tsx` | 「AI 驱动的**具身智能**职业成长操作系统 · 今日聚焦 **VLA 与 Sim2Real**」 | 旧（具身） |
| `app/layout.tsx` metadata | 「AI 驱动的**具身智能**职业成长操作系统」 | 旧（具身） |
| `components/SkillRadarCard.tsx` / `RadarChart.tsx` | 46 轴全量技能雷达（含 ROS2 / VLA / Mujoco） | 旧（具身） |
| `backend/core/target_roles.py` | llm **主攻** / vlm 卡位 / ai-algo 保底 / embodied **冻结** | 新（求职） |
| `backend/core/target_roles.py` | `TECH_BLACKLIST` 含 **VLA / ROS2 / Sim2Real / Mujoco** | 新（求职） |
| `/jobs` `/jd` `/resume` `/interview` `/reports` | 求职作战看板全链路 | 新（求职） |

**矛盾点**：Dashboard 首屏说"今日聚焦 VLA 与 Sim2Real"，而 `TECH_BLACKLIST` 明令
"VLA / Sim2Real 30 天内不投入"。**用户在同一个产品里被两套战略同时指挥。**

所以"模式可选项"不是加法，而是**把已经分裂的叙事显式化**。

---

## 四、"可选"的三种做法（方案对比）

| 维度 | **A. 前端本地模式** | **B. 后端配置模式（推荐）** | **C. 偏好表 + 运行时切换** |
|---|---|---|---|
| 存储 | localStorage / cookie | `config.py` + `.env`（`APP_MODE`） | 新建 `UserPreference` 表 |
| 谁决定界面 | 客户端 hook | Server Component 读 `/api/app-config` | 客户端 + 服务端都读 |
| 首屏一致性 | ✗ 会闪（SSR 不知模式） | ✓ 服务端即定，无闪烁 | ✓（需 RSC 取偏好） |
| 粒度 | 只能整体切 | **可模块级**（`modules.{jd,resume,...}`） | 可模块级 |
| 与项目哲学一致 | 一般 | ✓ **"把规范写成代码"**，与 target_roles/TECH_BLACKLIST 同源 | ✓ |
| 改动面 | 仅前端 | 后端 1 配置 + 1 接口 + 前端取数 | 后端 1 表 + 1 接口 + UI 切换器 |
| 成本 | 0.5–1 天 | **1–1.5 天** | 2 天 |
| 适合场景 | 纯个人临时用 | **长期、可提交 git、可复现** | 多人/多账号 |

**推荐 B**，理由：

- 模式影响的是**布局与服务端取数**（仪表盘画哪张雷达、KPI 换哪几个、今天推什么）。
  这类决策放在 **Server Component** 最干净；放 localStorage 会出现 SSR/CSR 不一致 + 首屏闪烁。
- 与既有哲学同源：`target_roles.py`、`TECH_BLACKLIST`、`report_enabled` 都是"配置即约束"。
  模式天然属于这一层 —— 改一行配置就切换，且能被 git 记录。
- 不自建偏好表，避免为"只有一个用户"的场景引入账号体系。

---

## 五、推荐的模式与模块设计

**模式 = 一组模块开关的预设**（而不是硬编码两套界面）。

```
APP_MODE = "growth" | "jobhunt" | "custom"
modules  = { jobs, jd, resume, interview, reports }   # 模块级布尔
```

| 维度 | `growth`（学习成长模式） | `jobhunt`（求职模式） |
|---|---|---|
| 导航 | 概览 / 项目 / Agent | 概览 / 项目 / Agent / **求职 / 岗位 / 简历 / 面试 / 报告** |
| 首页 | /dashboard | **/jobs**（求职作战看板当首页） |
| 仪表盘 banner | 「学习成长 OS · 今日聚焦 {当前主线技能}」 | 「求职作战看板 · 距 offer 目标 N 天」 |
| 雷达图 | **全域雷达（6 域聚合）** | **岗位对齐雷达（8 轴 = 当前赛道 required_skills）** |
| KPI | 技能就绪度 / 任务完成 / Agent 运行 | + 在投数 / 响应率 / 推荐岗位数 |
| 今日任务区 | Planner 生成的学习任务 | 学习任务 + **投递跟进**（`/api/reports/followups`） |
| 配置来源 | `skill_profile` 主线 | `target_roles.TARGET_ROLES` |

**设计要点**：

1. **模式只影响"展示"，不影响"数据"** —— 所有 API 继续存在。切模式不迁移、不删数据。
   这是最重要的一条纪律，否则"可选项"会变成"数据分裂"。
2. **默认值**：按 v2.0「求职优先」原则，默认 `jobhunt`；但允许 `growth` 用于
   "非求职周期"（例如拿到 offer 后回到学习主线）。
3. **接口**：`GET /api/app-config` → `{ mode, modules: {...}, landing: "/jobs" }`；
   前端 `layout.tsx` / `GlobalNav` / 各 page 读它。**单一数据源**，避免前端硬编码一份模式表。
4. **深链保护**：访问被关闭模块的路由 → 重定向到 `landing`，而不是 404。

---

## 六、雷达图为什么"密密麻麻"，怎么修

### 根因（已核实）

| 事实 | 数值 |
|---|---|
| 技能总数 | **48** |
| 雷达排除项（`EXCLUDE_FROM_RADAR`） | 仅 2（Frontend / Web Engineering） |
| **实际轴数** | **46** |
| 有 gap（target > level）的技能 | **34** |
| 其中属于**已冻结**具身方向的 | ROS2 / VLA / Robot Learning / Mujoco / Sim2Real 等 |

**两个病**：

1. **轴的语义不成立** —— 把"已冻结、30 天不投入"的具身技能和"主攻"的 LLM 技能画在同一张图上，
   形状没有解释力。
2. **维度数 = 数据量** —— 46 条轴、34 个凸点，标签互相压叠，天然不可读。
   雷达图的经验上限是 **6–8 轴**。

### 三种降维方案

| 方案 | 轴 | 数据是否现成 | 随模式变化 | 评价 |
|---|---|---|---|---|
| **R1 岗位对齐雷达** | **8** = 当前赛道 `required_skills` | ✓ 现成（`TARGET_ROLES`） | ✓ 天然（LLM 8 轴 / VLM 6 轴） | **求职模式立即可用**，直接回答"离岗位差多少" |
| **R2 域聚合雷达** | **6** = 技能域（LLM 基础/微调对齐/推理工程/多模态/工程交付/科研底座） | ✗ 需给 48 技能补 `domain` 字段 | 不需要 | **目标态正解**，语义最稳，长期通用 |
| **R3 Top-N gap** | 8 = gap 最大的 8 项 | ✓ 现成 | ✗ | 最省，但**轴会漂移**（今天画画的是 RoPE，明天换成别的），两张图不可比 |

**推荐组合**：

- **现在（求职模式）**：上 **R1**。零迁移成本，且"离目标岗位的技能形状"正是求职最该看的图。
- **目标态**：做 **R2** —— 给 `skill_profile.SkillProfile` 加 `domain` 枚举字段，
  48 技能归类后按域取平均 level。之后 `growth` 模式看 R2，`jobhunt` 模式看 R1。
- **不要用 R3** 作为主图（可作为补充的"Top 缺口条形图"，与雷达并存）。

---

## 七、顺带发现的问题（建议一并处理）

**6 个组件已死（未被任何页面 import）**：

| 死组件 | 说明 |
|---|---|
| `SkillOverview.tsx` | **雷达图的第二套实现**，标题还是「📡 Robot AI Capability」，含 46 轴同一问题 |
| `SkillGapSummary.tsx` | 仅被死组件 `SkillOverview` 引用 → 间接死亡 |
| `SkillCard.tsx` | 旧技能卡 |
| `CareerCard.tsx` | 旧职业目标卡 |
| `PendingSuggestions.tsx` | 旧待处理建议 |
| `TaskCard.tsx` | 被 `TodayTasks` 取代 |

> 影响：雷达图有**两个实现**（`SkillRadarCard` 在用、`SkillOverview` 已死），
> 改雷达时容易改错文件。建议先删死代码再改（`docs/agent-ui-improvement-analysis.md`
> 在 2026-08-21 就提过同类问题，部分已清理，这 6 个是残留）。

**另**：`app/layout.tsx` 的 `metadata.title/description` 与 `Dashboard.tsx` 的 banner
都还是"具身智能"叙事，与本轮战略相悖 —— 属于 §三 的收口范围。

---

## 八、落地步骤（分阶段，含改动文件）

### 阶段 1 · 立竿见影（0.5 天，低风险）— ✅ 已完成（2026-09-10）
- 雷达降维到 **R1 岗位对齐 8 轴**（求职模式的图）
  - `frontend/src/services/skillService.ts`：移除 `EXCLUDE_FROM_RADAR`/`filterRadarSkills`/`getRadarSkills`
  - `frontend/src/services/dashboardService.ts`：新增 `pickPrimaryTrack()`，雷达由 `主攻` 赛道
    `required_skills` 派生；`DashboardData` 改为 `radarAxes/primaryTrack/daysLeft`
  - `frontend/src/components/SkillRadarCard.tsx`：props 改为 `{axes, trackName, readiness}`，标题「岗位对齐雷达」
  - `frontend/src/components/KpiCards.tsx`：新增 `readinessLabel`，口径与主攻赛道匹配度同源
- 修掉旧叙事：
  - `Dashboard.tsx` banner → 「求职作战 · MULTI-AGENT」
  - `app/layout.tsx` metadata.description → 求职作战与能力成长
  - `JobsBoard.tsx` 副标题 → 主攻 LLM 大模型 / 卡位多模态 / 保底 AI 算法
  - **`backend/app/api/planner.py`**：移除写死的 `default="Robot AI Engineer"`，
    改为从 `TARGET_ROLES` 取「主攻」赛道（`_DEFAULT_TARGET_ROLE`）
  - `plannerService.ts` / `GenerateTaskButton.tsx`：不再硬编码岗位名
- 删 7 个死组件（`SkillOverview`/`SkillGapSummary`/`SkillCard`/`StarRating`/`CareerCard`/
  `PendingSuggestions`/`TaskCard`）→ 备份至 `.workbuddy/backup/dead-components-20260910/`

**验证**：`tsc --noEmit` exit 0；`scripts/smoke.sh` 40/40；`test_report_engine.py` 21 passed；
planner 默认岗位实测已切为「LLM / 大模型算法工程师」；冻结技能 target=level（gap 全 0），
不再计入 QuickActions 缺口数。

> 附：本次顺带修复 `stop.sh` 真实 bug —— Git Bash 的 `kill <winPID>` 会静默返回 0 却不杀进程，
> 导致 `|| taskkill` 兜底永不触发（前后端"停止成功"实则仍在运行）。已改为 Windows 走
> `MSYS_NO_PATHCONV=1 taskkill /F /T /PID`，并在 kill 后**复检端口**，失败则明确报错。

### 阶段 2 · 模式门控（1 天）
- `backend/app/core/config.py`：加 `app_mode` + `modules.*`
- `backend/app/api/app_config.py`（新）：`GET /api/app-config`
- `frontend/src/services/appConfigService.ts`（新）+ `app/layout.tsx` 注入
- `GlobalNav.tsx` / `app/page.tsx`（落地页重定向）/ `Dashboard.tsx` 按模式渲染

### 阶段 3 · 可选增强（1 天）
- **R2 域聚合雷达**：`skill_profile.py` 加 `domain` → 6 轴雷达（`growth` 模式用）
- 模块级开关在 UI 上可切（若不便改配置）

---

## 九、风险与"不要做的事"

| 风险 / 禁忌 | 说明 |
|---|---|
| ✗ **不要 fork 两个前端** | 两套代码 = 双倍维护，且必然漂移。只做门控。 |
| ✗ **不要让模式改动数据** | 隐藏的是入口，不是数据。否则切模式会"丢东西"。 |
| ✗ **不要删求职线** | v2.0 明确"求职优先"，求职线是当前主线资产。 |
| ⚠ 雷达降维会改变"就绪度"口径 | `computeReadiness` 目前对全 48 技能求和；换 8 轴后数字会变。需同步改 `KpiCards`，否则两处数字对不上。 |
| ⚠ 默认模式选择 | 默认 `jobhunt` 符合当前战略；但若用户在准备博士/学习周期，需能一键切回。 |

---

## 十、一句话总结

**做"模式门控"，不做"两套系统"；模式只改展示、不改数据；雷达图随模式换成
8 轴的"岗位对齐雷达"（现在）→ 6 轴的"域聚合雷达"（目标态）。**
顺带把已经打架的两套叙事（具身 banner vs 求职配置）收口。
