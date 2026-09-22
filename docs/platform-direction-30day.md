# 平台走向规划：从「展示看板」到「30 天施工执行台」

> 规划日期：2026-09-10｜输入：《30-Day LLM → VLM 求职施工计划 v2.0》
> 结论一句话：**平台缺一层「课程脊梁」实体，所以它只能度量状态、不能驱动进度。度量而不驱动 = 展示。**

---

## 一、诊断：为什么它现在像展示平台

你的直觉是对的，而且可以精确定位。三条证据，全部落在代码和数据模型上。

### 证据 1：导航里没有「今天」

顶栏 8 个入口（`GlobalNav.tsx`）：

```text
概览 · 项目 · 求职 · 岗位 · 简历 · 面试 · 报告 · Agent
```

这 8 个入口，**没有一个是"我今天该干什么"**。逐个看它们在回答什么问题：

| 入口 | 回答的问题 | 类型 |
|---|---|---|
| 概览 | 我现在到什么水平了 | 状态 |
| 项目 | 我的项目进展如何 | 状态 |
| 求职 | 我投了多少、转化如何 | 结果 |
| 岗位 | 市场上有哪些 JD | 信息 |
| 简历 | 我的简历诊断结果 | 结果 |
| 面试 | 我复盘过几次面试 | 结果 |
| 报告 | 系统给我发了什么报告 | 结果 |
| Agent | 我的 Agent 跑了什么 | 观测 |

**8 个入口里 7 个是「我现在怎么样」，0 个是「我现在该做什么」。**

这就是"展示平台"的精确含义：它是一面镜子，不是一张施工图。

### 证据 2：数据模型只有状态机，没有过程记录

现有 ORM（`backend/app/models/`）表达"进度"的方式是三个状态字段：

```text
Skill.level / target_level     →  我差几级
Task.status (todo/doing/done)  →  这条做没做完
Milestone.status               →  阶段到哪了
```

唯一记录"过程"的表是 `LearningLog`，而它是：

```text
content         Text       一句话自由文本
duration_minutes Integer    时长
artifact_url    String(500) 单个链接（可选）
```

**一天的全部产出 = 一条自由文本 + 一个可选链接。** 这个模型无法回答：

- 今天该产出几个东西？产出齐了吗？
- 我写了代码，但笔记呢？面试题呢？commit 呢？
- 昨天没完成，今天怎么补？

### 证据 3：Planner 只会"补缺口"，不认识"计划"

`agents/planner/` 的输入是**技能缺口**（`Skill.target_level - level`），输出是"今天补这个技能"的任务。

它知道：

```text
Transformer: level 2, target 4, gap 2  →  生成一条 Transformer 任务
```

它不知道：

```text
Day 2 的课程内容是「Attention 手写实现」，
验收标准是「能解释为什么除以 sqrt(d)」，
且今天必须同时交出 rope.py + docs/rope.md + 5 道题 + 1 个 commit
```

**计划只存在于你读的那份文档里，系统里没有它的投影。** 所以 Planner 生成的其实是"最合理的随机任务"，而不是"课程表上的 Day N"。

---

## 二、重新定位：平台应该回答的三个问题

| | 现在回答 | 改造后必须回答 |
|---|---|---|
| Q1 | 我到底什么水平？ | **今天（Day N）该干什么？** |
| Q2 | 我已经完成了多少？ | **今天该交的四样东西，交齐了吗？** |
| Q3 | 我的求职漏斗如何？ | **我现在的证据链，够不够支撑投出去？** |

Q3 保持不变（这部分是健康的）。**Q1 降级为 Q2 的副产品**——水平不再靠自评，而是靠证据推导。Q2 是全新的、也是最重要的一层。

---

## 三、支撑映射：30 天计划 15 个要素 → 平台动作

这是本文的核心。逐条对齐你那份计划，标出平台现状和要做的动作。

| # | 计划要素 | 平台需要提供 | 现状 | 动作 |
|---|---|---|---|---|
| 1 | Day 1–30 课程脊梁（含每日验收、面试题） | 课程计划实体 + 总览页 | ❌ 只存在于文档 | **新建 `PlanDay` + `/plan` 页** |
| 2 | 每天 6h 结构化时间块 | 计划 vs 实际时间 | ❌ | P4 可选，低优先 |
| 3 | **每日四件套**（代码/笔记/≥5 题/commit） | 每日契约 + 勾选 + 补齐 | ⚠️ `LearningLog` 单条自由文本 | **改造为 `Artifact` 四类** |
| 4 | 单一项目 `llm-vlm-finetuning-lab` 目录结构 | 项目 → 目录 → 产出映射 | ⚠️ 只有 Project/Milestone | 加 repo 绑定 + 目录 checklist |
| 5 | 只允许 5 类资源（禁止课程收藏） | 资源白名单（硬约束） | ❌ | **`RESOURCE_LOCK`**（复用 `TECH_BLACKLIST` 机制） |
| 6 | L0–L4 深度阶梯表 | 等级语义 + 晋级证据规则 | ⚠️ 0–5 整数，无证据约束 | **阶梯映射 + 晋级需 typed evidence** |
| 7 | 每日 ≥5 题 → 累计 50 LLM + 30 VLM | 题库生长 + 覆盖率矩阵 | ⚠️ 有 `InterviewQuestion` 表，无目标/无来源 | 加 `source_day` / `target` + 覆盖率视图 |
| 8 | Experiment A：SFT / LoRA / QLoRA 对比表 | 实验记录（多变体 + 多指标） | ❌ | **新建 `Experiment`** |
| 9 | Experiment B：VLM before/after | 同上 | ❌ | 同上 |
| 10 | Inference Benchmark：TTFT / Throughput / Memory | 基准记录 | ❌ | `Experiment` 的 benchmark 类型 |
| 11 | README 写成论文 | 从证据链生成 | ❌ | P4 生成器 |
| 12 | 简历叙事：小样本时序 → Foundation Model | 叙事线 + 论文反向校准 | ⚠️ 有 `/resume` 防虚构诊断 | 加叙事线 + STM-SHAP 校准 |
| 13 | 30 commits + 30 notes + 150 题「成果包」 | 累计守恒总账 | ❌（KPI 口径不同） | 今日页底部「总账」 |
| 14 | Day 29 海投启动 | 投递漏斗 | ✅ `/jobs` 已有 | **10 月起提为主位** |
| 15 | 不发散（D 级技术黑名单） | 生成时拦截 | ⚠️ `TECH_BLACKLIST` 已定义但未接 Planner 拒绝 | **接上拒绝逻辑** |

