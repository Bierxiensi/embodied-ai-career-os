# 掌握单元双环设计（Mastery Unit Dual-Loop）

> 2026-09-24 · 基于 brainstorming 产出 · 产品收敛重定位为「阶段制单主线 + 掌握单元双环」，打通 **学 → 做 → 考 → 证** 全链闭环
> 前身：`PRD_CAREER_OS_MODES.md`（阶段模式思想的收紧版）、`路线调整-Post-Training-v3.0.md`（主轴口径不变）
> 调研依据：`OPEN_SOURCE_REFERENCE_ANALYSIS.md`（09-16）、`相似项目调研与借鉴清单-2026-09-24.md`（54 候选 / 12 仓深读）

---

## 一、背景与决策记录

### 1.1 为什么重规划（三条实测诊断）

1. **输入形状不对**：64 个写端点绝大多数是「登记式」（建档/勾选），唯一每日入口（今日施工单）写的是布尔状态（`day_artifacts=0`、`day_progress=0`、`experiments=0`，从未被真实使用）——记录的是"勾没勾"，不是"学到了什么"。
2. **成长式能力全在死链上**：L1-L4 证据门、reviewer 证据评分、GitHub 建议确认、日报复盘——最像"伴随成长"的机制全部不可达或零消费（`is_verified` 全库 0、L2+ 证据 0 条）。
3. **四线并行与 1-2 小时/天严重失配**：求职/学习/学术/具身四条线 11 个导航入口，无主次、无容量约束、无停止规则；文档口径三方打架（三问/北极星/时间预算各有多套版本）。

**结论**：主战场是**接通与收窄**，不是新建。

### 1.2 已锁定决策（brainstorming 逐项确认）

| # | 决策项 | 结论 |
|---|--------|------|
| D1 | 重规划幅度 | **收敛重定位**：敢砍敢合，匹配每天 1-2 小时 |
| D2 | 主线结构 | **阶段制，每期只开一线**：当前=`post_training_growth`；`phd_application`（26 秋）、`job_hunt`（未来窗口）归档 |
| D3 | 成功标准 | **四个信号全要**：每天用得动 · 差距可量化 · 作品集说话 · 考得住 |
| D4 | 产品形态 | **掌握单元双环**：学/考在系统内闭环，重动手在系统外、证据回流 |
| D5 | 收口力度 | 登记式端点**撤 UI 留数据**（标 deprecated，不删库） |
| D6 | 复习调度 | **简化 SM-2 起步**（4 档评分），FSRS-6 后置增强 |
| D7 | Agent 编排 | **4 日常（supervisor/planner/knowledge/reviewer）+ 2 按需（research/career）** |

---

## 二、产品定义

### 2.1 北极星（当前阶段 · Post-Training 成长线）

> 在每天 ≤2 小时的容量约束内，把 Post-Training 能力（SFT→LoRA→DPO→GRPO）用**证据**做实——从"学过"推到"考得出、拿得出"，为申请季与下一次岗位窗口储备可验证的能力证明。

### 2.2 产品三问合同

| 三问 | 出口 | 可验收定义 |
|------|------|-----------|
| ① 距目标能力还差什么 | `/progress` | 六域雷达 + 逐技能 L 级 + 差距 Top5，**每条主张可点开证据** |
| ② 今天学/复习什么 | `/learn` `/review` | 1 个关键学习单元 + 10-15 分钟复习队列，容量预检兜底 |
| ③ 能力是否真提升 | 证据门晋级 | L1→L4 逐级变绿 + `is_verified` 变绿 + 测验正确率/记忆率曲线 |

### 2.3 四信号硬指标（"成了"的验收线）

| 信号 | 硬指标 |
|------|--------|
| 每天用得动 | 连续 **14 个日历日**完成「领任务→学/复习→留下实质记录」；OS 内操作体验目标 ≤15 分钟/天（E2E 代理指标：单日完整流点击 **≤25 步且无死路**）；计划生成前容量预检不满足即拒绝 |
| 差距可量化 | 任意时刻 `/progress` 能输出「本周补了哪块」；证据缺口自动转成明日施工单项 |
| 作品集说话 | Mini Post-Training Lab 的 **01_sft / 02_lora / 03_dpo** 三单元各产出 ≥1 条 L2+ 证据；packaging 一键组装 13 节 README 非空；简历 skill-lines 只收 gate≥1 |
| 考得住 | 核心题库（30 天脊梁面试题主题对应）`is_verified` 覆盖率 **30 天内 ≥50%** 且计数**单调不减**；掌握单元测验正确率与 SM-2 记忆曲线有记录 |

