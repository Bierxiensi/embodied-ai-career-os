# 系统审计：脏数据 · 概览口径 · 双角色切换

> 审计日期：2026-09-10 · 审计对象：Embodied AI Career OS（backend + frontend，开发库 `backend/data/app.db`）
> 证据来源：直连 SQLite 统计 + 各页面 SSR 渲染文本提取 + 代码走查

---

## 一、结论先行

你提的三件事，本质是**三个独立问题**，严重度递减、但根因同源：

| # | 你的观察 | 实际情况 | 严重度 |
|---|---|---|---|
| 1 | 前端有很多脏数据 | **确认，且相当严重**：214 个项目里只有 2 个是真的；292 个任务里大量重复（单个任务重复 29 次） | 🔴 P0 |
| 2 | 概览不明确 | **确认**：存在两个口径未解释的百分比、名为"今日"实为全量的卡片、"48 项/34 项待补"与雷达 8 轴口径打架 | 🟠 P1 |
| 3 | 雷达只有 LLM，无切换 | **确认**：`pickPrimaryTrack()` 硬选 `priority=主攻`，无任何切换入口 | 🟠 P1（但**修复成本最低**） |

**一个好得多的消息**：你想要的"双角色切换"，**后端数据已经全部就位、零新增接口**。
`/api/job-hunt` 已返回 4 条赛道（llm / vlm / ai-algo / embodied），每条都带
`skills[{name, level, required, gap}]`。切雷达**只是前端换一个数据源**，`SkillRadarCard`
连改都不用改（它已支持任意 `axes[]`）。

**而脏数据的根因是架构级的**：`backend/tests/` 目录下**没有 `conftest.py`**，
绝大多数测试用 `TestClient(app)` 直连**开发库** `data/app.db`。
每跑一次 `pytest`，就往你的真实数据库里灌一批 `M Test Project`。214 个项目就是这么来的。

---

## 二、问题一：脏数据（实测证据）

### 2.1 数据库实际构成

```
表                  行数    判读
─────────────────────────────────────────────────────────────
projects             214     🔴 真实只有 2 个
milestones           178     🔴 88 条 in_progress（多数挂在测试项目下）
agent_runs           393     🔴 全部为测试产生（planner 379 / reviewer 14）
tasks                292     🔴 248 todo / 42 done / 2 doing，大量重复
skills                48     ✅ 正常（seed 校准）
job_postings           6     ⚠️ 含 1 条"测试公司"
job_matches            6     ✅ 正常
job_applications       4     ✅ 真实
interview_logs         1     ✅ 真实
interview_questions   15     ✅ 正常
resume_facts           9     ✅ 真实
resume_versions        1     ✅ 真实
report_logs            1     ✅ 正常
activity_drafts / learning_logs / skill_assessments / papers*   未统计
```

### 2.2 真实项目只有 2 个

```
#1  SO101 Embodied AI System   （具身资产，保留）
#2  求职冲刺 · 2026 Q4          （当前主线项目）
其余 212 个 = 测试残留
```

按名称聚合的重复量（Top 12）：

| 次数 | 项目名 |
|---|---|
| 42× | `M Test Project` |
| 28× | `Scaffold Test` |
| 16× | `Test Project` |
| 16× | `Planner Test` |
| 14× | `Planner E2E` |
| 14× | `Idempotent Test` |
| 14× | `Gen Test` |
| 14× | `Filter Test` |
| 14× | `E2E SO101` |
| 8× | `SO101 Embodied AI` |
| 8× | `README Test` |
| 8× | `Patch Test` |

还有 `P`、`Detail Test` 这类单字符/无意义项目名。

### 2.3 任务的重复量同样夸张

| 次数 | 任务标题 |
|---|---|
| 29× | `ROS2 Topic 通信机制实践` |
| 28× | `topic 通信 + publisher/subscriber - Subscriber 节点` |
| 28× | `topic 通信 + publisher/subscriber - Publisher 节点` |
| 28× | `topic 通信 + publisher/subscriber - Launch 文件` |
| 27× | `Python asyncio 异步编程实践` |
| 14× | `python control - 第1步 / 第2步`（各 14） |
| 14× | `VLA 模型概念梳理与论文精读` |
| 14× | `Python 控制舵机 - 第1步 / 第2步`（各 14） |
| 13× | `PyTorch 自定义 Dataset 与 DataLoader 实践` |
| 13× | `Isaac Sim 基础环境搭建` / `Isaac Sim Python API 入门` |
| 8× | `完成测试 - 第1步 / 第2步` |