**盘点结论**：15 个要素里，**3 个已就绪（14/15 部分）、5 个需要改造、7 个需要新建**。好消息是——需要新建的 7 项全是「一张表 + 一个页面」的量级，且能完全复用现有的 FastAPI + Server Component + 设计 token 骨架。

---

## 四、六个核心设计决策

这六条决定了改造后平台的性质。逐条给理由。

### 决策 1：把「Day N」和「日历日期」解耦 ⭐ 最重要

```text
PlanDay.seq = 1..30        课程脊梁，不可变（改的是内容，不是序号）
DayProgress.calendar_date  执行记录，可移动
```

**理由**：你 9 月底离职、10 月海投面试，滑期是必然事件，不是异常。如果 Day 绑死日期：

- 滑 1 天 → 后面 29 天全部错位
- 用户看到"Day 5 的日期是昨天"，第一反应是放弃平台 —— 这是学习类工具最典型的死法

解耦后平台能说人话：

```text
课程进度 Day 7 / 30   日历已过 9 天   落后 2 天
→ 建议：Day 7 验收改为 30 分钟速通，缺口并入 Day 8 晨间时段
```

这也和上一轮 `track_key` 的设计哲学一致：**不同维度各自成轴，不要互相绑死**。

### 决策 2：每日契约（DailyContract）是新的核心实体

```text
Artifact 四类：code / note / questions / commit
「今天完成」的定义 = 四类齐全（commit 可自动同步 → 零手工）
平台第一次有了「未完成」这个概念
```

**理由**：这是把"展示"变"学习"的唯一机制。现在的 `todo/doing/done` 三态是人为切换的，没有客观标准，所以"完成"没有约束力。四件套是可核验的：

| 类型 | 核验方式 |
|---|---|
| `code` | 文件路径 / 提交 diff（可半自动） |
| `note` | 文本长度 + 是否关联当天任务 |
| `questions` | 题库里当天新增条数 ≥ 5（**自动可数**） |
| `commit` | GitHub API 按日期自动归集（**全自动**） |

四类里两类能自动核验 —— 这是关键，否则手工勾选三天就烦了。

### 决策 3：技能晋级必须有「typed evidence」

现在是 `evidence_score`（0–100 打分）驱动晋级，标准偏软，本质还是自评。改为把 L0–L4 阶梯和产出类型绑定：

| 晋级 | 必须提供的证据 |
|---|---|
| → L1 能解释 | 一份 `note` artifact |
| → L2 能实现/修改 | 一个 `code` artifact（有 commit） |
| → L3 能做实验 | 一条 `Experiment`（有指标表） |
| → L4 能研究 | 一条对比实验 + 一份复现报告 |

**理由**：这样"level"不再是自我感觉，而是从证据推出来的。副产品——你的简历里每个技能都能点开看到支撑证据，这在面试里是真金白银（"你说你会 LoRA，给我看看" → 直接打开实验表）。

### 决策 4：实验记录是一等公民

```text
Experiment
  ├── day_seq / name / kind (finetune | benchmark | ablation)
  ├── variants: JSON    [{name, trainable_params, gpu_mem, time, result}]
  ├── metrics:  JSON    [{name, value, unit}]
  ├── conclusion: Text
  └── artifact_ids
```

Day 12 的 LoRA vs QLoRA、Day 22 的 SFT/LoRA/QLoRA、Day 23 的 Transformers vs vLLM，全部直接落表。

**理由**：你计划里说"项目不再是『我跑了 Qwen』，而是『我研究了 PEFT 对训练成本与效果的影响』"——这句话的前提就是有一张**能填的表**。现在没有任何地方能填这张表，所以那句话只会停留在计划里。

### 决策 5：题库要「按天生长」，不是 Day 26 才开始整理

计划 §十 要求每天 ≥5 题，Day 26/27 说"开始建立 50 + 30 题"。**如果真等到 Day 26 才开始，必然写不出 50 题**——那时你只记得住最后几天。

改为：每天完成任务时顺手录题（计划本来就要求了），Day 26/27 只做**查缺补漏 + 分类过一遍**。

**顺带纠正计划里的一个口径冲突**：

| 出处 | 数字 | 实际含义 |
|---|---|---|
| §十「每天 5 题」×30 天 | 150 题 | 累计**上界** |
| §八 Day 26/27 | 50 LLM + 25~30 VLM ≈ 80 题 | **必达下界** |

两个数字都对，但混在一起容易让人以为要写 150 题而放弃。平台口径应该是：**累计目标 150，核心必达 80**，覆盖率矩阵用红格子把"缺口在哪"显示出来。

### 决策 6：资源锁 + 黑名单要「拒绝」，不只是「提示」

`TECH_BLACKLIST` 已经在 `target_roles.py` 定义了 12 项（ROS2 / VLA / Isaac / World Model…），但 Planner **没有真的拒绝**，只会生成出来。同理，计划 §二 要求"只允许 5 类资源"。

**理由**：计划自己说了最大风险是"又换学习路线"。约束如果不硬，等于没有。这两个都改成生成时的**硬拒绝 + 明确文案**：

```text
⛔ 该任务命中 D 级技术（VLA），30 天窗口内不投入。
   如确认要学，需二次确认。
```

---

## 五、数据模型增补（迁移 0009 起）

沿用现有约定：snake_case 落库、前端 adapter 转 camelCase、一条迁移只做一件事、注释里禁分号。