**`is_verified` 统一语义**（消除既有歧义）：表示「该考点已被用户闭卷实证掌握」——闭卷答对一次即置位。`interview_questions` 与 `unit_items.quiz` 共用该语义；不是题目质量验收标记。

### 2.4 阶段制

- 同一时刻只有一个 active stage。当前 `post_training_growth`；`phd_application`、`job_hunt` 为 archived：**数据保留、入口收敛进「阶段」设置页、切换需确认**（沿用 PRD modes 的"切换不删历史数据"）。
- **SO101 特殊定位**：不是阶段，是「证据工厂」——MISTAKES / baseline 改造记录随时可回流证据库（L2/L3），**永不占今日单**。
- **容量预算是产品级硬约束**：每日学习 60-120 分钟可配 + OS 操作体验 ≤15 分钟；任何计划/任务生成前 `assert_plan_capacity` 式预检，超限**显式拒绝**并给最短可行周期。

（产品名沿用 Embodied AI Career OS，不改名。）

---

## 三、信息架构与每日使用流

### 3.1 导航收敛：11 入口 → 三问三入口

| 入口 | 回答 | 承载 |
|------|------|------|
| `/learn` | 今天学什么 | 今日学习单（施工单+单元+欠账）+ 掌握单元视图 + 「生成任务」入口（从 /agents 迁回） |
| `/review` | 复习什么 | SM-2 复习队列 + 错题集 + Teach-Back 历史/每日复盘 |
| `/progress` | 能力真提升吗 | 六域雷达 + 证据门 L 级 + 差距 Top5 + 作品集组装入口 |

降级处置：

- **CommandPalette**（组件已建未接线）：接线，承载全部低频功能（项目/实验/简历/面试/博士/设置…）。
- **「阶段」设置页**：收纳归档线（phd/job_hunt）入口与切换确认。
- **`/knowledge`**：撤销一级入口，降为掌握单元内「问」入口（就地检索/提问，API 与页面组件保留）。
- **Mini Lab / 项目 / 实验**：挂 `/progress` 证据流下，不再独立一级入口。
- Sidebar 缺 `/today` 条目的 IA bug 随本次收敛一并修复（`/today` 并入 `/learn` 后退役为 redirect）。

### 3.2 每日使用流（OS 操作 ≤15 分钟）

```
开 /learn → 今日唯一关键单元（默认 1 个，可手动加副单元）+ 待复习 N 卡 + 昨日欠账
   ↓
学单元：摘要 / 概念卡 →（不懂就地「问」知识库）→ 测验 3-5 题
   ↓
Teach-Back：教练发起 3 题口述 → 判定 → 自动写 LearningLog（content=口述反思）+ 卡片入 SM-2 队列
   ↓
动手做（系统外，如 Mini Lab）→ commit 自动同步 → 半确认落为 L2 证据
   ↓
收工：「完成」判据 = 测验过 / Teach-Back 过 / 证据挂上（三选一，不再是布尔勾选）
```

### 3.3 掌握单元（核心组件）——学/考/证的最小闭环

- **定义**：一个单元 = 一篇论文的一个主题 / 一个技能点 / 一讲讲义 / 一个 Mini Lab 模块。
- **内容包**（Skill-Anything 裁剪版）：摘要 · 概念卡 · 测验 3-5 题 · 思考题 1-2 · 派生复习卡。
- **来源**：10 篇 Post-Training 论文（已有语料）+ RESOURCE_LOCK 8 类 + 带你学讲义（3 课起）+ Mini Lab 7 模块。
- **生成**（FreeLingo 式）：30 天脊梁确定性铺单元网格 → **打开才懒生成**内容 → sha256 缓存 → 无 LLM 时降级规则模板并标注 `generation_mode`。
- **两级模型路由**：MiMo flash（默认）生成卡片/题目/Teach-Back 判定；mimo-v2.6-pro（可配）做摘要 reduce 与 reviewer 深评；处处 rule 兜底 + 降级可见徽标。

