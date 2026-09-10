# 求职 Agent 设计方案

> 输入：《求职 Agent 工作指导 v1.0》+《求职 Agent 开发与运行规范 v2.0》
> 现状：Embodied AI Career OS（FastAPI + Next.js，已有多 Agent Runtime）
> 日期：2026-09-10｜冲刺窗口：2026-09-10 ～ 2026-10-09

---

## 0. 先说结论：三件事必须先定

### 0.1 战略冲突：现有配置和 v2.0 是反的

v2.0 把具身智能明确列进 **D 级「一个月主动不深挖」**（VLA / World Model / Robot Learning /
ROS2 / Isaac Lab / SO101），而当前系统的核心配置全是具身导向：

| 位置 | 现状 | v2.0 要求 | 处理 |
|---|---|---|---|
| `core/target_roles.py` | embodied 主攻 / robot-software 折中 / agent 保底 | LLM 主攻、VLM 卡位、AI 算法保底 | **增量**（新增 3 条，旧赛道 frozen 保留） |
| `core/skill_profile.py` | ROS2 / Isaac / VLA / Sim2Real / MoveIt2 为主要缺口 | Transformer / SFT / LoRA / KV Cache / vLLM | **增量**（新增 33 项，D 级 target=level 冻结） |
| `agents/career/rules.py` | `Robot AI Engineer` 要求 ROS2+Isaac | LLM / Multimodal / Foundation Model 三梯队 | **增量**（新增 5 个岗位，旧岗位保留） |
| `agents/research/templates.py` | ACT / VLA / Isaac Lab / ROS2（**全在 D 级黑名单**） | 按 A/B/C 级主题新增 | **增量**（新增 5 主题，旧模板保留备用） |
| `so101/` | 视为主线资产 | 保留代码，不投入时间 | 冻结，转工程能力旁证 |

**不做这件事，Agent 会天天推你去学被明令禁止的东西**——这是所有其他设计的前置项。

### 0.1.1 处理方式：冻结（freeze）而非删除

用户明确要求**利用现有基建、不抛弃旧内容**，所以配置层全部走"增量 + 冻结"：

| 机制 | 做法 | 效果 |
|---|---|---|
| 赛道冻结 | `TargetRole.frozen = True` | 仍计算匹配度、仍在看板展示（视觉降权），但不进入推动列表 |
| 技能冻结 | `target_level == level` | gap 恒为 0，永远排在缺口列表末尾，但历史 evidence 完整保留 |
| 模板保留 | 旧 research 模板不删，仅标注"长期保留，当前不主动推荐" | 未来重启具身方向时直接可用 |
| 数据保留 | JobApplication 的 `track=embodied` 记录不动 | 历史投递数据不丢 |

这样既换了主线，又没扔掉 SO101 / ROS2 / Mujoco 的实际积累——
它们在简历里仍是"能动手做硬件闭环"的工程能力旁证，只是不再占用今天的 8 小时。

### 0.1.2 复用清单（一个字都不用改的现有基建）

| 基建 | 复用方式 |
|---|---|
| `agents/core/`（BaseAgent / Executor / Registry / State） | 新增 Agent 直接实现契约即可被调度 |
| `agents/orchestrator/`（失败隔离执行链） | 新 Agent 编入 plan 即享受失败隔离 |
| `agents/supervisor/`（意图路由） | 只需扩枚举，不改图结构 |
| `api/job_hunt.py` 聚合模式 | 新数据（岗位池/匹配）沿用一次请求聚合，避免 N+1 |
| `scripts/seed_job_hunt.py` 幂等校准机制 | `calibrate_skills()` 直接完成 48 项技能对齐 |
| `services/reminder/scheduler.py`（APScheduler） | 日报/周报作为新 job 挂上去 |
| `llm/` Provider 抽象（mock/ollama/deepseek） | 简历诊断、面试模拟接真实 LLM 时零改造 |
| `/jobs` 前端看板 + `types/` 适配层 | 新增赛道/字段只需扩类型与元数据 |

### 0.1.3 实现备注（Batch 1 · 2026-09-10）

