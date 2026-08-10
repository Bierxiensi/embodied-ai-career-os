# Embodied AI Career OS V2 迭代设计

> 2026-08-10 · 基于 `docs/plane.md` 立项规划的系统偏差分析与迭代路线

---

## 一、现状诊断

### 1.1 立项回顾

`docs/plane.md` 定义了**双轨系统**：

| 轨道 | 内容 | 定位 |
|------|------|------|
| **主轨道 A** | SO101 Embodied AI End-to-End System（V0-V6：Python 控制 → ROS2 → MoveIt2 → ACT → SmolVLA → Isaac Lab → Sim2Real） | 核心交付物，简历项目 |
| **辅轨道 B** | Embodied AI Learning OS（能力图谱 → Planner → Reviewer → 知识库 → 每日任务 → 提醒 → 复盘） | 支撑系统，管理学习过程 |

### 1.2 当前实际

| 模块 | 完成度 | 说明 |
|------|--------|------|
| Multi-Agent 框架（Supervisor/Planner/Reviewer/Career/Research/Knowledge） | 85% | LangGraph 架构完整，规则引擎可用 |
| 数据库层（9 张表） | 90% | SQLAlchemy + PostgreSQL，种子数据就绪 |
| API 层（8 个路由模块） | 85% | FastAPI，CRUD + Agent 触发端点完整 |
| RAG 知识库（Paper Agent） | 80% | 向量检索可用，规则组答 |
| 前端 Dashboard | 75% | Next.js + 雷达图 + 技能卡 + 任务卡 |
| Docker 部署 | 100% | postgres + backend + frontend |
| LLM 真实接入 | 20% | 抽象层已架好，Agent 仍以规则驱动 |
| **SO101 机器人项目** | **0%** | 无任何 ROS2/ACT/VLA/Isaac 代码 |

### 1.3 偏离结论

**辅轨道（Learning OS）已完成 ~80%，主轨道（SO101 机器人）为 0%。**

偏离原因合理：Learning OS 贴近当前技能栈（FastAPI + LangGraph + Next.js），SO101 需要 ROS2/C++/机器人运动学等短板技能。当前优先完成 Learning OS 使其成为能"推着人走"的系统，再全力投入 SO101，这一策略被用户确认。

### 1.4 Learning OS 的核心缺口

系统骨架完整但缺少四个关键能力，导致**无法真正运转**：

1. **Agent 不够智能**——规则引擎只能生成模板化输出，没有 LLM 驱动的个性化能力
2. **缺少推送机制**——用户必须主动打开 Dashboard，中断后无人提醒
3. **技能升级依赖手动操作**——GitHub 上写的代码和系统里的技能等级完全断开
4. **和日常使用的 AI 工具隔离**——Learning OS 规划了任务，但执行在 Trae/Claude Code/WorkBuddy 中，两者没有数据流动

---

## 二、迭代目标

将 Learning OS 从"架构完整的空壳"升级为"能自动运转的 AI 教练系统"。

**成功标准**：
- 用户每天收到一条微信/终端提醒，知道今天该学什么
- 用户写完代码 push 后，系统自动感知，生成活动草稿等待确认
- 用户只需回"1"或在 Dashboard 点"确认"，就能完成学习闭环
- Reviewer 用 LLM 评估学习质量，自动更新技能等级
- 中断 3 天后回来，系统自动恢复上下文，告诉用户从哪继续

---

## 三、四大模块设计

### 模块 A：LLM 真实驱动 Agent

#### 3A.1 当前状态

| Agent | 当前驱动方式 | 局限性 |
|-------|------------|--------|
| Supervisor | 关键词正则匹配 | 无法理解自然语言意图 |
| Planner | 规则引擎（查 gap → 取首项 → 模板填任务） | 每日生成一模一样的内容 |
| Reviewer | 规则函数（有代码+1，有截图+1，有反思+1） | 不懂语义质量 |
| Career | 固定字典查表 | 不懂市场动态 |
| Research | 模板匹配（ACT → 预置模板） | 不懂论文内容 |