### 3.4 前端组件增删

| 动作 | 组件 |
|------|------|
| 新增 | `UnitView`（单元学习视图）、`ReviewQueue`（SM-2 卡片队列）、`ProgressBoard`（雷达+证据门+差距） |
| 改造 | `TodayBoard`→`LearnBoard`（完成判据换实质三选一）；`TaskCompleteForm`（死组件）复活为 Teach-Back/回收表单；`ReportsBoard` 并入 `/review` 作每日复盘 |
| 接线 | `CommandPalette`（全局快捷键） |
| 删除/退役 | 死组件子树其余部分、redirect 壳（随实施步骤清理） |

---

## 四、架构与数据模型

### 4.1 新数据模型（3 新 + 2 改）

**`mastery_units`（新）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | PK | |
| source_type | enum | paper / resource / lecture / lab |
| source_ref | str | 论文 id / 资源名 / 讲义路径 / Lab 模块名 |
| title | str | |
| skill_ids | JSON | 关联技能（对接 skill_profile 六域） |
| day_seq | int? | 对齐 30 天脊梁（可空=脊梁外单元） |
| generation_mode | enum | llm / rule（生成降级可见） |
| content_hash | str | sha256 缓存键 |
| status | enum | locked / ready / opened |

**`unit_items`（新）**

| 字段 | 类型 | 说明 |
|------|------|------|
| unit_id | FK | |
| kind | enum | summary / concept_card / quiz_q / exercise / flashcard |
| body | Text | |
| answer + rationale | Text? | quiz_q/exercise 用 |
| is_verified | bool | 统一语义：用户闭卷实证掌握（见 §2.3） |
| verified_at | datetime? | aware UTC |

**`review_cards` + `review_logs`（新，简化 SM-2）**

- card：`source`（concept_card 派生 / 错题 / Teach-Back 错项）、`due_at`、`interval_days`（初始 1 天）、`ef`（初值 2.5，clamp [1.3, 2.5]）、`lapse_count`、`card_status`（active / fixed）。
- 评分 4 档：again / hard / good / easy；标准 SM-2 公式更新 interval 与 EF；连续 2 次 good+ 置 `card_status=fixed`（默认不再排入，除非 lapse）。
- ⚠️ `card_status` 与 §2.3 的 `is_verified` **不是一回事**：前者是调度状态，后者是「闭卷实证掌握」的能力标记（挂在 `unit_items` / `interview_questions` 上）。
- review_logs：`rating`、`reviewed_at`、`duration_seconds`。

**`learning_logs`（改）**：+ `unit_id` / `session_id` 关联；Teach-Back 与测验反思**自动**落此表，`content`=用户口述/反思原文（AI 只起草转写，不改写事实）。

**`skill_assessments`（改）**：晋级申请事件来源扩展——测验过 / Teach-Back 过 / 证据挂上自动发起；`reviewer` 只读契约化输出建议，apply 由独立 apply 层执行（见 §4.3）。

### 4.2 intake 收口：64 个写端点 → 三类入口形状

1. **学习回收**（全自动）：Teach-Back / 测验 → 自动写 `learning_logs` + `review_cards`——最好的记录是自动生成的。
2. **半自动事实**（Proposal 确认）：commit 同步 → 预填证据草稿 → 一键确认落 L2；capture-first，**schema 级禁止 AI 直写事实**（AI 只产草稿，append-only 由确认动作触发）。
3. **主动登记**（收敛为一个 intake 组件）：experiments / 手写日志保留，统一走一个表单入口。

其余登记式端点**标 deprecated、保数据、撤 UI**（D5）。活跃写端点目标：**64 → ≤25**（写进 STYLE.md 不变量）。

### 4.3 编排层收窄（D7）