- **MatchAgent 实现为有意为之的"偏离"**：设计把 MatchAgent 列为 `BaseAgent` 子类，但
  `BaseAgent` 抽象强制 `build_graph()` 返回 LangGraph 图。纯同步、需可单测/可解释/不烧 token 的
  评分函数套 LangGraph 是过度设计，也违背"利用现有基建、不过度搭建"的反馈与 §0.2 原则。
  因此落地为 `backend/app/agents/match/engine.py` 中的独立可测模块（`JDParser` + `MatchEngine`），
  API 直接调用。**这仍是 Agent 能力，只是不强制 LangGraph 契约**——JDParserAgent 同理（解析即
  关键词命中，无需图编排）。后续若要做"JD 结构化 → 多 Agent 协同诊断"，再按 `BaseAgent` 接入。
- **评分可解释**：5 维分项（技术栈40 / 项目25 / 学历年限15 / 科研10 / 行业10）全部确定性规则，
  `GET /api/job-postings` 每条内联 `dimension_scores` 与 `gaps`，前端抽屉逐维展示"为什么是这个分"。
- **踩坑**：`SessionLocal(autoflush=False)`，录入时新增的 `JobMatch` 在 `commit()` 前 SELECT 不到，
  故 `POST /api/job-postings` 直接用 `_match_and_store` 返回的内存对象构造响应，不回查。
- **种子样例**：`init_db` 幂等播种 4 条跨赛道 JD（llm/vlm/ai-algo/embodied），首次启动即填满岗位池，
  便于直接看匹配效果。

### 0.1.4 实现备注（Batch 2 · 2026-09-10）

- **ResumeAgent 实现为有意为之的"偏离"**（与 MatchAgent 同）：设计把 ResumeAgent 列为 `BaseAgent`
  子类（依赖 LLM 做解析/诊断/生成），但"防虚构校验"是硬约束（v2.0 §8：每条 claim 必须有 ResumeFact
  锚点，否则标红），必须是确定性、可单测、可解释、不烧 token 的规则。因此落地为
  `backend/app/agents/resume/engine.py` 中的独立可测模块（纯规则 + 锚点库），API 直接调用。
  LLM 仅在未来做"措辞优化 / 生成建议"的增量，且生成内容同样要再过一遍防虚构校验——这仍是 Agent
  能力，只是不强制 LangGraph 契约。
- **防虚构校验流程**：`extract_claims(md)` 抽取可校验 claim（bullet/编号项/含指标独立行，跳过
  markdown 标题与"小节标签"短行）→ 与 `ResumeFact` 做**归一化子串匹配**（去空白 + 去标点 + 转小写，
  保留 `% + →` 等事实常用符号）；命中→绿（记录锚点 fact title），未命中→红（原因：未在事实锚点库找到依据）。
- **评分可解释**：前端逐条展示"为什么绿 / 为什么红 / 依据是什么"；给定 `posting_id` 时额外输出
  `jd_alignment`——JD 每条要求技能在事实库 / 已锚定 claim 中是否有依据（✓/✗）。
- **种子**：`init_db` 幂等播种 9 条真实 `ResumeFact`（源自 `docs/MY_CONTEXT.md`：标书审核 /
  科研知识库 / 油耗 SaaS / STM-SHAP / RL-RA-QR / 北航·郑航学历 / 技术栈自评 / SO101）+ 1 个示例版本
  「LLM 主攻版（示例）」（含 2 条演示性虚构 claim）。实测：13 claim → 11 锚定 / 2 标红 / 风险 15%。
- **踩坑**：`ResumeFact`/`ResumeVersion` 的 import 不能放进 `if db.query(ResumeFact).count()==0:`
  块内——Python 会把该名字视为函数内未赋值 local，在 `if` 条件里引用时抛 `UnboundLocalError`。
  已把这两行 import 提到 `_seed_if_empty` 顶部（与既有 `JobPosting`/`JobMatch` 等 import 并列）。
- **实施量**：后端 2 表 + 引擎 + 9 个 API + 种子；前端 `/resume` 页（ResumeBoard：版本列表 / 防虚构
  诊断 / 事实锚点库）+ 服务层 + 导航；9 个单测；smoke 新增 4 项。纯增量，未动框架层。