注意 `Python 控制舵机 - 第X步` 与 `python control - 第X步` —— **同一个任务的中英文两套标题**，
是不同时期 seed/Planner 产出的，语义重复。

### 2.4 脏数据已经渗透到页面

| 页面 | 脏数据表现 |
|---|---|
| `/projects` | **重灾区**：前 16 张卡里 14 张是测试项目；`E2E SO101` 甚至显示"进行中 100%" |
| `/dashboard` 今日任务 | `完成测试 - 第1步`、`Old task`、`Test task`；重复项刷屏；`ROS2/VLA/Isaac` 等已冻结方向任务仍在推 |
| `/jd` 岗位池 | `测试公司 · LLM 微调工程师` 被计入"5 可优先投 (A+B)"，还进了日报推荐位 |
| `/reports` 日报 | 「今日学习任务」推的是 `ROS2 Topic 通信机制（40min）`、`SO101 ACT 模型泛化调试` —— **v2.0 已冻结具身，日报却还在推具身任务，与战略直接冲突** |
| `/interview` | 干净，但"已回写任务 #215, #216, #217, #218"指向的是被重复污染的任务池 |
| 概览 KPI | `Agent 执行 10 · 成功率 100% · 本周` —— 统计的正是那 393 条测试运行，**指标本身已失真** |

### 2.5 根因分层（这是重点）

**P0 —— 测试直连开发库**

```
backend/tests/ 目录下没有 conftest.py
```

- `test_dashboard_projects.py`、`test_e2e_project_workflow.py`、`test_milestones_api.py`、
  `test_github_api.py` 等大多数文件：`client = TestClient(app)` → 打真实 `data/app.db`
- `test_e2e_learning_loop.py:37`、`test_agent_closure.py:31` 更严重：**硬编码了 Linux 容器路径**
  `/workspace/embodied-ai-career-os/backend/data/app.db`，回退值 `data/app.db` 即开发库
- **对照组**：`test_paper_agent_e2e.py:32` 做对了 ——
  `os.environ["DATABASE_URL"] = "sqlite:///临时库"`，其 docstring 明确写着
  「不污染开发态 data/app.db」

> **正确范式已经存在，只是没推广到其他 20+ 个测试文件。** 这是本次审计最重要的发现。

**P1 —— Planner 持久化无幂等**

`app/api/planner.py:143-158`：

```python
if req.persist and task_data:
    new_task = Task(title=..., skill_name=..., ...)   # 无条件 INSERT
    db.add(new_task)
```

没有 `(title, skill_name, 当天)` 去重 → 每点一次「生成今日任务」就多一条。
379 次 planner 运行 → 292 条任务。

**P1 —— 缺少"今日"语义**

- `GET /api/tasks` 只支持 `project_id` 过滤，**无 status / 无日期 / 无 limit**
- 前端 `TodayTasks` 组件名叫"今日任务"，实际渲染传进来的全量 292 条，
  头部写「已规划 292 项 · 完成 42 项」，KPI 写「今日任务 42/292 · 250 项待完成」
- **"今日"这个词在撒谎**

**P1 —— 无数据清理能力**

- `app/api/tasks.py` 明确注释「不做 DELETE（历史任务服务 Day7 Reviewer Agent，是宝贵数据）」
  → 清理脏数据目前只能手写 SQL
- `app/api/projects.py` 有 `DELETE /{id}`，但**没有批量清理，也没有按来源识别**

**P2 —— 测试数据没有标记（设计缺陷）**

`projects` / `tasks` / `milestones` 表**都没有 `source` / `is_test` 字段**。
事后再想区分"真数据 vs 测试残留"，只能靠名字猜（`M Test Project` 能猜，`P` 不能猜）。
**这是最该在设计上补的一环** —— 否则清理一次，下次跑测试又会长回来。