- 日常链：`supervisor`（意图分类 + **停止规则**：一次会话只激活一个主 Agent、decision-ready 即停、研究检索"信息开始重复即停"）→ `planner` / `knowledge` / `reviewer`。
- 按需：`research` / `career`（on-demand，不进每日流；差距职能由纯函数 readiness + career_roi 常驻 `/progress`）。
- **Y9 修复**：`user_input` 真正透传子 agent + 意图→参数提取（topic/时长/技能），替换 `_resolve_input()` 硬编码占位。
- **Y10**：planner 默认保留 `rule`，前端加显式「AI 生成」开关（生成耗时 5-10s，不进主链路）。
- 3 处过时人设 prompt（llm_generator「Robot AI Engineer/SO101」、reviewer「具身智能学习导师」、career「机器人行业猎头」）全部换 Post-Training v3.0 口径。
- `reviewer` **只读 + fail-closed**：输出契约 JSON 并显式校验，非法输出标 block 重试（不静默降分、不吞异常）；**不得成为第二写入方**，晋级写库由 apply 层执行。

### 4.4 后端聚合端点

新增 `GET /api/today`：施工单 + 今日单元 + 复习队列 + 欠账一次返回；容量预检前置；各分区独立兜底（一区挂不致全挂）。前端从拼 5 端点变 1 个，状态编排上收后端。

### 4.5 数据流（闭环全景）

```
30天脊梁(确定性网格) → unit 网格 → 打开懒生成(llm|rule, sha256缓存, 降级可见)
                                ↓
              学 / 测 / Teach-Back → unit_items.is_verified ↑ · review_cards 入队 · learning_logs(自动)
                                ↓
        证据事件(测验/commit/实验) → evidence_gate L1→L4 晋级 → skill_assessments(契约化 apply)
                                ↓
              /progress 雷达·差距 Top5 → 缺口生成明日施工单项 ──闭环回 ②
commit 同步(窄事件流, 先修通 .github_last_sync 水位) ──半确认──→ L2 证据 ↗
```

### 4.6 减法清单

| 对象 | 处置 |
|------|------|
| 零消费端点（GET /api/dashboard、tools/prompt+context、career-mode/transitions、paper/compare 等） | 标 deprecated；paper/compare 本期不挂新 UI（论文对比需求由单元内「问」入口覆盖） |
| 死组件/死 service（githubService 零 import 等前端约 1/3 死代码） | 三死链先接通（reviewer 确认流、GitHub 建议确认、复盘），其余进删除清单 |
| redirect 壳（dashboard/reports/evidence/experiments） | 随实施清理 |
| 测试专用端点（PATCH /skills/{id} 等） | 移出公开 API 或显式标注 |

---

## 五、质量设计

### 5.1 错误处理与降级可见

| 风险 | 处置 |
|------|------|
| LLM 不可用/超时 | 处处 rule 兜底 + 降级可见徽标（`generation_mode`/`answer_mode` 同款） |
| 懒生成失败 | 单元骨架 + 重试 + 规则模板兜底，不阻塞今日单渲染 |
| 容量超限 | 显式拒绝生成 + 给最短可行周期（禁止静默截断） |
| LLM 输出非法 | 契约 JSON 校验 fail-closed：block 重试，不静默降分、不吞异常 |
| 静默退化（hash 嵌入 / provider 退 mock） | 界面告警（/knowledge 先例）+ 复核探针并入 `scripts/smoke.sh` 检查项（沿用 verify_xiaomi.py 手法） |
| 时间戳 | 新表一律 aware UTC；读路径统一 normalizeUtc |
| 聚合端点分区失败 | 各区独立 `.catch` 兜底 |

### 5.2 测试门禁

1. **pytest 基线 437 passed / 2 skipped 不降**，新增以下用例组：单元生成/降级/缓存、SM-2 调度（due/EF/lapse/fixed 晋升）、Teach-Back 自动落库契约、evidence_gate 晋级触发、reviewer 只读契约 fail-closed（含**不写库断言**）、容量预检拒绝、意图门控查询零写入、Y9 透传回归。
2. **前端**：tsc/eslint RC0 + 既有「编译 service 吃真 HTTP」冒烟手法覆盖今日流渲染、懒生成、Teach-Back 表单、复习评分。
3. **四信号 E2E**（可复跑脚本，直接当验收单）：
   - *用得动*：模拟 14 天日流 → 单日完整流点击 ≤25 步且无死路；
   - *量化*：`/progress` 响应含雷达 + 差距 Top5 + 每条主张带 evidence 引用；
   - *作品集*：01_sft/02_lora/03_dpo 三单元产物 → packaging 组装 → 13 节 README 非空；
   - *考得住*：`is_verified` 计数单调不减 + 正确率与 SM-2 曲线有记录。