```text
新增 4 张表
──────────────────────────────────────────────────────────
plan_days         课程脊梁（seq 1..30）
  seq, title, phase(1-4周), theme, objectives[], acceptance[],
  interview_topics[], resources[], est_minutes, level_targets(JSON)

day_progress      执行记录（与日历解耦）
  plan_day_id, calendar_date, status, actual_minutes, deviation_note

artifacts         每日四件套
  day_progress_id, kind(code|note|questions|commit), title,
  url, payload(JSON), auto_verified(bool), verified_at

experiments       实验记录
  day_seq, name, kind, variants(JSON), metrics(JSON),
  conclusion, artifact_ids(JSON)

改造 3 张表
──────────────────────────────────────────────────────────
tasks             + plan_day_id (FK, nullable)  ← 与 track_key 正交
interview_questions + source_day_seq, + skill_name, + is_verified
skills            + evidence_gate (推导出的最高可信等级)
```

**设计要点**：`tasks.plan_day_id` 和 `tasks.track_key` 是**两个正交轴**——前者说"属于课程第几天"，后者说"属于哪条赛道"。一条 Day 11 的 LoRA 任务，`plan_day_id=11` + `track_key='llm'`。这保持了上一轮"不同维度各自成轴"的一致性。

---

## 六、信息架构重构

现顶栏 8 项过于拥挤且全偏"结果"。改为**过程区 + 结果区**，并把求职类收拢到二级导航（复用已有 `SubNav` 模式）。

```text
现在                                  改造后
────────────────────────────          ────────────────────────────
概览 · 项目 · 求职 · 岗位 ·           今日 · 施工 · 项目 · 题库 ·
简历 · 面试 · 报告 · Agent            求职 ▾ · 复盘 · Agent

                                     求职 ▾ 二级：投递 / 岗位 / 简历 / 面试
```

| 入口 | 性质 | 说明 |
|---|---|---|
| **今日** | 过程·主位 | 新首页，默认落地页。替代 `/dashboard` 作为默认 |
| **施工** | 过程 | 30 天课程脊梁总览 + 滑期决策（`/plan`） |
| **项目** | 过渡 | 从"里程碑进度条"改为"证据链"视图 |
| **题库** | 过程 | 覆盖率矩阵 + 快速录题 + 抽题模拟 |
| 求职 ▾ | 结果 | 投递 / 岗位 / 简历 / 面试 四项收进二级，10 月提为主位 |
| 复盘 | 结果 | 原 `/reports` |
| Agent | 观测 | 保持现状，但不在主栏抢位 |

**关键**：`/dashboard` 不删除，降为「我的水平」——从默认落地页变成从"今日"侧边进入的能力盘点页。省下的开发量用在 `/today`。

---

## 七、分阶段路线图

工时按「平台实际投入」计，不是日历天。**硬约束：单周平台工时 ≤ 2 个晚上（≤8 小时）**，理由见第九节。

### P0 · 今日施工单（1 个晚上 ≈ 3–4h）

| 项 | 内容 |
|---|---|
| 后端 | `plan_days` 表 + 30 天种子脚本（幂等，仿 `seed_job_hunt.py`）；`tasks.plan_day_id` |
| 前端 | `/today` 页：今天是 Day N（按实际进度算）· 今日任务 + 验收标准 · 四件套勾选 · 「总账」条（commit X/30 · note Y/30 · 题 Z/150） |
| 复用 | `PageHeader` / `PlannerResultCard` / 设计 token，零新依赖 |
| **验收** | **打开首页 5 秒内知道：今天第几天、干什么、做完没有** |

### P1 · 课程脊梁 + 滑期机制（1 个晚上）

| 项 | 内容 |
|---|---|
| 后端 | `day_progress` 表；进度算法（课程进度 vs 日历进度） |
| 前端 | `/plan` 30 天总览（4 周分带、状态色）、落后提示 + 三个决策按钮（压缩 / 顺延 / 放弃） |
| **验收** | 滑 3 天后页面明确说"落后 3 天"并给出可执行建议，不自动顺延 |

### P2 · 证据闭环（1 个晚上）

| 项 | 内容 |
|---|---|
| 后端 | `artifacts` 表；`experiments` 表；GitHub commit 按日自动归集 |
| 逻辑 | 技能晋级改为 evidence-gated；`TECH_BLACKLIST` 接 Planner 硬拒绝 |
| 前端 | 四件套详情抽屉、实验对比表渲染器（`variants` → 表格） |
| **验收** | 填一次 LoRA vs QLoRA 实验，页面直接渲染出对比表；技能升级弹窗显示"因为这份代码" |

### P3 · 题库生长 + 模拟面试（1 个晚上）

| 项 | 内容 |
|---|---|
| 后端 | `interview_questions` + `source_day_seq` / `skill_name`；覆盖率统计 |
| 前端 | 快速录题（单输入框）、覆盖率矩阵（skill × category，红格 = 缺）、抽题模拟 |
| **验收** | 每天录题 ≤ 1 分钟；Day 26 时看到的是"缺口在哪"而不是"从零开始" |

### P4 · 求职包装自动化（1 个晚上）

| 项 | 内容 |
|---|---|
| 生成 | README 骨架从证据链生成（Motivation→…→Failure Cases） |
| 生成 | 简历技能行自动附证据链接 |
| 页面 | 项目页 → 证据链视图；`/jobs` 提为主位 |
| **验收** | Day 24/25 的 README 和简历是"导出 + 润色"，不是"从空白开始写" |

**总计 ≈ 4.5 个晚上 / 5 个工作日投入**，分布在 2 周内。

---

## 八、明确不做（防发散）

这份清单和第七节同等重要。平台建设本身就会变成一次"路线发散"。