### 0.1.5 实现备注（Batch 3 · 2026-09-10）

- **InterviewAgent 同样落地为独立可测模块**（与 MatchAgent / ResumeAgent 一致）：
  `backend/app/agents/interview/engine.py` 纯规则三段——`aggregate_weakness()`（弱项聚合）、
  `weak_to_tasks()`（弱项 → 学习任务草稿）、`pick_questions()`（题库抽题）。理由是"面经 → 补知识"
  闭环的核心是**确定性聚合与推导**（弱项按频次排序、缺口映射到技能与任务模板），不是 LLM 生成；
  套 `BaseAgent`/LangGraph 无收益。模拟面试的"评分"当前用规则（命中/命中率/hit_count），
  未来若要做"答题质量打分"再引 LLM，且不改变题库契约。
- **闭环落点**：`POST /api/interviews/{id}/to-tasks` 把弱项/知识缺口直接写成 `Task`（复用既有 Task 模型，
  `status=todo`、`skill_name` 关联技能画像），回写后前端「任务」页与 `Planner` 立即可见——真正做到
  "面经变学习任务"，而非另起一套待办。
- **题库抽题策略**：按 `category` 过滤 → 优先级排序（低频优先，保证覆盖面）→ 命中后 `hit_count += 1`，
  支撑 v2.0 §Day26/27 的"50+30 题"刷题机制，避免反复刷同几题。
- **种子**：`init_db` 幂等播种 15 道题库（LLM / Multimodal / Project / Coding 四类）+ 1 条示例面经
  （含弱项与知识缺口）。实测：`/api/interviews/stats` 正确聚合弱项频次；`to-tasks` 回写 4 条 Task；
  `simulate` 抽 3 题且 `hit_count` 递增。
- **实施量**：后端 2 表 + 引擎 + 面经/题库/统计/回写/模拟 API + 种子；前端 `/interview` 页
  （InterviewBoard：面经记录 / 弱项统计 / 题库练习 / 模拟抽题）+ 服务层 + 导航；单测 + smoke 新增 5 项。
  纯增量，未动框架层。

### 0.1.6 实现备注（Batch 4 · 2026-09-10）

- **报告引擎同样是纯规则独立模块**（与 Match / Resume / Interview 一致）：
  `backend/app/services/report/engine.py` 分「构建」与「渲染」两层——`build_daily` / `build_weekly`
  读库组装 `ReportData`（sections + metrics），`render` 负责出 markdown。核心是确定性聚合
  （漏斗统计、缺口排序、弱项聚类、停滞判定），没有需要 LLM 判断的环节。
- **编排与计算分离**：`services/report/service.py` 只做 build → 落库 → 推送 → 标记 sent。
  这样调度器与 API 共用同一条链路，`/reports` 页与推送内容永远一致。
- **幂等靠 (kind, period_key) 唯一约束**：`ReportLog` 对 `(kind, period_key)` 建唯一索引，
  日报 period_key=日期、周报=ISO 周（`2026-W37`）。同一期已 `sent=True` 时默认跳过，
  `force=true` 才重推——避免 dev server 热重载或进程重启导致同一天重复推送。
- **跟进提醒的判定是"或"关系**（`due_followups`）：
  1. `next_action` 文本能解析出日期且 <= 今天（支持 `2026-09-12` / `9/12` / `12日`，跨年自动顺延）；
  2. 状态仍是 applied/screening 且 `updated_at` 停滞 >= `report_followup_stale_days`（默认 5 天）。
  offer/rejected 等终态不再提醒；无待跟进时不发空提醒。
- **顺手做了 DRY 重构（低风险）**：`reminder/channels.py` 新增 `build_channel()` 工厂，
  `ReminderEngine.__init__` 改为委托它，报告服务复用同一个通道构造逻辑——避免两处各自
  处理 serverchan 的 key 分支。已有 `test_reminder.py` / `test_reminder_channels.py` 全绿。