LLM Provider 层（`app/llm/`）已完成抽象（`LLMClient` / `get_llm` / Provider 切换），但 Agent 层尚未接入。

#### 3A.2 目标架构

```
用户输入 → Supervisor (LLM 意图理解)
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
Planner   Career    Research
(LLM 生成 (LLM 分析  (LLM 拆解
个性化任务) 技能缺口)  研究计划)
    │         │         │
    └─────────┼─────────┘
              ▼
         Reviewer (LLM 证据评估)
              │
              ▼
        Skill Level 自动更新
```

#### 3A.3 各 Agent 改造方案

**Supervisor → LLM 意图路由**

```
输入: "我想了解 VLA 在机械臂抓取上的最新进展"
输出: {intent: "research", agents: ["research"], confidence: 0.92}

输入: "今天只有 30 分钟，学点什么"
输出: {intent: "learn", agents: ["planner"], confidence: 0.87}

Fallback: LLM 调用失败 → 回退现有规则匹配
```

**Planner → LLM 智能任务生成**

```
输入:
  - skill_name: "ROS2"
  - current_level: 1
  - target_level: 4
  - available_minutes: 40
  - recent_logs: ["完成 workspace 创建和 colcon build"]
  - fatigue: "normal"
  - user_context: "6.5年开发，Python 熟练，机器人新手，有 SO101 真机"

LLM Prompt 约束:
  - 每天只生成一个核心任务
  - 验收标准必须可验证（运行截图 / Git commit / 代码可执行）
  - 难度递进：不要跨级跳跃
  - 结合用户背景（有真机可操作的优势）

输出 (TaskOutput):
  title: "ROS2 publisher 节点：发布 SO101 关节控制指令"
  skill: "ROS2"
  objective: "创建 publisher 节点，发布 /joint_commands 话题"
  duration: 40
  difficulty: "beginner"
  acceptance: ["创建 so101_control 包", "topic echo 能收到消息", "Git commit 代码"]
  resources: ["ROS2 官方 Tutorial: Creating a package", "SO101 舵机控制协议文档"]
  status: "todo"

保留 safe_generate: LLM 调用失败 → fallback RuleGenerator
```

**Reviewer → LLM 证据评估**

```
输入:
  - task: {title, skill_name, acceptance, ...}
  - learning_log_content: "完成了 publisher 节点，topic 通信正常..."
  - artifact_url: "https://github.com/.../commit/abc123"
  - github_evidence: [{commit_sha, message, files_changed, ai_suggestions}]
  - 历史 assessments: [{old_level, new_level, reason, date}]

LLM Prompt 约束:
  - 评估维度：理解深度(1-5) / 完成质量(1-5) / 是否真正掌握
  - 参考 evidence 和 acceptance 的匹配度
  - 如果连续 3 次同类任务完成良好 → 可升级
  - 如果依赖 AI 工具比例过高 → 降置信度

输出:
  {new_level: 2, confidence: 0.72, reason: "...", should_level_up: true}

Fallback: LLM 失败 → 回退 rule_generator + score_evidence
```

**Career → LLM 缺口分析**

```
输入:
  - target_role: "Robot AI Engineer"
  - current_skills: [{name, level, target_level, evidence}, ...]
  - 岗位描述（可选，用户粘贴）

输出:
  {matched: [...], missing: [...], priority: ["ROS2", "Isaac", "C++"],
   market_insights: "当前 VLA 岗位普遍要求 Sim2Real 经验...",
   suggested_timeline: "0-2月: ROS2+MoveIt2; 2-4月: ACT+SmolVLA; ..."}

保留固定字典作为 fallback
```

**Research → LLM 研究计划拆解**

```
输入: topic="ACT 算法"
输出:
  {plan: {
    paper_candidates: ["ACT original paper", "ACT with Diffusion enhancement"],
    code_repos: ["tonyzhaozh/act", "huggingface/lerobot"],
    experiment_design: "在 SO101 上复现 20 episodes pick-place，对比 chunk_size 影响",
    verification: "泛化到 3 个新位置，成功率 > 60%"
  }}

保留预设模板作为 fallback
```