```text
❌ 不接入新的 Agent / 不扩展多 Agent 编排
   现有 7 个 Agent 足够，Planner + Reviewer 够用

❌ 不做 D 级技术相关任何功能
   MoE / RLHF / CUDA Kernel / Isaac / VLA / World Model
   → 现有 embodied 任务模板应归档（不是删除，标记 frozen）

❌ 不做课程资源库 / 收藏夹
   直接违反计划 §二「不要再课程收藏」

❌ 不做移动端 App / 多用户 / 权限体系
   单人自用，一辈子用不上

❌ 不做系统监控大屏 / Agent 性能调优面板
   这是"展示"的极致，恰好是要摆脱的东西

❌ 不做 PlanDay 的 CRUD 管理界面
   用「计划文件 + 幂等种子脚本」，改计划 = 改 Python 文件 + 重跑脚本
   （与 target_roles.py / seed_job_hunt.py 既有约定一致）
```

---

## 九、风险与对冲

### 风险 1（最大）：平台建设吞掉学习时间 ★

一个"学习平台"最大的失败模式，是把时间花在建设平台上而不是学习上。30 天里你已经历过一次路线发散，这是第二次机会。

**对冲（硬约束）**：

```text
单周平台工时 ≤ 2 个晚上（≤8h）
超了 → 立即停手，回学习
平台没有"顺手加个功能"这种选项
```

如果 P0–P4 全部按计划做完需要的工时超出预算，**优先砍 P4，其次砍 P3**。P0/P1 不可砍——没有它们平台就还是展示台。

### 风险 2：计划硬编码进 DB 后，改计划成本高

计划会变（比如你发现 Day 9 显存计算要花两天）。

**对冲**：不做 CRUD 界面，用**计划文件 + 幂等种子脚本**。改 `plan_30d.py` 里的内容 → 重跑脚本 → `seq` 不变则更新、变了则新增。和 `target_roles.py` 完全一致的既有模式。

### 风险 3：滑期机制被滥用成"自动顺延"

如果落后就自动顺延，那永远不会补，30 天变成 45 天。

**对冲**：**只提示，不自动**。落后时必须手动选一个：压缩 / 顺延 / 放弃，且选择要落 `deviation_note`。强迫面对取舍。

### 风险 4：四件套变成形式主义

为了凑数写 5 道烂题，不如写 0 道。

**对冲**：`questions` 类允许标"待验证"，Day 21/26 的面试验收就是验证环节——答不出来的题会被标红，倒逼质量。不要为了数字好看加校验规则。

---

## 十、一句话路线

```text
现在：8 个入口全在回答「我怎么样」     →  一面镜子

改造后：第一个入口回答「今天干什么」    →  一张施工图
       证据链自动长出简历和 README     →  一条流水线

投入：4.5 个晚上，2 周内完成
铁律：单周平台工时 ≤ 2 个晚上，超了就去学习
```

---

## 十一、P0 实施记录（2026-09-10 ~ 09-11）

P0 已落地并通过验证。以下是实际实现与规划的两处**有意偏离**，以及一条实测踩坑。

### 11.1 偏离一：`day_artifacts` 表从 P2 上移到 P0

规划 §五把 `artifacts` 表列在 P2，但 §七 的 P0 前后端清单里又要求"四件套勾选"。
这是原文自相矛盾 —— 没有表就勾不了。

**处理**：把表放进 P0，P2 只保留"自动核验 + Experiment 表 + evidence gating"。
理由：四件套是 P0 验收标准（"做完没有"）的唯一答案来源，没有它 P0 交付不了。
自动核验（commit 由 GitHub 归集、questions 由题库条数判定）确实属于 P2，因为它是优化不是前提。

### 11.2 偏离二：新增 `day_artifacts` 之外的迁移**不止一条**

规划没说迁移怎么切。实际按"一条迁移只做一件事"拆成三条（0009 建 plan_days、
0010 建 day_artifacts、0011 给 tasks 加 plan_day_id）——
因为 `run_migration.py` 按 `;` 裸切分，多语句在同一事务里任一句失败会整批回滚，
留下静默缺失（0008 那次已经踩过）。

### 11.3 实测踩坑：**通用技能映射不要回填到具体课程日**

首版 `SKILL_TO_DAY_SEQ` 把 `Python → Day 2`、`Deep Learning → Day 5`、`PyTorch → Day 6`
也收了进去，理由是"这些技能在那些天会被用到"。跑完立刻出问题：

```
Day2 [Attention 手写实现] ← [Python]          Career OS Day2 数据库层
Day2 [Attention 手写实现] ← [Python]          Python asyncio 异步编程实践
Day5 [Loss 与反向传播全链路] ← [Deep Learning] 算法/系统设计题刷题（具身方向）
```

默认落地页因此显示了两条与 Attention 毫无关系的任务。

**教训**：通用框架/语言技能（Python / PyTorch / Deep Learning）**不蕴含属于课程第几天**。
只有课程特有的技能名（Transformer / RoPE / SFT / LoRA / vLLM / ViT…）才能安全映射。

**修法**：
1. `SKILL_TO_DAY_SEQ` 只保留课程特有技能，绑定数从 7 条降到 3 条（全对）
2. `seed_plan_30d.py` 增加 `--rebind`：先清空全部 plan_day_id 再重绑 ——
   映射规则收紧后旧错绑不会自动消失（因为默认只填 NULL 的行），必须显式重置
3. 原则记入代码注释：**宁可少绑，不可错绑**。错绑比不绑更有害，
   因为它伪造了"今天该做这个"的因果 —— 而平台的价值恰恰建立在因果可信上。

### 11.4 P0 交付物

| 层 | 文件 | 说明 |
|---|---|---|
| 数据源 | `app/core/plan_30d.py` | 30 天课程唯一事实来源 + 5 类资源锁 + D 级黑名单副本 |
| 模型 | `app/models/plan_day.py` `app/models/day_artifact.py` | 课程日 / 每日产出 |
| 迁移 | `migrations/0009~0011` | 建表 ×2 + tasks.plan_day_id |
| 接口 | `app/api/plan.py` | `/api/plan`、`/api/plan/today`、`/api/plan/artifacts` |
| 种子 | `scripts/seed_plan_30d.py` | 幂等 upsert + 任务回填（`--dry-run` / `--rebind`） |
| 页面 | `app/today/page.tsx` + `components/TodayBoard.tsx` | 默认落地页 |
| 导航 | `GlobalNav` 首位加「今日」；`app/page.tsx` 重定向改 `/today` | /dashboard 未删，降为二级 |
| 测试 | `tests/test_plan_api.py` | 10 项（含 day 越界 422 / 课程日缺失 404 / kind 非法 422） |