- **踩坑**：新增的 `ReportLog` 必须被 `app.models` 导入，否则 `Base.metadata.create_all` 建不出表；
  已在 `models/__init__.py` 注册。另外 `JobApplication.updated_at` 带 `onupdate`，测试里若要
  伪造"停滞"必须在 **INSERT 时**给值（UPDATE 会被 `onupdate` 覆盖）。
- **图表外的实感**：日报把"推荐岗位 / 简历动作 / 面试题 / 学习任务 / 投递 / 今日优先"合成
  一屏，正好覆盖 v2.0 §23.1 要求的七项；周报覆盖 §23.2 六项（含"博士积累"= 科研底座技能 + 论文进度）。
- **实施量**：后端 1 表（ReportLog）+ 引擎 + 编排服务 + 6 个 API + 3 个调度 Job + 配置项；
  前端 `/reports` 页（ReportsBoard：调度配置 / 待跟进 / 日报周报正文 / 归档历史）+ 服务层 + 导航；
  21 个单测；smoke 新增 7 项（6 API + 1 页面）。纯增量，未动框架层。

### 0.2 精力分配：文档明确禁止把主要精力放在 Agent 框架上

v2.0 §17「不再把主要精力放在 Agent Framework」、§24.2「不允许一次性生成整个项目」。
所以本方案的原则是：

> **复用现有 Runtime，只按 `BaseAgent` 契约加业务 Agent，不重构框架；
> 匹配与评分先用纯规则（可解释、可单测、不依赖 LLM），LLM 只做措辞与生成类增量。**

你真正要花时间的是 LLM Core（30%）+ Coding/Training（25%），这个 Agent 系统只是你的工具，
不该反过来吃掉冲刺时间。整体实施量控制在 **8 个工作日以内**，且只做批次 0+1 就已经能用。

### 0.3 优先级锁（写进代码，不靠自觉）

```
求职 > LLM 核心能力 > 项目 > 博士准备 > 具身
```

对应 v2.0 §13 的 P0–P5。系统里所有任务排序、冲突提示都按这个来。

---

## 1. 能力缺口：v2.0 的 8 个模块 vs 现有系统

| # | 模块 | 现状 | 缺口 | 优先级 |
|---|---|---|---|---|
| 1 | 简历解析 | 无 | 全缺 | P1 |
| 2 | 方向推荐 | Career Agent（gap 分析 + 路线生成）| 配置需重排 | P0（改配置即可）|
| 3 | 计划生成 | Planner Agent（规则 + LLM 双生成器）| 接 30 天路线模板 + 面试回写 | P1 |
| 4 | 资源检索 | Knowledge Agent（论文 RAG）+ Research Agent | 主题库重配；可做学习资源库 | P2 |
| 5 | 简历诊断 | 无 | 全缺（含防虚构校验） | P1 |
| 6 | 面试模拟 | 无 | 全缺（题库 + 面经回写） | P1 |
| 7 | 投递跟踪 | ✅ `JobApplication` + `/jobs` 看板 | 缺 JD 字段、匹配度、面试记录 | P0（扩展）|
| 8 | JD 匹配 | 无 | 全缺（v2.0 给了 5 维权重） | **P0** |

**判断**：离 P0（10 月底上岸）最近的是 **#8 JD 匹配 + #7 投递跟踪**——
"找岗位，不盲投"直接决定投递效率。简历诊断和面试模拟重要但可以后置一周。
所以实施顺序是 **配置重排 → 岗位池/匹配 → 简历线 → 面试线 → 日报周报**。

---

## 2. Agent 拓扑设计

```
                     Supervisor（意图路由 4 → 8 类）
                              │
        ┌─────────┬───────────┼───────────┬──────────┐
        │         │           │           │          │
     Planner   Reviewer    Career    Research   Knowledge   ← 现有（改造）
        │                     │           │
        │              ┌──────┴───┐       │
        │              │          │       │
   JDParser ──→ MatchAgent    ResumeAgent  │             ← 新增
                        │          │
                        └── InterviewAgent ──┘           ← 新增
                                  │
                          回写 Task（面试题 → 学习任务）
```

### 2.1 新增 4 个 Agent（全部复用 `BaseAgent` 契约）