#### 3A.4 Provider 选择

| 场景 | Provider | 原因 |
|------|----------|------|
| 主力生产 | DeepSeek API | 低成本，中文好，用户已有 |
| 离线/隐私 | Ollama（本地 7B） | 16GB 显存可跑，零费用 |
| 复杂推理 | OpenAI 兼容 API | 任何兼容服务可替换 |
| 开发调试 | Mock（默认） | 零依赖，可单测 |

#### 3A.5 改造文件清单

```
backend/app/agents/
├── supervisor/nodes.py        ← analyze_intent 接 LLM
├── planner/
│   ├── generators/llm_generator.py  ← 增强 prompt（已有骨架）
│   └── nodes.py
├── reviewer/nodes.py           ← evaluate_evidence 接 LLM
│   └── rules.py                ← 保留为 fallback
├── career/nodes.py             ← analyze_target 接 LLM
│   └── rules.py                ← 保留为 fallback
└── research/nodes.py           ← match_template 接 LLM
```

---

### 模块 C：每日自动提醒系统

#### 3C.1 设计目标

1. **早间推送**（默认 8:30）：今日任务 + 预计时长 + 技能进度
2. **晚间检查**（默认 21:00）：今天完成了吗？引导快速确认
3. **中断恢复**（>3 天无活动）：自动恢复上下文 + 建议从哪继续
4. **手机收到**——不依赖打开电脑和 Dashboard

#### 3C.2 推送通道

```
              Notification Service (抽象层)
                      │
      ┌───────────────┼───────────────┐
      ▼               ▼               ▼
Server酱 (微信)      Email           Terminal
(首选，免费 5条/天)  (备选)          (开发调试)
```

首选 **Server酱**：注册获取 SendKey，`POST` 一行代码，微信服务号立刻收到。

#### 3C.3 调度机制

技术选型：**APScheduler**（轻量，无需 Redis/Celery，FastAPI lifespan 内嵌）

```python
# FastAPI lifespan 新增
start_scheduler():
    ├── Job: morning_reminder   cron: 30 8 * * *
    ├── Job: evening_check      cron: 0 21 * * *
    └── Job: inactivity_detect  cron: 0 10 * * *
```

#### 3C.4 推送模板

**早间推送**：
```
☀️ 今日学习任务

📌 ROS2 Topic 通信
   创建 publisher/subscriber 节点
   预计 40 分钟
   验收：代码截图 + Git commit

📊 ROS2 Lv1 ██░░░ → Lv4
```

**晚间检查**：
```
🌙 今日学习回顾

ROS2 publisher 任务完成了吗？
回 "1"=完成  "2"=部分  "3"=没做

（不回默认记录为未完成）
```

**中断恢复**（3 天无活动触发）：
```
👋 3 天不见了

离开前：ROS2 publisher 节点 (进度 60%)
未完成：subscriber 实现 + launch 文件

🔁 今天建议：继续 subscriber 实现 (30 分钟)
```

#### 3C.5 数据来源

| 推送内容 | 数据来源 |
|---------|---------|
| 今日任务 | Planner Agent（前一日或当日凌晨生成） |
| 昨日完成 | ActivityDraft 表 + LearningLog 表 |
| 技能进度 | Skill 表 level/target_level |
| 最后活动 | ActivityDraft 表 max(detected_at) |

#### 3C.6 用户配置

```python
# settings.py 新增
reminder_config = {
    "channel": "serverchan",        # serverchan | pushplus | email | terminal
    "channel_key": "",              # SendKey（用户填）
    "morning_time": "08:30",
    "evening_time": "21:00",
    "inactivity_days": 3,
    "timezone": "Asia/Shanghai",
}
```

#### 3C.7 落地文件

```
backend/app/services/reminder/
├── __init__.py
├── scheduler.py      # APScheduler 生命周期管理
├── channels.py        # Server酱 / Email / Terminal 实现
├── templates.py       # 消息模板（早间/晚间/中断恢复）
└── engine.py          # 读数据 → 选模板 → 调通道 → 发推送
```