**验收证据**：后端 166 passed（P0 前 156），dev 库指纹 `md5sum -c` 不变；
前端 `tsc --noEmit` exit 0；10 条路由全部可达；`/` 307 → `/today`。

**关键口径**：任务列表为空是**正常且诚实**的状态 —— 当天的执行内容由
`PlanDay.acceptance` 定义，任务只是 Planner 的产物（P1/P2 才会自动挂到当天）。
不要为了让页面"看起来满"而伪造绑定。

---

## 十二、P1 实施记录（2026-09-11）

P1 已落地并通过验证。核心是把"课程进度"与"日历进度"解耦，并对落后日期做
**只提示、不自动顺延**的手动决策（压缩 / 顺延 / 放弃）。

### 12.1 滑期算法口径（落到 `GET /api/plan/overview`）

```
day_index  = 日历推导的「今天算课程第几天」（clamp 1..30，沿用 P0 的 _resolve_day_index）
view_seq   = ?day= 覆盖值（默认 = day_index），仅影响以下口径
completed  = 满足「status ∈ (done, compressed) 且 seq <= view_seq」的天数
behind     = max(0, view_seq - completed)          ← 落后几天
is_missed  = (seq <= view_seq) 且 status 未通过     ← 标红待决策
```

「某天通过」判定两条路（与 /today 四件套口径一致）：
- 有 `day_progress` 且 `status ∈ (done, compressed)`
- 或四件套齐全（day_artifacts 含全部 4 类）

### 12.2 决策写入口（`POST /api/plan/progress`）

幂等 upsert（同 plan_day_id 重复提交即更新）。三个决策 + 完成：

| status | 语义 | 执行日期 | deviation_note |
|---|---|---|---|
| `done` | 四件套齐全 / 明确完成 | 写今天 | 可选 |
| `compressed` | 压缩：验收降级速通，算过 | 写今天 | **必填**（默认文案） |
| `deferred` | 顺延：推后手动补，**不自动顺延后续天** | 清空 | 必填 |
| `skipped` | 放弃：不再投入，释放时间 | 清空 | 必填 |
| `pending` | 复位（清理用） | 清空 | —— |

**硬约束**：落后时页面把标红日期交给用户手动选一个决策，选择必须落 `deviation_note`
（至少带默认文案），平台绝不自动顺延 —— 否则 30 天变 45 天（风险 3）。

### 12.3 交付物

| 层 | 文件 | 说明 |
|---|---|---|
| 模型 | `app/models/day_progress.py` | 执行记录：plan_day_id UNIQUE + status/calendar_date/actual_minutes/deviation_note |
| 迁移 | `migrations/0012_day_progress.sql` | 建表（单语句，注释无分号） |
| 导出 | `app/models/__init__.py` | 加 `DayProgress` |
| 模型 | `app/schemas/plan.py` | DayProgressOut / ProgressUpdate / PlanDayStatusItem / PlanOverview |
| 接口 | `app/api/plan.py` | 新增 `GET /api/plan/overview`、`POST /api/plan/progress`（沿用 /plan 路由前缀） |
| 类型 | `frontend/src/types/index.ts` | PlanDayStatus / PlanOverview |
| 服务 | `frontend/src/services/planService.ts` | getPlanOverview / setDayProgress + snake→camel adapter |
| 页面 | `frontend/src/app/plan/page.tsx` + `components/PlanBoard.tsx` | 施工总览（默认 Server Component + 客户端决策） |
| 导航 | `GlobalNav` 加「施工」→ /plan（在「今日」之后） | IA 落实：今日 / 施工 / 概览 … |

### 12.4 验证

- 后端 `tests/test_plan_api.py`：P0 的 10 项 + P1 的 4 项 = **14 passed**
  （覆盖：overview 落后计数、compressed 计入课程进度、status 非法 422、未知 plan_day 404）
- 前端 `tsc --noEmit` exit 0（修了一处 `null` vs `undefined` 类型错）
- 实时冒烟（`urllib` 直打 127.0.0.1:8000）：
  `?day=5` → `behind=5, completed=0`；标记 Day1=compressed → `behind=4, completed=1`；
  复位 → `behind=5`。结果符合"只提示不自动顺延"
- `/plan` SSR：200，含「施工总览 / 30 天课程脊梁 / 滑期横幅」

### 12.5 一个实现坑（已修）

`get_overview` 里 `else: status = PROGRESS_PENDING` 引用了未导入的常量
（`PROGRESS_PENDING` 漏进 import），首跑 500。已在 `plan.py` 的 day_progress
import 补回 `PROGRESS_PENDING`。教训：新增分支引用的常量要确认已 import。

### 12.6 与规划的一致 / 偏离

- **一致**：决策 1（seq 与日历解耦）、风险 3（只提示不自动顺延）全部落地。
- **偏离**：规划 §五把 `day_progress` 之外的 `experiments`/`artifacts` 改写列在 P2/P3，
  本阶段**未动** day_artifacts 结构（仍按 plan_day_id 归属，不是 day_progress_id），
  保持 P0 契约，避免一次改两张表引入回归。P2 再决定要不要把 artifact 改挂 day_progress。

---

## 十三、P2 实施记录（2026-09-11）

P2「证据闭环」已落地并通过验证。五项机制全部实现：让「今天做了没有」和
「技能凭什么晋级」都由**真实证据**判定，而不是手工勾选或自评。

### 13.1 五项机制