| Agent | 职责 | 输入 → 输出 | 是否依赖 LLM |
|---|---|---|---|
| **JDParserAgent** | 岗位录入与 JD 结构化 | JD 文本 → `{公司/岗位/城市/薪资/技术要求/学历/经验/论文要求/梯队}` | 可选（规则优先） |
| **MatchAgent** | JD × 简历匹配评分 | JobPosting + 能力矩阵 → 分数 + A/B/C/D + 差距 | **否**（纯规则，可解释） |
| **ResumeAgent** | 简历解析 / 诊断 / 多版本 | 简历 md → 结构化画像；+JD → 修改建议 | 是 |
| **InterviewAgent** | 出题 / 评分 / 反馈闭环 | 岗位方向 → 题目 + 评分；面经 → 学习任务 | 是 |

**为什么 MatchAgent 坚持纯规则**：v2.0 要求"能解释为什么是这个分"，
而且规则实现可以单测、不烧 token、不因 mock provider 输出假结论。
LLM 只在"差距分析的自然语言解释"上做增强。

### 2.2 改造 4 个现有 Agent

| Agent | 改什么 |
|---|---|
| **Supervisor** | 意图从 4 类扩到 8 类：`learn / complete / career / jd / match / resume / interview / unknown` |
| **Career** | `ROLE_REQUIRED_SKILLS` 换成三梯队岗位；保留 gap 计算与稳定排序逻辑（这部分是对的） |
| **Research** | `TEMPLATES` 从 ACT/VLA/Isaac/ROS2 换成 A/B/C 级主题 |
| **Planner** | 新增 30 天路线模板（Week1-4）；支持接收 InterviewAgent 回写的学习任务 |

### 2.3 明确不动

`agents/core/`（BaseAgent / Executor / Registry）、`orchestrator`（失败隔离）、
`reviewer`（评分）、`knowledge`（RAG 检索）——框架层一个字都不改。

---

## 3. 数据模型（新增 6 张表）

```
JobPosting ──1:N──> JobMatch
    │ 1:N                                    ResumeFact（事实锚点库）
    └──> JobApplication（已有）                   ↑ 校验
                    │ 1:N                     ResumeVersion
                    └──> InterviewLog ──生成──> Task（学习任务）

InterviewQuestion（题库，独立）
```

| 表 | 关键字段 | 说明 |
|---|---|---|
| **JobPosting** | company, title, city, salary_range, jd_text, source, url, posted_at, tier(1/2/3), required_skills(JSON), education, min_years, paper_required, dedup_key, status | 岗位池，与投递记录分离：先看再投 |
| **JobMatch** | posting_id, match_score, grade(A/B/C/D), dimension_scores(JSON), gaps(JSON), updated_at | 匹配结果单独存，可重算、可对比 |
| **ResumeVersion** | name(LLM/VLM/FoundationModel/AIAlgorithm), content_md, target_tier, is_primary | 一岗一版，不虚构 |
| **ResumeFact** | category(work/project/paper/edu/metric), title, org, start, end, facts(JSON), source | **防虚构的锚点库** |
| **InterviewLog** | company, role, round, asked_questions(JSON), weak_questions(JSON), jd_gaps, knowledge_gaps, next_actions, interviewed_at | 面经 → 学习任务 |
| **InterviewQuestion** | category(LLM/Multimodal/Project/Coding), question, difficulty, answer_outline, source, hit_count | 支撑 Day26/27 的 50+30 题 |

### 3.1 匹配评分（严格按 v2.0 §22）

```
match_score = 技术栈 40% + 项目经验 25% + 学历/工作年限 15% + 科研/论文 10% + 行业匹配 10%
A ≥ 80 强匹配优先投 | B ≥ 65 正常投 | C ≥ 50 有缺口可练手 | D < 50 不推荐
```

技术栈维度用 `skill_profile` 的等级加权；项目经验用 ResumeFact 与 JD 关键词的命中；
学历/年限、论文、行业为规则常量（硕士在读 + 5 年 + EI 论文一作）。

---

## 4. 战略配置重排（批次 0 的具体内容）

### 4.1 三梯队岗位（`target_roles.py`）