---

### 模块 D：GitHub Commit → AI 建议 → 人工确认

#### 3D.1 核心思路

AI 负责"看到 commit 并猜测关联什么技能"（高容错），人负责"确认或驳回"（负最终责任）。

#### 3D.2 流程

```
GitHub Push
    │
    ▼
定时拉取新 commit（每 30 分钟）
    │
    ▼
LLM 逐条分析 commit
  "这条 commit 大概率在练 ROS2（改了 ros2_ws/ 下 publisher 节点，
   commit message 提到 joint_control），建议关联 ROS2 + Python"
    │
    ▼
写入 CommitSuggestion 表（status=pending）
    │
    ▼
触达用户：
  - Dashboard "待确认"面板
  - 晚间检查一并发问（"今天 push 了 2 个 commit，确认关联网球？"）
    │
    ▼
用户 ✓ 确认 / ✗ 驳回 / ✏️ 改关联
    │
    ▼
确认的 → 写入 Skill.evidence，被 Reviewer 引用
驳回的 → 标记 ignored，不重复提醒
```

#### 3D.3 LLM Prompt 设计

```
你是一个代码活动分析器。分析以下 Git commit：

Commit Message: feat: 实现 ROS2 joint_command_publisher 节点
文件变更:
  - ros2_ws/src/so101_control/so101_control/publisher.py (+45)
  - ros2_ws/src/so101_control/launch/publisher.launch.py (+12)
  - ros2_ws/src/so101_control/package.xml (+3)
Diff 摘要: 新增 ROS2 Python publisher 节点，发布 /joint_commands 话题...

已知技能: [ROS2, Python, C++, Robot Learning, Isaac, Agent, Frontend, ...]

返回 JSON:
{
  "suggestions": [
    {"skill": "ROS2", "reason": "修改了 ros2_ws 下的 publisher 节点和 launch 文件", "confidence": 0.92},
    {"skill": "Python", "reason": "新增 .py 文件，ROS2 Python 节点实现", "confidence": 0.75}
  ],
  "suggest_ignore": false,
  "summary": "实现了 SO101 机械臂关节命令的 ROS2 publisher 节点"
}
```

#### 3D.4 数据模型

```python
class CommitSuggestion(Base):
    __tablename__ = "commit_suggestions"

    id: str                  # UUID
    commit_sha: str
    commit_message: str
    repo: str
    files_changed: JSON      # ["ros2_ws/src/.../publisher.py", ...]
    diff_summary: str        # LLM 生成的变更摘要
    ai_suggestions: JSON     # [{"skill": "ROS2", "reason": "...", "confidence": 0.92}]
    status: str              # pending | confirmed | rejected
    confirmed_skill: str | None
    confirmed_at: datetime | None
    created_at: datetime
```

#### 3D.5 落地文件

```
backend/app/services/github/
├── __init__.py
├── client.py       # GitHub API 拉 commit 列表
├── analyzer.py      # LLM 分析 commit → 生成建议
├── store.py         # CommitSuggestion 表读写
└── sync.py          # APScheduler 定时拉取 + 分析 + 手动触发入口
```

---

### 模块 F：外部 AI 工具打通

#### 3F.1 核心认知

WorkBuddy / Trae / Claude Code 都不暴露 `POST /execute` 这样的被调用 API。**对接的本质是文件系统桥接**。

#### 3F.2 方向 A：指令注入

Learning OS 把每日任务翻译成各工具能消费的格式：

```
Learning OS 每日任务："实现 ROS2 publisher"
          │
          ├─→ 生成 SKILL.md → ~/.workbuddy/skills/
          │     WorkBuddy 启动时自动加载
          │
          ├─→ 生成 project_rules.md → 项目/.trae/rules/
          │     Trae IDE 打开项目时自动读取
          │
          └─→ 生成 prompt（Dashboard 一键复制）
                手动粘贴到 Claude Code / ChatGPT
```

#### 3F.3 方向 B：结果感知（核心）