4. **数据纪律**：fixture 全合成；写路径用副本库 + 指纹比对；测试永不写开发库。

### 5.3 STYLE.md 不变量（加模块前的对照门槛）

- SQLite 单文件；不新增平行权威域（core/ 纯函数层是策略单一真源）。
- 加端点前先问「能否并入三类 intake」；活跃写端点 ≤25 且总数不增反减。
- 拒绝线清单成文：自动投递/爬虫、Gmail 全量授权、AGPL 代码复制、横向膨胀（不加第五条线）、未经人审的 AI 直写事实。
- specs/*.instructions.md 绑代码路径（frontmatter applyTo），改前先读，防 AI 改码漂移。

---

## 六、开工前置裁决（第 0 步，零代码）

| # | 裁决项 | 建议 | 影响 |
|---|--------|------|------|
| 1 | X4 六维匹配 timeline 缺奖励（`_timeline_score(None)` 恒 70） | 改为按截止日/窗口距今计分（进实施步骤 1） | 博士匹配排序失真 |
| 2 | 北航本校去留 | 保留但降权（申请季前最终裁决） | 博士看板口径 |
| 3 | Y7：learning_logs 14 条演示数据 | 清（先备份，同 job_applications 先例） | 新卡片/统计口径 |
| 4 | 三问口径单一真源 | 以本 spec §2.2 为准，旧文档标注 superseded | 防口径漂移 |
| 5 | 时间预算口径 | 每日学习 **60-120 分钟可配** + OS ≤15 分钟，容量预检用此口径 | 计划生成硬约束 |

---

## 七、实施顺序（6 步，每步可独立验收）

| 步 | 内容 | 验收 |
|----|------|------|
| 0 | 前置裁决落地（§六）+ 文档口径收口 | 零代码，裁决记录在案 |
| 1 | 减法清理：死链/死组件/redirect、3 处 prompt、Y9/Y10、X4 计分 | 活跃写端点 ≤25；pytest 不降 |
| 2 | 三入口 + `GET /api/today` 聚合 + CommandPalette 接线 | 每日流走通（旧数据形态） |
| 3 | 掌握单元：schema + 懒生成 + 缓存 + 降级 + `/learn` 单元视图 | 30 天脊梁铺满单元网格，打开才生成 |
| 4 | Teach-Back 回收 + 简化 SM-2 + `/review` | 自动落 learning_logs；复习队列可排 |
| 5 | 证据晋级闭环 + 作品集组装 + `/progress` | 四信号 E2E 全绿 |

每步拆包进入 writing-plans 产出实施计划（建议步 1-2 一份、步 3-4 一份、步 5 一份）。

---

## 八、范围外（明确不做）

1. 自动投递 / 爬虫 / 反指纹 / Gmail 全量 OAuth（只做用户主动粘贴/转发的窄 intake）。
2. 未经人审的 AI 直写事实；不可解释的多 Agent 自动决策。
3. 第五条线（习惯/财务/泛知识等横向膨胀）。
4. AGPL/GPLv3 对标项目代码复制；不 fork、不绑上游。
5. 阶段切换到 `job_hunt` 的求职执行细节（本期只建切换机制与归档收纳）。
6. SO101 的日常化（保持证据工厂定位，不占今日单）。

---

## 九、附录：借鉴机制映射（精简）

| 机制 | 来源 | 落点 |
|------|------|------|
| 三命令对三问 | Learn FASTER | §3.1 三入口 |
| Teach-Back 主动回收 | Learn FASTER | §3.2/§4.1 学习回收 intake |
| 资料→掌握单元 | Skill-Anything | §3.3/§4.1 mastery_units |
| /today 单端点 + 容量预检 + 懒生成 | FreeLingo | §2.4/§4.4 |
| capture-first + Proposal 确认 | Northstar / Friend-Xu | §4.2 半自动事实 |
| 停止规则 + 意图门控 | sean2077 / Pluto-Mo | §4.3 supervisor |
| reviewer 只读 fail-closed | sean2077 / JSE | §4.3 |
| 间隔重复 | Northstar（SM-2 简化起步） | §4.1 review_cards |
| 事件流自动记录（窄版） | jobseeker-analytics | §4.2 commit 同步 |
| STYLE.md 不变量 | notiapply | §5.3 |
