# 两份 Spec 的 Review（2026-09-18）

> 被审对象：`docs/superpowers/specs/2026-09-17-question-bank-expansion-design.md`、`docs/superpowers/specs/2026-09-17-tailwind-migration-design.md`
> 结论：**两份都不建议按原文直接执行。** 题库那份的执行物已经存在且跑不起来、且达不到它自己写的核心指标；Tailwind 那份的前提有 4 处与代码事实不符，按原文执行会做出一个不生效的配置文件。

## 摘要

| Spec | 结论 | 阻断项 | 建议 |
|---|---|---|---|
| 题库 110→150 | ⛔ 不可执行 | 4 项 | 修 1 处语法错 + 补 2 题 LLM + 规整 20 个技能名 + 重划分类；建议先只做「核心 12 题」 |
| Tailwind 迁移 | ⚠️ 前提错误 | 5 项 | 删掉"安装 + tailwind.config.ts"，改成"把 token 登记进 `@theme`"，补等价性判据 |

---

# 一、题库 110→150

## 1.1 先说好的（实测确认，不用改）

| 项 | 实测 |
|---|---|
| 缺口分析表的数字 | **完全准确**：LLM 48 / Multimodal 20 / Project 19 / Coding 23 = 110，与库中逐项一致 |
| 目标 150 与代码一致 | `QUESTION_CATEGORY_TARGETS` = LLM 50 + MM 30 + Project 40 + Coding 30 = 150 ✓ |
| 幂等实现 | `main()` 先取全表 `question` 集合再比对，写法正确；实测与库中 110 题**零完全重复** |
| 元字段 | `question_type="open"` / `is_verified=False` / `hit_count=0` 在 `main()` 里统一注入，不会漏 |

## 1.2 🔴 阻断项

### B1 · 执行物已存在，而且有语法错误，根本跑不起来

Spec 写「执行方式：**新建** `backend/scripts/seed_questions_v2.py`」。实际该文件**已存在**（377 行）——问题不是"新建"，是"修"：

```
文件：backend/scripts/seed_questions_v2.py
行 255："answer_outline": "1) 挑战：指代消解（"它"指什么）、话题切换……
实测：SyntaxError: invalid syntax (line 255)
```

中文引号用了 ASCII 双引号，字符串提前闭合。**整个模块无法 import，`python scripts/seed_questions_v2.py` 必然失败。**

改法：把 `（"它"指什么）` 改成全角引号 `（"它"指什么）`，或转义为 `\"`。全文件只有这 1 处真错（另 94 行含中文旁的引号但都是正常字符串边界）。

### B2 · 只写了 38 题，缺 LLM 的 2 题 → **核心必达指标达不到**

实测解析该脚本：`category` 取值分布 = **Multimodal 10 / Project 21 / Coding 7，LLM 0 题**。

| | 现状 | 跑完脚本（实测推算） | Spec 声称 |
|---|---|---|---|
| 总题数 | 110 | **148** | 150 |
| 核心（LLM+MM） | 68 | **78** | 80 |
| LLM | 48 / 50 | 48 / 50（缺口仍是 2） | 50 |
| Multimodal | 20 / 30 | 30 / 30 ✓ | 30 |

**关键**：`150` 是上界（计划 §十"每天 5 题 × 30 天"倒推），**`80` 核心必达才是有原文依据的硬指标**（计划 §八 Day26/27「50 LLM + 25~30 VLM」）。现在脚本连 80 都达不到，差的正是那 2 道 LLM 题。

改法：补 2 道 LLM 题（缺口表已列 LLM 缺口 = 2，但补充清单里没写这 2 题的内容，需要新增）。

### B3 · 20 个技能名不在 canonical 名单 → **覆盖率矩阵会被灌成一片红**

`coverage_matrix()` 的行 = 主攻赛道 `required_skills`（8 个）**∪ 题库里出现过的 skill_name**（代码注释明写"会自动补到行尾"）。每个技能 4 个格子，红格 = 某 (技能, 分类) 为 0。

实测投影：

| | 现状 | 补入后 | 变化 |
|---|---|---|---|
| 矩阵行数 | 8 | **36** | +28 |
| 格子总数 | 32 | **144** | +112 |
| 已填格子 | 12 | 44 | +32 |
| **红格数** | **20（62%）** | **100（69%）** | **+80 红格** |

新增的 28 行里，**20 个不在 `SKILL_PROFILE` 的 49 个 canonical 技能名单中**：

```
A/B 测试、Agent、OCR、Prompt Engineering、分布式训练、图文检索、多模态 Agent、
多模态对齐、多轮对话、安全对齐、幻觉检测、推理优化、数据工程、模型监控、
视觉编码器、视频理解、评估体系、评估指标、部署优化、长上下文
```