| # | 机制 | 落地位置 | 口径 |
|---|---|---|---|
| A | `experiments` 表 + CRUD | `api/experiments.py` | `variants`/`metrics` 原样存 JSON，前端直接渲成对比表 |
| B | questions 轴自动判定 | `api/plan.py` `/today` `/overview` | 当日 `interview_questions.source_day_seq` 计数 ≥ `QUESTIONS_MIN_PER_DAY`(=5) → 视为已交 |
| C | commit 按日期自动归集 | `api/plan.py` `/commits/sync` + `core/github_client.py` | commit 日期 − SPRINT_START + 1 = 课程日；写 `day_artifacts(kind=commit, auto_verified=True)`，按 `(plan_day, sha)` 去重 |
| D | 技能晋级 evidence-gated | `core/evidence.py` + `api/skills.py /evidence` | L1 note/题 → L2 code+已核验 commit → L3 Experiment → L4 对比实验+复现报告；结果写回 `skills.evidence_gate` |
| E | `TECH_BLACKLIST` 硬拒绝 | `api/planner.py` `/generate` | 命中 D 级技能直接剔除候选；全被拦截时返回 `blocked` + ⛔ 拒绝文案，不降级、不静默 |

**commit 同步的三路来源**：① `payload.commits` 直传（测试 / 演示，绕过 GitHub API）；
② 真实 GitHub（`repo`/`token` 缺省读 `PLAN_REPO` / `GITHUB_TOKEN`）；③ 无 token 时
`skipped=True` 优雅跳过（不 500）。客户端只用 stdlib `urllib`，不引入新依赖。

### 13.2 交付物

| 层 | 文件 | 说明 |
|---|---|---|
| 迁移 | `migrations/0013_experiments.sql` | 建表（单语句，注释无分号） |
| 迁移 | `migrations/0014_interview_questions_meta.sql` | +3 列：source_day_seq / skill_name / is_verified |
| 迁移 | `migrations/0015_skills_evidence_gate.sql` | +1 列：evidence_gate |
| 模型 | `app/models/experiment.py` | Experiment（kind: finetune/benchmark/ablation） |
| 模型 | `app/models/interview_question.py` / `skill.py` | 补 P2 三列 / evidence_gate 列 |
| 逻辑 | `app/core/evidence.py` | evidence-gated 推导（纯规则，不烧 token） |
| 逻辑 | `app/core/github_client.py` | commit 拉取 + 日期→课程日映射 |
| 接口 | `app/api/experiments.py`（新）· `plan.py`（+/commits/sync）· `skills.py`（+/evidence）【+2】· `planner.py`（黑名单） | |
| 前端 | `types` + `services/experimentService.ts` | Experiment / CommitSyncResult / SkillEvidence + adapter |
| 前端 | `components/ExperimentTable.tsx`·`ExperimentBoard.tsx`·`EvidenceBoard.tsx` | 对比表渲染器 + 录入表单 + 证据链视图 |
| 页面 | `app/experiments/page.tsx`·`app/evidence/page.tsx` | 两个 Server Component 页（force-dynamic） |
| 导航 | `GlobalNav` 加「实验」→ /experiments、「证据」→ /evidence | IA：今日 / 施工 / 实验 / 证据 / 概览 |

> 约定沿用：新增业务逻辑一律落成**独立纯规则模块**（`core/*.py`），不套 BaseAgent /
> LangGraph —— 见 §0.1.3「有意偏离」。本阶段 `evidence.py` / `github_client.py` 均遵循。

### 13.3 验证

- 迁移：`run_migration.py --only 0013/0014/0015` 全部 ✓，`PRAGMA table_info` 复核
  `experiments` 12 列、`interview_questions` 三新列、`skills.evidence_gate` 均存在
- 后端 `tests/test_p2_evidence_loop.py`：**8 passed**（experiments CRUD / 过滤 /
  非法 kind·day_seq 422 / 题库条数自动判定 / commit inline 归集与去重 / 无 token 跳过 /
  evidence-gate≥L3 / 黑名单硬拒绝）
- 回归：`test_planner_project_context` + `test_task_track_scope` + `test_plan_api`
  共 **26 passed**（planner.py 改了 `GeneratedTaskOut`，需回归确认）
- 前端 `tsc --noEmit` exit 0
- 实时冒烟（`urllib` 直打 127.0.0.1:8000）：`/api/skills/evidence` 200（48 技能）、
  `/api/experiments` 200、`/commits/sync` inline `synced=1`、`/today` 含
  `questions_from_bank`、实验 3 变体、`/overview behind=2`；写入的实验与 commit 已即时清理
- SSR：`/experiments` 200（「实验对比」）、`/evidence` 200（「证据可信度」）、
  `/today` 200（含「同步 GitHub commits」按钮）
- **开发库零污染**：跑完全部测试后 `experiments=0`、`day_artifacts=0`、
  无 `source_day_seq` 非空题、无 `P2 ·` 残留 —— 隔离闸门有效

### 13.4 两个实现坑（均已修，均由验证阶段发现）

1. **黑名单拒绝分支 500**：`GeneratedTaskOut.duration` 无默认值，而 `/generate` 的
   拒绝分支不产生任务时长 → pydantic `ValidationError`。P2 单测首跑即命中。
   修法：`duration: int = 0`。
2. **前端类型漏字段**：`planService.ts` 的 `TodayDTO` 未加 `questions_from_bank`，
   `tsc` 报 `TS2339`。修法：接口补 `questions_from_bank: number`。

教训：**新端点要么被测试覆盖、要么被类型检查覆盖**，二者缺一就会把 500 / 编译错放过去。

### 13.5 与规划的一致 / 偏离

- **一致**：决策 3（evidence-gated）、决策 4（实验一等公民）、决策 6（黑名单硬拒绝）
  全部落地；P2 验收两句——「填一次 LoRA vs QLoRA 实验，页面直接渲染对比表」
  （`ExperimentTable` 按 variants 字段并集出列）与「技能升级因为这份代码/实验」
  （`EvidenceBoard` 的 typed evidence ref）——均已在 `/experiments`、`/evidence` 达成。
- **偏离**：规划 §七 P2 前端列了「四件套详情抽屉」，实际落地为**两个独立页**
  （`/experiments`、`/evidence`），未做抽屉。理由：证据链是跨课程日的长列表，
  抽屉装不下且与 `/today` 的「今天」语义冲突；独立页更契合「面试时打开对照」的场景。