---

## 三、问题二：概览（Dashboard）为什么不明确

逐条给出证据（截取自 `/dashboard` 实际渲染文本）：

| 现象 | 证据 | 问题 |
|---|---|---|
| **名实不符** | h1 = `Embodied AI Career OS`，副标题 = 「AI 驱动的求职作战看板」 | 系统名还停在具身时代，与已转向的求职主线打架 |
| **两个百分比并列，无口径解释** | `职业目标进度 35%`（按里程碑）+ `主攻岗位匹配度 75%`（按技能） | 用户不知道该盯哪个；35% 和 75% 谁高谁低无意义 |
| **"今日任务"名不副实** | `今日任务 42/292 · 250 项待完成` | 名为今日、实为全量；292 还被脏数据撑大 |
| **缺口口径打架** | 雷达说"8 项硬性技能"，快捷操作说`技能图谱 48 项技能 · 34 项待补` | 用户困惑：到底要补 8 项还是 34 项？ |
| **Agent 指标失真** | `Agent 执行 10 · 成功率 100% · 本周` | 统计的是测试产生的 planner 运行，无业务含义 |
| **卡片时长缺单位** | 渲染出裸数字 `20` / `30` / `40` / `0` | 代码是 `{task.duration ?? "预计 30 min"}` —— 有值时不带 "min" |
| **潜在交互 bug** | `TodayTasks` 用 `key={idx}`，且 `activeFormIdx` 也用数组下标 | 292 条含大量重复项时，点「完成并复盘」可能打开错误的卡片 |

**核心症结**：概览页把**三种不同性质的信息**（战略目标 / 能力现状 / 任务执行）
混在同一屏、用同一种视觉重量呈现，且**没有主次**。用户看不到"我现在该干什么"。

---

## 四、问题三：雷达图与双角色切换（我理解的需求）

### 4.1 我理解你要的是什么

> **不是**两套系统，**也不是**单纯的"再加一个雷达图"。
> 你要的是：**同一份能力数据，两个观察视角，随时切换。**

- **视角 A｜求职冲刺（LLM 主攻）** —— 当前主线。
  看 Transformer / Attention / SFT / LoRA… 的 8 轴差距，服务于 10 月底拿 offer。
- **视角 B｜具身智能（长期目标）** —— 未来方向。
  看 ROS2 / VLA / Robot Learning / Isaac / Sim2Real 的积累，
  服务于"随时巩固基础、保持具身手感"，不让这条线在冲刺期彻底荒废。

一句话：**视角 A 决定"今天投什么、补什么"，视角 B 回答"我的具身底子还剩多少"。**

### 4.2 数据已就位（零后端改动）

`GET /api/job-hunt → target_roles` 已返回（实测）：

| key | 名称 | priority | frozen | 技能（level/required） | 匹配度 |
|---|---|---|---|---|---|
| `llm` | LLM / 大模型算法工程师 | 主攻 | 否 | Transformer 3/4、Attention 3/4、Pretraining 2/4、SFT 3/4、LoRA/QLoRA 3/4、PyTorch 3/4、Python 4/4、Deep Learning 3/4 | **75%** |
| `vlm` | 多模态 / VLM 算法工程师 | 卡位 | 否 | ViT 2/4、Multimodal Alignment 1/4、VLM 1/4、LoRA/QLoRA 3/4、PyTorch 3/4、Python 4/4 | **58%** |
| `ai-algo` | AI 算法 / 推理工程师 | 保底 | 否 | Python 4/4、Deep Learning 3/4、PyTorch 3/4、Inference Optimization 2/4、Linux 3/4 | **75%** |
| `embodied` | 具身智能 / VLA 算法工程师 | 暂缓 | **是** | ROS2 2/4、VLA 1/4、Robot Learning 2/4、PyTorch 3/4、Isaac 1/4、Sim2Real 0/4 | **38%** |