其中 **3 个有现成的 canonical 英文名**，只是写成了中文（这正是记忆里记过的坑：画像技能名用英文、JD/题库容易写中文）：

| 脚本里 | 应改为 |
|---|---|
| 多模态对齐 | `Multimodal Alignment` |
| 推理优化 | `Inference Optimization` |
| 分布式训练 | `Distributed Training`（或 `FSDP/ZeRO`） |

剩下 **17 个是真新概念**（OCR / 图文检索 / 视频理解 / 数据工程 / 评估体系 / 评估指标 / 模型监控 / A/B 测试 / 安全对齐 / 幻觉检测 / 长上下文 / 多轮对话 / 部署优化 / 视觉编码器 / 多模态 Agent / Agent / Prompt Engineering）——需要你决定走哪条路：

- **A**：补进 `skill_profile.py`（题库与能力画像打通，但这些技能对现有 3 条赛道没有 required_level，会新增一批 gap）
- **B**：改挂已有技能（如 多模态 Agent → `Agent Application`、视觉编码器 → `ViT`、长上下文 → `RoPE`/`Transformer`）——不新增行，但语义略粗

**Spec 自己写了 `skill_name`：关联技能（canonical name），实际没遵守。**

**后果**：P3 的验收标准是「Day 26 时看到的是"缺口在哪"而不是"从零开始"」。红格从 20 → 100，其中 80 个是**词表不统一造成的假缺口**，不是真实面试缺口。这会把"缺口在哪"这个信号淹掉——**等于反向实现验收标准**。

### B4 · Project 分类灌水，且灌的是一个"无原文依据"的目标

Project 的 21 题里，至少 10 题是 **LLM 理论题**，不是项目/工程题：

```
MoE 架构与路由策略 / DPO 原理与实现 / 安全对齐 RLHF-DPO / 分布式训练 FSDP-ZeRO /
推理优化 量化剪枝蒸馏 / 幻觉检测与缓解 / 长上下文处理 / 多轮对话管理 /
模型监控与可观测性 / A-B 测试与灰度发布
```

这带来两层问题：

1. **LLM 分类仍然虚低**：真实的 LLM 理论缺口被藏进了 Project，LLM 只 +2（48→50）看起来"快达标了"，实际是把该记在 LLM 名下的 10 题挪走了。
2. **Project 40 这个目标本身无原文依据**。`engine.py` 的注释和 P3 实施记录（`platform-direction-30day.md` §14.6）都自认：**LLM 50 / Multimodal 30 有原文依据，Project 40 / Coding 30 是"为补满 150 倒推的"**。为一个倒推出来的目标灌 21 题，性价比最低。

改法：MoE / DPO / RLHF / 分布式 / 推理优化 / 幻觉 / 长上下文 / 多轮对话 / 监控 / A-B 归 **LLM**；Project 只留真正的工程实践题（RAG 架构 / RAG 检索 / RAG 评估 / Agent 架构 / 工具调用 / Prompt Engineering / 注入防御 / 评估体系 / 数据清洗 / 数据飞轮 / 部署选型）。

## 1.3 ⚠️ 建议补充

| # | 缺失 | 建议 |
|---|---|---|
| S1 | **没有验收标准** | 跑完 `/api/interview-questions/coverage`：`core_done == 80`、`Multimodal == 30`；重跑脚本 `新增 0 / 跳过 N`；开发库 `interview_questions` 110 → 148（或 150），基线白名单同步更新 |
| S2 | **没有 `--dry-run`** | 项目既有惯例（`seed_plan_30d.py` 有）。先打印"将新增 N 题 + 分类分布"不落库，核对无误再真跑 |
| S3 | **没有 `--revert`** | 40/38 题一次性进库，写错了没法撤。按 `source='seed_v2'` 删除即可回滚 |
| S4 | **没有备份步骤** | 写入前 `cp backend/data/app.db backend/data/app.db.bak-20260918` |

## 1.4 ✅ 我建议的执行方式（改后）

```
第一批（现在，≈12 题）—— 目标：core 80/80 必达
  LLM +2        补上缺口表里缺的那 2 题
  Multimodal +10
  → 验收：core_done=80、Multimodal 30/30

第二批（offer 落定后，≈28 题）—— 目标：上界 150
  Project（重划分类后）+Coding
  → 前置：先决定 17 个新技能的归属（补 skill_profile 还是改挂已有技能）
```

理由：在 offer 倒计时 43 天、离职 6 天的窗口里，**第一批能达成计划原文的硬指标（80 核心）**，第二批只是追一个倒推出来的上界。省下的时间给面试自测更值。

## 1.5 顺带一个产品观察（不阻断）

现在 `is_verified` 全库 110 题**全为 0**，`hit_count` 也基本未被使用过。也就是说题库是"库存"而不是"训练集"——**110 道题从没被闭卷答过一遍**。加 38 道新题只会让库存更大。