- **沿用 §12.6 契约**：`day_artifacts` 仍按 `plan_day_id` 归属（未改挂 day_progress）；
  `SKILL_TO_DAY_SEQ` 仍只收录课程特有技能，未改键；questions 自动判定用
  `interview_questions.source_day_seq`（绑 seq 而非 plan_day_id），与 day_progress 同哲学。

---

## 十四、P3 实施记录（2026-09-11）

P3「题库生长 + 模拟面试」已落地并通过验证。核心是把计划里两个冲突的口径（150 vs 80）
裁决清楚，并用覆盖率矩阵把「缺口在哪」变成页面上的红格。

### 14.1 口径裁决（决策 5）

| 出处 | 数字 | 平台口径 |
|---|---|---|
| §十「每天 5 题 × 30 天」 | 150 | **累计目标 150**（上界） |
| §八 Day 26/27「50 LLM + 25~30 VLM」 | ~80 | **核心必达 80**（下界，LLM 50 + 多模态 30） |

分类目标（`agents/interview/engine.QUESTION_CATEGORY_TARGETS`）：LLM 50 / Multimodal 30 /
Project 40 / Coding 30 = 150；核心分类 = LLM + Multimodal（`CORE_TARGET = 80`）。
先保 80 核心，避免"要写 150 题"的挫败感。

### 14.2 三个能力

| 项 | 内容 |
|---|---|
| 快速录题 | 单输入框（Enter 提交 / Shift+Enter 换行 / 支持粘贴多行一次录多道）+ 分类·技能下拉 + 可选答题要点 |
| 覆盖率矩阵 | skill × category 网格，**红格 = 该 (技能, 分类) 一题为 0**；行 = 主攻赛道 `required_skills` ∪ 题库已出现的 `skill_name`；另有四分类 done/target 进度条 |
| 抽题模拟 | 沿用 `/api/interview/simulate`（纯规则，命中次数少者优先） |

### 14.3 交付物

| 层 | 文件 |
|---|---|
| 引擎 | `agents/interview/engine.py` +`QUESTION_CATEGORY_TARGETS` / `CORE_TARGET` / `coverage_matrix()`（纯函数） |
| Schema | `schemas/interview.py` +CoverageCategoryOut / CoverageSkillOut / QuestionCoverageOut |
| 接口 | `api/interviews.py` +`GET /api/interview-questions/coverage?track_key=` |
| 类型 | `types/index.ts` +CoverageCategory / CoverageSkill / QuestionCoverage；`InterviewQuestion` 补 P2 三字段 |
| 服务 | `interviewService.ts` +`getQuestionCoverage()`；**修复** `createQuestion` 未转 snake_case |
| 组件 | `components/QuestionBoard.tsx`（新） |
| 页面 | `app/questions/page.tsx`（新，Server Component + PageHeader） |
| 拆分 | `InterviewBoard` 去掉题库/抽题（迁到 `/questions`），只留面经 → 弱项 → 回写；`/interview` 不再取题库 |
| 导航 | `GlobalNav` +「题库」→ /questions |

**无新迁移**：`source_day_seq` / `skill_name` / `is_verified` 三列 P2 已加（0014），P3 不动表结构。

### 14.4 验证

- 后端 `tests/test_p3_question_coverage.py`：**7 passed**（引擎口径 150/80、红格、未知技能补行、
  端点形状、`?track_key=` 切换、快速录题联动、清理回基线）
- 回归：`test_interview_engine.py` + `test_p2_evidence_loop.py` 共 **18 passed**
- 前端 `tsc --noEmit` exit 0
- 实时冒烟（127.0.0.1:8000 / :3000）：`/coverage` total=15 target=150 core=10/80 skills=8 cells=0/32；
  POST 一题（skill=Transformer）→ 该格 0→1；SSR `/questions` 200（"题库与覆盖率"）、`/interview` 200
- 开发库零污染：冒烟题已删，`interview_questions` 仍 15、无残留

### 14.5 顺带修掉的历史 bug

`interviewService.createQuestion` 旧实现**直接 post camelCase**（`answerOutline`），而
`apiClient` 不做 key 转换、后端字段是 `answer_outline` → 被 Pydantic 当未知字段忽略，
**答题要点被静默丢弃**（UI 新建题的 outline 一直是空的）。
P3 改为显式 snake_case 映射（含 `source_day_seq` / `skill_name` / `is_verified`）。
教训：service 层"直接透传 payload"会漏掉 camel→snake 转换，聚合字段尤其容易漏。

### 14.6 与规划的一致 / 偏离

- **一致**：决策 5 全部落地；P3 验收两句（每天录题 ≤1 分钟、Day 26 看「缺口在哪」）
  由快速录题框 + 红格矩阵承接。
- **落实 IA**：§九把「题库」列为一级入口 —— 本阶段从 `/interview` 拆出独立 `/questions` 页，
  面经线保持单一职责。**没有做两套前端**：题库 / 抽题只此一处实现。
- **偏离**：分类目标里 Project/Coding 的 40/30 无原文依据（计划只给了 LLM 50 + VLM 30），
  是按"补满 150"倒推的。若日后有更明确的分配，只改 `QUESTION_CATEGORY_TARGETS` 一处。

> 🔴 **2026-09-22 更正**：上面这句"只改一处"**当时是错的**。实测当时 150 硬编码在**两处** ——
> `agents/interview/engine.py` 的 `QUESTION_CATEGORY_TARGETS`，以及 **`api/plan.py` 的
> `TARGET_QUESTIONS = 150`**（30 天计划总账的「面试题」KPI，是独立的一份）；`CORE_TARGET = 80`
> 也是独立字面量、不从分类目标派生。现已改为**单一真源 + 派生**：只改
> `QUESTION_CATEGORY_TARGETS`，`CORE_TARGET` 与 `api/plan.py` 的 `TARGET_QUESTIONS`
> 自动跟随；回归护栏见 `backend/tests/test_p3_question_coverage.py`。
> 仍保留的字面量只剩**展示文案**（`core/plan_30d.py` Day30 验收、前端
> `QuestionBoard.tsx` 空态提示），不参与任何判定。