**三层收集策略**：

```
第 1 层：被动感知（零负担）
    系统检测 GitHub commits + 文件时间戳
    → LLM 推断完成了什么
    → 写入 ActivityDraft（status=pending_confirm）

第 2 层：晚间追问（极低负担）
    微信推送："ROS2 任务完成了吗？回 1=完成 2=部分 3=没做"
    → 用户回 "1" → ActivityDraft → confirmed → Reviewer

第 3 层：手动补充（可选）
    Dashboard 看到 AI 预填的草稿，修改或补充笔记
```

**核心原则：系统能猜的绝不问用户，用户只做确认/驳回。**

#### 3F.4 数据模型

```python
class ActivityDraft(Base):
    __tablename__ = "activity_drafts"

    id: UUID
    source: str              # "github_commit" | "evening_checkin" | "manual"
    source_ref: str | None   # commit_sha / task_id
    task_guess: str          # LLM 猜测对应的任务
    skill_guess: str         # LLM 猜测关联的技能
    suggested_summary: str   # AI 预填的学习总结
    status: str              # pending_confirm | confirmed | rejected | expired
    detected_at: datetime
    confirmed_at: datetime | None
    user_notes: str | None
```

#### 3F.5 用户实际负担

| 场景 | 操作 | 耗时 |
|------|------|------|
| 晚间微信提醒 | 回 "1" | 3 秒 |
| 周末 Dashboard | 扫一眼本周活动，确认/驳回几条 | 2 分钟 |
| 需要补充笔记 | 写两句话 | 30 秒 |

#### 3F.6 工具 Prompt 生成

用户仍可在 Dashboard 点击"🤖 AI 辅助"→ 选择工具 → 生成适配 prompt → 一键复制：

```
选 "Claude Code / Trae" → 生成：

请帮我创建一个 ROS2 Python package：
[具体任务要求...]

注意：我是 ROS2 初学者，请先解释架构，再写代码。
写完后用 -- 标注我需要检查的关键点。
完成后请 git commit，commit message 包含 [ros2-publisher]

选 "WorkBuddy" → 生成：

当前项目上下文：
- 仓库: so101-embodied-ai
- 最近文件: ros2_ws/src/so101_control/
- 目标: 实现 joint_command_publisher
请帮我分析现有代码结构，然后实现任务。
```

#### 3F.7 落地文件

```
backend/app/services/tools/
├── __init__.py
├── prompts.py        # Prompt 模板 + 按 tool + task_type 生成
├── context.py         # 上下文恢复包（Markdown，喂给 WorkBuddy 或 Obsidian）
├── tracker.py         # 工具使用记录（LearningLog 扩展字段）
└── activity_draft.py  # ActivityDraft CRUD + 感知引擎
```

---

## 四、实施路线

### Phase 1：LLM 接入 + 提醒骨架（第 1-2 周）

**目标**：系统能用 LLM 生成个性化任务，能发晚间提醒。

| 优先级 | 任务 | 涉及文件 |
|--------|------|---------|
| P0 | Planner LLM Generator 增强 + 接入 DeepSeek | `planner/generators/llm_generator.py`, `llm/factory.py` |
| P0 | Supervisor LLM 意图路由 | `supervisor/nodes.py` |
| P1 | Reviewer LLM 证据评估 | `reviewer/nodes.py` |
| P1 | Career / Research LLM 接入 | `career/nodes.py`, `research/nodes.py` |
| P2 | APScheduler 骨架 + Terminal 通道 | `services/reminder/scheduler.py`, `channels.py` |
| P2 | 晚间检查模板 + 引擎 | `services/reminder/templates.py`, `engine.py` |

### Phase 2：GitHub 感知 + 活动草稿（第 3 周）

**目标**：push 代码后系统自动感知，晚间提醒集成确认。