> 匹配度公式实测为 `mean(level / required)`（llm 24/32=75%、vlm 14/24=58%、embodied 9/24≈38% 全部吻合）。
> 赛道对象字段（实测）：`key / name / priority / salary_range / note / frozen / match_pct / skills[]`，
> 其中 `skills[].fields = name / level / required / gap / missing`。
> 注意是 snake_case `match_pct`，前端由 service 层 adapter 转 camelCase。

**所以切换器是纯前端改动**：`pickPrimaryTrack()` 从"硬选主攻"改为"按当前视角选赛道"，
`SkillRadarCard` 一行不用改。

### 4.3 一个必须由你拍板的张力（重要）

`target_roles.py` 把具身标了 `frozen=True`、并把 `ROS2/VLA/Isaac/Sim2Real` 放进 `TECH_BLACKLIST`，
含义是 v2.0 的「30 天内不主动深挖」。但你现在说「需要随时巩固基础、学习具身知识」。
**这两个要求在"是否允许 Planner 产出具身任务"上直接冲突**，必须选一个：

| 方案 | 视角 B 能看到 | Planner 行为 | 风险 | 我的建议 |
|---|---|---|---|---|
| **① 只读盘点** | 具身雷达 + 缺口 | 仍只出 LLM 任务 | 最保守，完全遵守 v2.0；但"学习具身"落不了地 | |
| **② 低强度巩固通道**（推荐） | 同上 | 切到视角 B 时，Planner 可出**具身巩固任务**，但单任务 ≤45min、且不进入「主攻技能缺口」推动列表 | 略微突破 v2.0 的"不深挖"，但符合你"保持手感"的真实诉求 | ✅ |
| **③ 完全放开** | 同上 | 按具身赛道正常规划 | 30 天冲刺期路线发散，直接威胁 offer 目标 | |

我倾向 **②**：给具身一条**受控的"保养"通道**（短时长、不抢主线时间、不推动技能缺口），
既尊重 v2.0 的战略纪律，又满足你"不丢手感"的需求。

### 4.4 切换器的技术选型

**用 URL 参数 + cookie 记忆，不用纯 localStorage。**

| 方案 | SSR 友好 | 可分享/收藏 | 首屏闪烁 | 结论 |
|---|---|---|---|---|
| 纯 localStorage | ❌ Server Component 读不到 | ❌ | ✅ 会闪烁 / hydration mismatch | ✗ |
| **URL `?role=embodied` + cookie 记忆上次选择** | ✅ `searchParams` 原生可读 | ✅ | ✅ 无闪烁 | ✅ 推荐 |
| 后端配置写死 | ✅ | ❌ | ✅ | 需要重启后端才能切，不适合"随时切" |

实现：新增 `RoleSwitcher.tsx`（Client，分段控件）→ `router.push('?role=...')`
→ Server Component 读 `searchParams.role` → 选赛道 → 传给 `SkillRadarCard` / `KpiCards`。

**纪律**：视角**只改"看什么"，不改数据**。不删任何记录、不解除 `TECH_BLACKLIST`、
不改 `frozen` 字段（方案 ② 的任务生成走独立开关，不动赛道配置）。

---

## 五、修复方案与分阶段计划

> **执行状态（2026-09-10）**：阶段 A / B / C / D **全部完成并验证**；阶段 E 未启动。
> 验证证据见文末「七、执行结果与验证」。

### 阶段 A · 止血：测试隔离（0.5 天，P0，先做这个） ✅ 已完成

1. 新增 `backend/tests/conftest.py`：session 级把 `DATABASE_URL` 指向临时 SQLite
   （复用 `test_paper_agent_e2e.py` 已验证的范式），结束自动清理
2. 清理 5 个硬编码 `/workspace/...` 路径的测试文件
3. 把「测试不得写开发库」写进 `.workbuddy/memory/MEMORY.md` 作为硬约束

> **不做这步，后面所有数据清理都会白费** —— 下次跑 `pytest` 又长回来。

**实际落地补充**：
- `conftest.py` 的守卫会被「模块级 `client = TestClient(app)`」绕过 lifespan 的问题绊倒，
  因此守卫内部**直接调用 `init_db()`** 建表灌种子（原实现依赖 TestClient 的 lifespan）。