---

## 十五、P4 实施记录（2026-09-11）

P4「求职包装自动化」已落地并通过验证。核心命题：**Day 24/25 的 README 和简历应该是
"导出 + 润色"，不是"从空白开始写"** —— 把 P2 攒下的证据链接到成品上。

### 15.1 三项要求 → 三个交付

| P4 要求（§七） | 落地 |
|---|---|
| README 骨架从证据链生成（Motivation→…→Failure Cases） | `services/packaging/engine.build_readme_skeleton()`：13 节论文体骨架（逐字对齐 plan_30d Day 24 结构），**数据能填的自动填、只有人能写的留带提示的占位** |
| 简历技能行自动附证据链接 | `build_skill_lines()` + `GET /api/resume/skill-lines`：**只收录 `evidence_gate >= 1` 的技能**，每行附 `refs`；自评 ≥3 却无证据的进 `pending`（= 写进简历即虚构） |
| 项目页 → 证据链视图；`/jobs` 提为主位 | `ReadmeDraftCard` 挂在 `/projects/[id]`；`GlobalNav` 把「求职」提到「今日」之后 |

### 15.2 README 的两类内容（设计要点）

| 类型 | 处理 | 例 |
|---|---|---|
| 数据能填 | 从证据链自动填 | 里程碑进度表、涉及技能及证据等级（`compute_skill_evidence` 的 `ref`）、实验记录对比表 |
| 只有人能写 | **留带写作提示的占位**，不留白 | Motivation / Architecture / Environment / Dataset / Training / LoRA & QLoRA / VLM / Evaluation / Inference Benchmark / Results / Future Work |

`Failure Cases` / `Lessons Learned` 标为 `⚠️ **必填**` —— 对应 Day 24 验收的
「不得空着」与「像论文不像课程作业」。

### 15.3 交付物

| 层 | 文件 |
|---|---|
| 引擎 | `services/packaging/engine.py`（纯函数 `build_readme_skeleton` / `build_skill_lines`） |
| 取数 | `services/packaging/service.py`（项目技能 = 里程碑任务 `skill_name` 去重；项目实验 = `skill_name` 命中该技能集） |
| Schema | `schemas/project.py` +`ProjectReadmeIn` |
| 接口 | `api/projects.py` +`GET/POST /{id}/readme`；`api/resume.py` +`GET /api/resume/skill-lines` |
| 重构 | `patch_project` 的**内联 README 拼接删除**，改调同一构建器 —— 否则 GET 预览与自动生成会是两套实现，口径必然漂移 |
| 类型/服务 | `types/index.ts` +ProjectReadme/SkillLine/SkillLinePending/SkillLineReport；`packagingService.ts`（新） |
| 组件 | `ReadmeDraftCard.tsx`（预览 / 重新生成 / 保存 / 复制 / 下载 .md）、`SkillLinesCard.tsx`（ready + pending 两组） |
| 页面 | `projects/[id]/page.tsx` +README 卡；`resume/page.tsx` +技能行卡（`ResumeBoard` 增 `initialSkillLines`） |
| 导航 | `GlobalNav`「求职」提为主位 |

**无新迁移**：`projects.readme`（既有列）与 `skills.evidence_gate`（P2 的 0013）都已存在，
P4 只加接口与展示。

### 15.4 验证

- 后端 `tests/test_p4_packaging.py`：**11 passed**（空数据骨架含全 13 节 / 必填标记 /
  证据与实验落正文 / 技能行过滤与排序 / GET 预览无副作用 / 一键导出落库 / 润色回存 /
  空内容 400 / 404 / patch completed 自动生成回归 / skill-lines 形状 / 录题→ready 增长闭环）
- 回归：`tests/test_project_readme.py` 3 passed（旧 README 契约未破）；全量 `pytest tests -q` → **198 passed**
- 开发库零污染：跑完全量测试与实时冒烟后 `app.db` md5 与之前完全一致（`55da06bb…`）
- 前端 `tsc --noEmit` exit 0
- 实时冒烟（127.0.0.1:8000 / :3000）**18 项全过**：`/api/projects/1/readme` 取 7 条里程碑
  → 1602 字符骨架、`saved_readme` 为 null 且 GET 无副作用；`/api/resume/skill-lines`
  total=48 / ready=0 / pending=16；SSR `/projects/1`（"README 骨架"）与 `/resume`
  （"技能行（附证据）"）均 200

### 15.5 冒烟抓到的 bug：summary 与列表长度不一致

`build_skill_lines` 首版把 `pending` 截断到 12 条，但 `summary.pending` 报的是**截断前**的 16 ——
前端会显示"待补证据 16 项"却只渲染 12 个 chip。单测没覆盖这条，**实时冒烟的自洽断言抓到了**。
修法：去掉截断（条数受技能总数 48 约束，无需保护），并补断言钉死
`summary.pending == len(pending)`。教训：**summary 必须与它描述的列表同源生成**，
"截断 / 分页"是这类不一致的高发点。

### 15.6 现状与下一步

当前真实数据下 `ready = 0`（48 项技能 `evidence_gate` 全为 0、`experiments` 表为空、
项目 1 的里程碑任务未打 `skill_name`）—— **这是诚实的空状态，不是 bug**：
按 P2 规则，得先有笔记 / 代码 / 实验，简历行才长得出来。`pending` 的 16 项正是
"自评 ≥3 但尚无证据"的高风险行（Agent Application / Explainability / FastAPI / …），
它们就是 P4 之后最该优先补证据的对象。

**路线图 P0–P4 全部完成。** 若继续投入，优先级是把 Day 1–30 的真实产出
（笔记 / 代码 / commit / 实验）填进去，让 `ready` 从 0 长起来 —— 那时是"用平台"，不是"造平台"。