| key | 岗位 | 定位 | 薪资 | 硬性技能 |
|---|---|---|---|---|
| `llm` | LLM / 大模型算法工程师 | **主攻** | 36–45K | Transformer, Attention, Pretraining, SFT, LoRA/QLoRA, PyTorch, Python |
| `vlm` | 多模态 / VLM 算法工程师 | **卡位**（差异化） | 36–45K | ViT, Multimodal Alignment, VLM, LoRA/QLoRA, PyTorch, Python |
| `ai-algo` | AI 算法 / 推理工程师 | **保底入口** | 30–40K | Python, Deep Learning, PyTorch, Inference Optimization, Linux |
| `embodied` | 具身智能 / VLA | **暂缓**（保留观察，不投时间） | — | 冻结，target = level |

### 4.2 技能画像分级（`skill_profile.py`）

- **A 级（30 天打穿）**：Transformer / Attention / MHA / RoPE / RMSNorm / SwiGLU /
  Pretraining / SFT / LoRA / QLoRA / KV Cache / Prefill·Decode / Quantization / FSDP·ZeRO / vLLM
- **B 级（必须理解）**：DPO / RLHF / MoE / FlashAttention / Gradient Checkpointing / Distributed Training
- **C 级（理解即可）**：ViT / CLIP / BLIP / LLaVA / Q-Former / Flamingo / Multimodal Alignment
- **D 级（冻结）**：ROS2 / VLA / Robot Learning / Isaac / Sim2Real / MoveIt2 / SO101
  → **`target_level` 设为等于 `level`**，看板 gap = 0，系统不会再推你去学

evidence 全部替换为可对外陈述的真实事实：
标书审核 Agent（覆盖率 56%→90%，30min→10min，3000+ 份）、
研发协同平台（30+ 人，交付周期 −200%）、STM-SHAP（EI 一作，NSE/RMSE +13%）、
科研知识库（Top-5 56%→78%，结构化召回 85%）、油耗 SaaS（MAPE<1%，1000+ 台）。

### 4.3 研究主题库（`research/templates.py`）

从 ACT / VLA / Isaac Lab / ROS2 → 换成：
`Transformer` / `SFT` / `LoRA-QLoRA` / `KV-Cache-Inference` / `VLM` 五个，
四类任务结构（paper / code / experiment / verification）保持不变，复用现有匹配逻辑。

---

## 5. API 设计（新增/扩展）

```
# 岗位池与匹配
POST   /api/job-postings                  录入/批量录入 JD
GET    /api/job-postings?tier=&grade=     岗位池（带匹配结果）
POST   /api/job-postings/{id}/match       计算并存储匹配（幂等，可重算）
GET    /api/job-postings/stats            梯队分布 + A/B/C/D 分布

# 简历线
GET    /api/resume                        简历版本列表
POST   /api/resume/parse                  简历 → 结构化画像
POST   /api/resume/diagnose?posting_id=   JD 定向诊断（含防虚构校验）
GET    /api/resume/facts                  事实锚点库

# 面试线
GET    /api/interviews                    面经列表
POST   /api/interviews                    记录面经
POST   /api/interviews/{id}/to-tasks      弱项 → 学习任务（回写 Planner）
GET    /api/interview-questions?category= 题库
POST   /api/interview/simulate            模拟面试出题 + 评分

# 现有
POST   /api/agent/run                     扩展 intent：jd / match / resume / interview
GET    /api/job-hunt                      现有聚合（增加 job_postings 摘要）
```

---

## 6. 前端（新增 2 页 + 1 处改造）

| 页面 | 内容 |
|---|---|
| `/jd`（新增） | 岗位池表格（梯队 / 匹配度 / 等级 / 差距）、JD 录入框、匹配详情抽屉 |
| `/interview`（新增） | 面经记录、弱项统计、题库练习、模拟面试入口 |
| `/jobs`（改造） | 投递记录关联 JobPosting，展示 JD 匹配度列 |

`/jobs` 是现有最贴近 P0 的资产，新设计围绕它扩展，不另起炉灶。

---

## 7. 自动化调度（复用 APScheduler）