- 5 个 paper 系列测试原本各自维护临时库 + **import 期 `unlink()`**，
  删除失败会中断 pytest **收集阶段**。已统一改为依赖 `conftest.py`，
  彻底移除 import 期的文件系统副作用。
- 依赖「运行中后端 :8000」的 3 个 E2E 脚本（`test_agent_closure` /
  `test_e2e_learning_loop` / `test_phase2_week1`）加入 `collect_ignore`，
  因为它们通过真实 HTTP 请求打的是外部进程的库，conftest 的隔离管不到。

### 阶段 B · 数据治理（0.5 天，P0） ✅ 已完成

4. 给 `projects` / `tasks` / `milestones` 加 `source` 字段
   （`user`(默认) / `test` / `seed` / `planner`），测试与 seed 写入时打标
5. 新增 `backend/scripts/purge_test_data.py`：
   - **默认 dry-run**，只打印将被处理的清单
   - `--apply` 才执行；执行前**自动备份** `app.db` 到 `.workbuddy/backup/`
   - 分批执行（每批 ≤10 个实体），每批后校验
   - **白名单保护**：`job_applications` / `resume_facts` / `interview_logs` / `career_goal` 一律不动
6. Planner 幂等：同 `(title, skill_name, 当天)` 已存在则复用，不新增

> **落地补充**：迁移以 `migrations/0007_source_marker.sql` 落库（`_migrations_applied` 追踪）。
> `source` 在 Pydantic 响应模型里加了 `mode="before"` 校验器把 `None` 回落为 `user`
> —— 未 flush 的 ORM 实例列默认值尚未生效，否则 `model_validate` 会报 `string_type`。

### 阶段 C · 概览口径修正（0.5 天，P1） ✅ 已完成

7. 两个百分比标签化：`职业目标进度` → **`里程碑进度`**（并说明是 Career 里程碑）；
   `主攻岗位匹配度` → **`岗位匹配度`**（随视角变）
8. h1 随视角变：`求职作战看板` / `具身智能成长看板`
9. `今日任务` → **`任务池`**（或加"近 7 天"过滤）；KPI 改 `任务进度 done/total`
10. `技能图谱 48 项 · 34 项待补` → **`本视角待补 N 项`**（jobhunt 6 项 / embodied 5 项）
11. `Agent 执行` 指标：剔除 `source=test` 的运行，或换成"近 7 天规划任务数"
12. 修 UI bug：`key={idx}` → `key={task.id}`；时长补 `min` 单位

### 阶段 D · 双角色切换（1 天，P1 —— 你的核心诉求） ✅ 已完成

13. `RoleSwitcher.tsx`（分段控件：求职冲刺 ⇄ 具身智能）+ URL `?role=` + cookie 记忆
14. `pickPrimaryTrack()` → `pickTrackByRole(roles, role)`
15. Dashboard / /jobs 按视角渲染（雷达轴、匹配度、缺口数、h1、副标题全部跟随）
16. （若选方案 ②）视角 B 下的 Planner 低强度巩固通道

> **落地补充**：视角状态走 **URL `?role=` + cookie `view_role`**，由 Server Component
> 读取 —— 不用 localStorage，避免客户端水合不一致导致的闪烁。
> 项 16（视角 B 的 Planner 低强度巩固通道）**未实现**，需你确认后再做（见审计结论）。

### 阶段 E · 可选增强 ⏸ 未启动

17. 视角扩展到 4 赛道（llm / vlm / ai-algo / embodied），而非只有 2 个
18. `TECH_BLACKLIST` 命中时的处理：从"直接拒绝"改为"提示 + 二次确认"

---

## 六、风险与"不要做的事"