| 优先级 | 任务 | 涉及文件 |
|--------|------|---------|
| P1 | GitHub commit 拉取 + CommitSuggestion 存储 | `services/github/client.py`, `store.py` |
| P1 | LLM commit 分析器 | `services/github/analyzer.py` |
| P1 | ActivityDraft 引擎 | `services/tools/activity_draft.py` |
| P2 | Dashboard "待确认"面板 | `frontend/src/components/` |
| P2 | 晚间检查集成 commit 确认 | `services/reminder/engine.py` 更新 |
| P2 | Server酱 微信推送通道 | `services/reminder/channels.py` 新增 |

### Phase 3：工具桥接 + 中断恢复（第 4 周）

**目标**：工具 prompt 生成 + 中断恢复提醒 + 完整闭环验证。

| 优先级 | 任务 | 涉及文件 |
|--------|------|---------|
| P1 | 工具 Prompt 生成器（Trae/Claude/WorkBuddy） | `services/tools/prompts.py` |
| P1 | 上下文恢复包生成 | `services/tools/context.py` |
| P1 | 中断恢复推送模板 + 引擎 | `services/reminder/templates.py` 新增 |
| P2 | 早间推送（今日任务） | `services/reminder/engine.py` |
| P2 | Dashboard "最近活动"面板 | `frontend/src/components/` |
| P3 | 端到端闭环测试（生成任务 → 写代码 → push → 感知 → 确认 → 升级） | `tests/` |

---

## 五、不变更的部分

以下已有模块**不在本次迭代范围内**，保持现状：

- Paper Agent RAG 系统（Paper/Chunk/Embedding）——可用，E 模块延后
- Research Agent 模板系统——LLM 接入后自然增强，不需额外改造
- 前端核心组件（雷达图/技能卡/任务卡）——样式可用，仅增"待确认"面板
- Docker 部署方案——无需变更
- Career 种子数据——后续用户自行更新

---

## 六、架构总览（迭代后）

```
                         微信提醒
                            ▲
                            │
                     Server酱 / PushPlus
                            ▲
                            │
     ┌──────────────────────┴──────────────────────┐
     │              Embodied AI Career OS           │
     │                                              │
     │  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
     │  │Supervisor│  │ Planner  │  │ Reviewer  │ │
     │  │ (LLM路由)│  │(LLM生成) │  │(LLM评估)  │ │
     │  └──────────┘  └──────────┘  └───────────┘ │
     │        │             │              │        │
     │  ┌─────┴─────┐  ┌───┴────┐  ┌──────┴──────┐│
     │  │  Career   │  │Research│  │  Reminder   ││
     │  │(LLM缺口)  │  │(LLM拆解│  │  Engine     ││
     │  └───────────┘  └────────┘  └─────────────┘│
     │                                              │
     │  ┌──────────────────────────────────────┐   │
     │  │        Activity Perception           │   │
     │  │  GitHub Sync → Commit Analyzer(LLM)  │   │
     │  │         → ActivityDraft              │   │
     │  └──────────────────────────────────────┘   │
     │                                              │
     │  ┌──────────────────────────────────────┐   │
     │  │         Tool Bridge                  │   │
     │  │  SKILL.md / rules.md / Prompt Export │   │
     │  └──────────────────────────────────────┘   │
     └──────────────────────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
         WorkBuddy      Trae IDE      Claude Code
        (SKILL.md)   (project_rules)   (prompt)
                            │
                            ▼
                      GitHub Repo
                            │
                            ▼
                    CommitSuggestion
```

---

## 七、成功验收标准

| 场景 | 验收标准 |
|------|---------|
| 日常学习 | 用户每天收到晚间提醒 → 回"1" → Reviewer 自动评估 → 技能等级可能更新 |
| 中断恢复 | 用户 3 天没活动 → 第 4 天早上收到恢复提醒 → 知道从哪继续 |
| 编码感知 | 用户 push 代码 → 30 分钟内系统生成 CommitSuggestion → 晚间一并发问确认 |
| LLM 智能 | Planner 根据用户本周进度 + 疲劳度生成个性化任务，而非每天重复 |
| 工具桥接 | 用户在 Dashboard 点"AI 辅助"→ 复制 prompt → 粘贴到 Trae/Claude Code 即可工作 |