计划 Day 21/26 的"面试验收"才是题库的真实用途：**用现有 110 题闭卷自测，把答不出来的标出来**。如果这个环节没做，题库从 110 补到 150 对 offer 概率的边际贡献接近 0。

---

# 二、Tailwind CSS 迁移

## 2.1 前提核对（5 条，4 条与代码事实不符）

| Spec 声称 | 实测 | 判定 |
|---|---|---|
| 「步骤 1：`npm install -D tailwindcss @tailwindcss/postcss`」 | `frontend/package.json` devDeps 已有 `tailwindcss: ^4` + `@tailwindcss/postcss: ^4`；`postcss.config.mjs` 已配好 | ❌ 已完成，多余 |
| 「步骤 2：globals.css 注入 `@import "tailwindcss"`」 | `globals.css` 第 1 行就是这个 | ❌ 已完成 |
| 「新建 `tailwind.config.ts` 映射变量到主题」 | 仓库无任何 `tailwind.config.*`；项目是 **Tailwind v4（CSS-first）**，主题定义在 CSS 的 `@theme` 块里 | ❌ **v3 写法，会做出不生效的配置** |
| 「无设计系统」 | `globals.css` 已有 **67 个 CSS 变量** + 一个 `@theme inline` 块 | ❌ 不成立 |
| 「暗色模式部分支持（`[data-theme="dark"]`）」 | 全仓库 **搜不到 `data-theme`**；实际是 `@media (prefers-color-scheme: dark)` 覆盖 `:root` | ❌ 假的 |

**真正缺的是什么**：`@theme` 里目前只登记了 4 个变量（`--color-background` / `--color-foreground` / `--font-sans` / `--font-mono`）。Tailwind v4 只有 `@theme` 里登记过的变量才会生成工具类。所以：

```
实测：bg-card / text-ink / rounded-card / border-hairline 等 token 工具类
     在当前配置下无法生成（全仓库使用次数 = 0）
同时：flex / text-sm 这类默认工具类可用（Tailwind 确实在跑）
inline style：59 个文件 / 933 处
```

→ **迁移的真实工作只有一件事：把 67 个 token 登记进 `@theme`**，让 `bg-card` 这类类名真正存在。不是"引入 Tailwind"。

## 2.2 🔴 映射表里 3 处不成立

| Spec 表里的写法 | 问题 | 修正 |
|---|---|---|
| `bg-page` ← `--color-page` | **该变量不存在**（实测 67 个变量里没有），实际叫 `--color-canvas` | 改成 `bg-canvas` ← `--color-canvas` |
| `rounded-card` ← `--radius-card-lg` | v4 的 `--radius-*` 命名空间下，`--radius-card-lg` 生成的是 **`rounded-card-lg`**，不是 `rounded-card` | 二选一：①用 `rounded-card-lg`（0 处改动）②把变量改名 `--radius-card`（要改 **37 处** `var(--radius-card-lg)` 引用） |
| （漏了）排版 token | `--font-size-hero/title/body/caption/micro` **不在 v4 命名空间**（v4 是 `--text-*`），`text-hero` 不会生成 | 要么改名 `--text-*`，要么放弃（实测 `--font-size-body` 被引用 **0 次**、`--font-size-hero` **1 次** → 价值极低，建议放弃） |

其余行是对的：`bg-card` / `text-ink` / `text-ink-80` / `text-ink-48` / `border-hairline` / `text-primary` / `bg-emerald` / `bg-amber` / `bg-rose` / `rounded-pill`（`--radius-pill` 生成 `rounded-pill` ✓）。

表里漏了 `--radius-item-md`（被引用 42 次）和 `--radius-item-sm`（20 次）。

**改名成本参考**（inline 里被引用的变量共 33 个、1202 次）：

```
--color-ink-48      232 次      --radius-pill       104 次
--color-ink         105 次      --radius-item-md     42 次
--color-primary      81 次      --radius-card-lg     37 次
--color-card         58 次      --color-zinc-100     36 次
--color-canvas       24 次      --radius-item-sm     20 次
```

→ **结论：不要为了少打几个字符去改名**。保持 `--radius-card-lg` / `--radius-item-md`，接受 `rounded-card-lg` 这种类名。改名省下的是打字，付出的是 99 处引用的回归风险。

## 2.3 🟠 缺了一条关键规则：token 等价性判据

Spec 写「迁移时不改功能，只改样式写法」。但**样式写法一变，颜色就会变**——因为项目里有 29 个文件、81 个硬编码色值，其中一部分与 token 并不相等。实测例子：