| 风险 / 禁忌 | 说明 |
|---|---|
| ✗ **不要在阶段 A 之前清理数据** | 测试不隔离，清完还会长回来 |
| ✗ **不要直接 `DELETE FROM projects`** | 会级联影响 milestones / tasks 外键；必须先 dry-run 出清单、备份、分批 |
| ✗ **不要碰真实业务表** | `job_applications` / `resume_facts` / `interview_logs` / `career_goal` 是真实数据，清理脚本必须白名单保护 |
| ✗ **不要 fork 两套前端** | 两个角色 = 两个**视角**，不是两份代码。两套代码必然漂移 |
| ✗ **不要让视角改动数据** | 切视角不能删记录、不能改 `frozen`、不能改 `TECH_BLACKLIST` |
| ⚠ **视角 B 会暴露"具身只有 38%"** | 这是事实，不是 bug。但要明确标注"这是长期视角，非当前冲刺目标"，避免焦虑 |
| ⚠ **`测试公司` 岗位需人工确认** | 它已进入 `job_matches` 并被日报引用，删之前要确认不是有意留的对照样本 |
| ⚠ **`SO101 Embodied AI System` 与 `SO101 Embodied AI`（#1 / #15）可能重复** | 需人工判断哪个是主项目，不要自动删 |

---

## 七、执行结果与验证（2026-09-10）

### 7.1 数据治理前后对比

| 表 | 清理前 | 清理后 | 判定 |
|---|---|---|---|
| `projects` | 214 | **2** | ✅ 仅剩真实项目（`SO101 Embodied AI` / `Claw Code Agent`） |
| `milestones` | 178 | **12** | ✅ |
| `tasks` | 292（单任务最多重复 29 次） | **17→18** | ✅ 去重并剔除 `source=test` |
| `agent_runs` | 393（全部为 `target_role="Robot AI Engineer"` 测试残留） | **6** | ✅ |

白名单表（`job_applications` / `resume_facts` / `interview_logs` / `career_goal` /
`interview_questions` / `report_logs` / `skills` / `job_postings` / `job_matches`）
**行数零变化**，清理未触碰任何真实业务数据。

### 7.2 测试隔离验证（阶段 A 的验收门）

```
$ ./.venv/Scripts/python.exe -m pytest tests -q
147 passed, 614 warnings in 9.87s
```

跑完整套测试前后，用 md5 比对开发库：

```
$ md5sum -c db_before.md5
data/app.db: OK          ← 指纹完全一致，一个字节都没被写
```

| 指标 | 套件运行前 | 套件运行后 |
|---|---|---|
| `app.db` md5 | `18e97d50…37bb` | `18e97d50…37bb` ✅ |
| `projects` | 2 | 2 |
| `milestones` | 12 | 12 |
| `tasks` | 18 | 18 |
| `agent_runs` | 9 | 9 |

**结论：测试已彻底与开发库解耦。** 清理后的数据不会再被 `pytest` 重新灌脏。
`backend/data/` 目录下也只剩 `app.db` 一个文件，不再有 `test_paper_*.db` 残留。

### 7.3 双角色切换验证

| 路由 | 雷达图 | 匹配度 | 视角标题 |
|---|---|---|---|
| `/dashboard` | LLM 主攻 8 轴 | 75% | 求职作战看板 |
| `/dashboard?role=embodied` | 具身 6 轴 | 38% | 具身智能成长看板 |

两套视角均由 Server Component 服务端渲染，无客户端闪烁 / hydration 警告。

### 7.4 遗留决策项（需你拍板）

- **§4.3 视角 B 的 Planner 行为**：切到「具身智能」视角时是否允许 Planner 出**具身任务**？
  建议是「低强度巩固通道」（单任务 ≤45min、不进主攻缺口推动列表），而非完全放开。
  当前实现为**完全不生成**，保持 v2.0「LLM 主攻、具身 frozen」不变。

---

## 八、一句话总结

**脏数据的根因是"测试直连开发库"（`tests/` 缺 `conftest.py`），先修这个再清数据；
概览的问题是"三种信息混在一屏、没有主次"；
而你要的双角色切换，后端数据已完全就位，是三个问题里最便宜的一个 ——
`pickPrimaryTrack()` 从"硬选主攻"改成"按 `?role=` 选赛道"即可，
`SkillRadarCard` 一行都不用动。**

唯一需要你拍板的是 §4.3：切到「具身智能」视角时，**要不要允许 Planner 出具身任务**（我建议给低强度巩固通道，而非完全放开）。