现有调度器已有 morning / evening / comeback / github_sync 四个 job，直接加：

| Job | 时间 | 产出 | 模板 |
|---|---|---|---|
| `job_daily_report` | 每日 08:30 | 新推荐岗位 / 匹配理由 / 简历动作 / 面试题 / 学习任务 / 投递状态 / 今日优先 | v2.0 §23.1 |
| `job_weekly_report` | 每周一 09:00 | 投递统计 / 能力差距 / 项目进度 / 面试汇总 / 下周任务 / 博士积累 | v2.0 §23.2 |
| `job_followup_remind` | 每日 10:00 | `next_action` 到期的投递提醒 | 现有提醒通道 |

---

## 8. 约束内建（把规范写成代码，而不是靠记忆）

直接在配置与代码里固化 v2.0 §17/§28 的约束：

| 约束 | 落地方式 |
|---|---|
| 具身暂缓 | `skill_profile` 中 D 级技能 `target = level`（gap 恒为 0）；`TECH_BLACKLIST` 常量 |
| 不在主线深挖 D 级 | Planner 生成任务时命中 `TECH_BLACKLIST` → 拒绝并提示"当前 30 天不投入" |
| 简历不虚构 | ResumeAgent 输出的每条 claim 必须在 `ResumeFact` 有锚点，否则标红并列出依据 |
| 了解 ≠ 掌握 | skill level 只能由用户手动改，或由"通过验证"（测试/讲解/面试通过）提升；Agent 不得因"看过"提级 |
| 不每天换路线 | `TARGET_ROLES` / 技术选型锁（`1 LLM + 1 VLM + 1 训练 + 1 推理 + 1 项目`）变更需显式改配置 + git commit |
| 求职优先 | 任务冲突时按 `求职 > LLM 能力 > 项目 > 博士 > 具身` 排序 |
| 一个模块一次 | Codex 任务必须带 Definition of Done（v2.0 §25 的 9 项 checklist 模板化） |

---

## 9. 实施路线（按 P0 远近排序）

| 批次 | 内容 | 工作量 | 完成后你能做什么 |
|---|---|---|---|
| **0 ✅ 已完成** | 战略配置增量重排：target_roles / skill_profile / career rules / research templates + 前端类型适配 | 半天 | Agent 不再推错方向；看板匹配度反映真实目标 |
| **1 ✅ 已完成** | 岗位池 + JD 匹配：2 表（JobPosting/JobMatch）+ 纯规则匹配引擎 + 4 个 API + `/jd` 页 + 4 条种子样例 | 2–3 天 | 录 JD 即得 A/B/C/D 评级与差距，做到"找岗位不盲投" |
| **2 ✅ 已完成** | 简历线：ResumeVersion / ResumeFact + ResumeAgent + 防虚构校验 | 2–3 天 | 一岗一版简历，自动诊断，且不会写出假数据 |
| **3 ✅ 已完成** | 面试线：InterviewLog / InterviewQuestion + InterviewAgent + 回写任务 | 2–3 天 | 面经变学习任务，形成"面试→补知识"闭环 |
| **4 ✅ 已完成** | 日报 / 周报调度：报告引擎 + ReportLog 归档 + 3 个 APScheduler Job + `/reports` 页 | 1 天 | 每天 08:30 自动出报告 |

**最小可用 = 批次 0 + 1（约 3 天）**，就能覆盖 P0 里最缺的"找岗位、看 JD、反推能力"。
批次 2–4 可以边投边做——v2.0 也要求"不要等学习完成再开始投"。

---

## 10. 需要你确认的 4 件事

1. **战略转向是否确认**：把系统主线从具身切成 LLM/VLM（这会让 `/jobs` 看板的三赛道完全变样）
2. **批次 0 现在就做，还是先看完整路线再定**
3. **MatchAgent 是否接受纯规则版**（可解释、可单测、无 LLM 依赖）——我推荐纯规则起步
4. **简历事实锚点库**：是否把 v2.0 §3 的 5 个核心项目量化数据（56%→90%、+13%、56%→78%、MAPE<1%、1000+ 台）直接灌入 `ResumeFact`