| 组件 | 硬编码值 | 对应 token | 判定 |
|---|---|---|---|
| TodayBoard | `#FAFAFB` | `--color-item-bg` = `#FAFAFB` | ✅ 精确相等，可安全替换 |
| TodayBoard | `#FEF2F2` | `--color-rose-soft` = `#FEF2F2` | ✅ 精确相等 |
| TodayBoard | `#FFFFFF` | `--color-card` = `#FFFFFF` | ✅ 精确相等 |
| TodayBoard | **`#F5F5F5`** | `--color-zinc-100` = **`#F4F4F5`** | ❌ **不相等，替换即静默改色** |
| GlobalNav | `#000000` | **无对应 token** | ❌ 需新增 token 或保留 |

**必须补的规则**：每个硬编码色值落库前先分类——

```
① token 缺失（如导航黑 #000000）      → 新增 token，写进 @theme
② 与某 token 近似但不等（#F5F5F5）    → 逐个人工确认：统一到 token 还是保留
③ 有意的局部差异                      → 保留 inline，加注释说明为什么不用 token
```

没有这条规则，"迁移"就会变成"静默改视觉"，且没有任何测试能发现。

## 2.4 🟠 迁移顺序与验收

Spec 的顺序是 QuestionBoard → TodayBoard → Dashboard → JobsBoard，理由是"改动频繁"。但体量恰好相反：**最大的（JobsBoard 996 行 / TodayBoard 605 / QuestionBoard 511）留到最后**，等于把方案能否在复杂组件上成立这件事推迟到收尾才验证。

建议：

```
第 0 步  一个中等组件端到端试点（建议 ReportsBoard 424 行）
         含：登记 token → 改 className → tsc → eslint → next build → 视觉比对
第 1 步  试点通过后再批量，按体量从小到大
```

**Spec 缺验收标准，建议补**：

- `@theme` 登记后，`bg-card` / `text-ink-48` / `rounded-card-lg` 等类名**实际生成**（build 产物里能查到）
- 试点组件 inline style 数归零
- `node node_modules/typescript/bin/tsc --noEmit` 0 错、`next build` 通过
- **视觉无变化**：试点组件迁移前后截图比对
- 暗色模式仍生效（`@theme` 会把变量输出到 `:root`，与既有 `@media (prefers-color-scheme: dark)` 覆盖的先后顺序**需实测确认**，这是本次唯一有真实风险的技术点）

## 2.5 Spec 里"不做的事"要补一条

原清单（不引 Shadcn / 不引 Tailwind UI / 不一次迁完 / 不改功能逻辑）都对。**建议补上最重要的一条**：

> 不做任何产品行为改动 —— 本次是纯样式重构，不新增、不删除、不移动任何界面元素。

---

# 三、优先级（PM 视角，必须说）

这两件事**都不解决 09-17 诊断出的问题**：

| 09-17 诊断的 P0 | 本轮的两份 Spec |
|---|---|
| JD#5 面试 09-14 结束未回写（已超 72h） | 无关 |
| `/today` 不回答 PRD F2 的问题 | 无关 |
| 课程窗口盖住黄金投递期（重叠 16 天） | 无关 |

- **Tailwind 迁移**：纯技术债，唯一收益是"以后改样式快一点"。**不产生任何用户可见变化。**
- **题库补题**：在 offer 倒计时 43 天里，把库存从 110 加到 148，**不产生任何 offer 概率增量**——除非配合"闭卷自测"这个真正用题的动作。

不建议取消，但建议明确标注：**这两件事是"可与求职并行、但不得挤占面试/投递时间"的副线**。若时间冲突，先做 1.4 的题库第一批（12 题，能达成 80 核心硬指标），Tailwind 整体后移到 offer 落定。

---

# 四、需要你拍板

| # | 事项 | 选项 |
|---|---|---|
| 1 | 题库第一批范围 | A. 只做核心 12 题（LLM+2 / MM+10），Project/Coding 后移（**推荐**）<br>B. 一次做完 40 题 |
| 2 | 17 个新技能名 | A. 补进 `skill_profile.py`（题库与能力画像打通）<br>B. 改挂已有技能（不新增矩阵行） |
| 3 | Project 分类里的 10 题 LLM 理论题 | A. 归 LLM（**推荐**）<br>B. 维持 Project |
| 4 | `rounded-card` 类名 | A. 接受 `rounded-card-lg`，不改名（**推荐**）<br>B. 改名 `--radius-card`，改 37 处引用 |
| 5 | Tailwind 迁移时机 | A. offer 落定后（**推荐**）<br>B. 本周并行做试点 |

拍板后我可以直接动手：修 B1 的语法错、补 B2 的 2 题、按决定规整技能名与分类、给执行脚本加 `--dry-run`/`--revert`/备份，Tailwind 那边把 67 个 token 登记进 `@theme` 并做试点组件。
