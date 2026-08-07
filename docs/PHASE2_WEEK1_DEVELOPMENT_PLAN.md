# Embodied AI Career OS v1.0 · Phase 2 Week 1 Development Plan

## Week 1 主题：Agent Runtime 升级 —— 从单 Agent 到 Multi-Agent Supervisor

---

## 一、Week 1 总目标

### Phase 1 已完成（单线流程）

```text
Career Goal
    ↓
Skill Gap
    ↓
Planner Agent
    ↓
Task
    ↓
Learning Log
    ↓
Reviewer Agent
    ↓
Skill Update
```

### Phase 2 Week 1 目标（升级为 Multi-Agent Supervisor 架构）

```text
                 User Intent
                     ↓
              Supervisor Agent
                     ↓
        ┌────────────┼────────────┐
        ↓            ↓            ↓
 Career Agent   Planner Agent  Research Agent
        ↓            ↓            ↓
        └────────────┼────────────┘
                     ↓
              Reviewer Agent
                     ↓
              Learning Loop
```

### Week 1 核心能力对照表

| 能力          | Phase 1 | Phase 2 Week 1 |
| ------------- | ------- | -------------- |
| Agent 数量    | 2       | 5              |
| Agent 调度    | ❌       | ✅ Supervisor   |
| 任务生成      | 规则    | Agent 协作     |
| 职业分析      | 静态    | Career Agent   |
| 学习规划      | 单轮    | 多 Agent       |
| LLM 支持      | ❌       | 准备接入       |
| Agent 运行记录 | 基础    | 完整 Tracing   |

---

## 二、Day 1 · Agent Runtime 重构

### 1. 开发任务

**目标**：建立统一 Agent 基础框架。

**当前结构**：

```text
agents/
  planner/
  reviewer/
```

**问题**：每个 Agent 各自实现 `state` / `graph` / `execution`，导致重复代码。

**改造为**：

```text
agents/
├── core/
│   ├── agent.py
│   ├── state.py
│   ├── executor.py
│   └── registry.py
├── planner/
└── reviewer/
```

### 2. 技术学习任务

学习 **LangGraph 核心概念**，重点：

1. StateGraph
2. Node
3. Edge
4. Conditional Edge
5. Checkpoint

**目标**：能够解释 —— *LangGraph 为什么适合 Multi-Agent 系统？*

### 3. 文件变化

**新增**：

```text
backend/app/agents/core/
  ├── agent.py
  ├── state.py
  ├── executor.py
  └── registry.py
```

**修改**：

```text
backend/app/agents/planner/graph.py
backend/app/agents/reviewer/graph.py
```

### 4. Trae / Claude Code Prompt

```text
你现在负责重构 Embodied AI Career OS Agent Runtime。

目标：
把 Planner Agent 和 Reviewer Agent
抽象成统一 Agent Framework。

要求：
新增 agents/core/ 实现：
1. BaseAgent
2. AgentState
3. AgentExecutor
4. AgentRegistry

要求：
不要改变现有业务逻辑。
Planner 和 Reviewer 必须继续运行。

执行前输出：
1. 当前 Agent 架构分析
2. 文件变化
3. 重构计划
等待确认。
```

### 5. 验收标准

运行：

```bash
pytest tests/agents
```

通过：

```text
Planner Agent PASS
Reviewer Agent PASS
```

新增能力：

```python
AgentRegistry.list_agents()
```

输出：

```python
[
    "planner",
    "reviewer",
]
```

---

## 三、Day 2 · Supervisor Agent 设计

### 1. 开发任务

新增 **Supervisor Agent**。

**职责**：理解用户需求，决定调度哪些 Agent。

例如输入：

```text
我要学习 Isaac Lab
```

Supervisor 判断需要：

```text
Research Agent + Planner Agent
```

### 2. State 设计

```python
SupervisorState:
    user_input
    intent
    required_agents
    execution_plan
    result
```

### 3. Graph 结构

```text
START
  ↓
analyze_intent
  ↓
select_agents
  ↓
create_plan
  ↓
END
```

### 4. 技术学习任务

学习 **LangGraph Multi Agent Pattern**，重点：

- supervisor pattern
- routing
- agent handoff

### 5. 文件变化

**新增**：

```text
agents/supervisor/
  ├── state.py
  ├── graph.py
  └── nodes.py
```

**修改**：

```text
agents/core/registry.py
```

### 6. Prompt

```text
实现 Supervisor Agent。

目标：
根据用户输入决定调用哪些 Agent。

例如：
学习 ROS2     → Research + Planner
完成任务      → Reviewer
职业规划      → Career Agent

要求：
使用 LangGraph。
不要接 LLM。
先使用规则 Router。

执行前输出方案。
```

### 7. 验收标准

输入：

```json
{
  "message": "我要学习 VLA"
}
```

输出：

```json
{
  "agents": ["research", "planner"]
}
```

---

## 四、Day 3 · Career Agent

### 1. 开发任务

实现 **Career Agent**。

**作用**：负责岗位分析、Skill Gap 计算、学习方向推荐。

**输入**：

```text
target_role
current_skill
```

**输出**：

```text
skill_gap
priority
recommendation
```

### 2. 技术学习任务

- Career Recommendation Agent 设计
- Skill Ontology 概念

### 3. 文件变化

**新增**：

```text
agents/career/
  ├── state.py
  ├── graph.py
  ├── nodes.py
  └── rules.py
```

**新增模型**：

```text
models/career_analysis.py
```

### 4. Prompt

```text
实现 Career Agent。

输入：
- 用户目标岗位
- 当前 Skill

输出：
1. Gap 分析
2. 优先学习技能
3. 推荐路线

保持 Rule-based。
不要调用 LLM。
```

### 5. 验收标准

输入：

```text
target_role: Robot AI Engineer
skills:
  ROS2    = 1
  Isaac   = 0
  PyTorch = 3
```

输出：

```text
priority:
  1. Isaac
  2. ROS2
  3. Robot Learning
```

---

## 五、Day 4 · Research Agent

### 1. 开发任务

新增 **Research Agent**。

**功能**：论文 / 资料研究入口。Phase 2 先不做 RAG，先做 Research Task 生成。

例如输入：

```text
学习 ACT
```

输出：

```text
需要学习：
1. paper
2. code
3. experiment
```

### 2. 技术学习任务

学习 **Research Agent Pattern**：

- planning
- decomposition
- evidence collection

### 3. 文件变化

**新增**：

```text
agents/research/
  ├── state.py
  ├── graph.py
  ├── nodes.py
  └── templates.py
```

### 4. Prompt

```text
实现 Research Agent。

输入：技术主题
输出：研究计划（paper / code / experiment / verification）

不要联网。
使用模板。
```

### 5. 验收标准

输入：

```text
ACT
```

输出：

```json
{
  "paper": "ACT paper",
  "code": "LeRobot ACT",
  "experiment": "SO101 imitation learning"
}
```

---

## 六、Day 5 · Agent Orchestrator

### 1. 开发任务

连接 Supervisor → Agents，形成执行链。

```text
User
  ↓
Supervisor
  ↓
Career
  ↓
Planner
  ↓
Task
```

### 2. 技术学习任务

学习 **Agent workflow orchestration**。

### 3. 文件变化

**新增**：

```text
agents/orchestrator/
  ├── workflow.py
  └── executor.py
```

**修改**：

```text
api/agent.py
```

### 4. Prompt

```text
实现 Agent Orchestrator。

目标：
用户请求进入 Supervisor。
Supervisor 选择 Agent。
执行 Agent。

要求：
记录：
- agent_name
- input
- output
- duration

保存 AgentRun。
```

### 5. 验收标准

API：

```text
POST /api/agent/run
```

输入：

```text
学习 Isaac Lab
```

输出：

```text
Research Agent
Planner Agent
执行结果
```

---

## 七、Day 6 · Agent Observability

### 1. 开发任务

增强 **Agent Run Tracking**。

记录结构：

```json
{
  "agent": "planner",
  "model": "rule-v1",
  "input": "xxx",
  "output": "xxx",
  "duration": "300ms"
}
```

### 2. 技术学习任务

学习 **Agent Observability**：

- tracing
- execution log
- debugging

### 3. 文件变化

**新增**：

```text
models/agent_trace.py
services/tracing.py
```

**修改**：

```text
agent executor
```

### 4. Prompt

```text
增加 Agent 执行追踪。

要求：
所有 Agent 执行自动记录：
- 开始时间
- 结束时间
- 输入
- 输出
- 状态

不要引入第三方 Tracing 系统。
```

### 5. 验收标准

Dashboard 新增 **Agent Activity** 面板，显示：

```text
Planner executed
Reviewer executed
```

---

## 八、Day 7 · Integration + Refactor

### 1. 开发任务

整合 Phase 2 Week 1 所有 Agent。最终架构：

```text
Supervisor
  ├── Career
  ├── Research
  ├── Planner
  └── Reviewer
```

### 2. 技术学习任务

总结完成 **LangGraph Multi-Agent 基础**，输出学习文档：

```text
docs/agent-system.md
```

### 3. 文件变化

**新增**：

```text
docs/
  ├── agent-system.md
  └── phase2-week1-summary.md
```

**修改**：

```text
README.md
ARCHITECTURE.md
```

### 4. Prompt

```text
进行 Phase 2 Week 1 收尾。

任务：
1. 检查 Agent 架构
2. 运行全部测试
3. 更新文档
4. 生成架构图

不要增加新功能。
```

### 5. 验收标准

#### 功能验收

输入：

```text
我要成为 Robot AI Engineer
```

系统流程：

```text
Supervisor
  ↓
Career Agent
  ↓
Planner Agent
  ↓
生成今日任务
```

#### 技术验收

项目结构：

```text
agents/
  ├── core
  ├── supervisor
  ├── career
  ├── planner
  ├── research
  └── reviewer
```

测试：

```bash
pytest  # 全部通过
```

---

## 九、Week 1 最终成果

完成后，项目从：

> AI 学习 Dashboard

升级为：

> **Multi-Agent Embodied AI Career Operating System**

具备能力：

- LangGraph Multi-Agent
- Agent Routing
- Agent Runtime
- Agent Trace
- Career Planning
- Research Planning
- Learning Loop

---

## 十、Phase 2 后续路线衔接

```text
Week 1     Multi-Agent Runtime
             ↓
Week 2     LLM Provider + Prompt System
             ↓
Week 3     Agent Intelligence
             ↓
Week 4-6   Knowledge Base + RAG
             ↓
Week 7-9   Robot Experiment OS
             ↓
Week 10-12 Career Portfolio Agent
```

---

## 设计原则

> **Week 1 的设计重点是：不要急着堆功能，而是先把 Agent 基础设施搭牢。**
>
> 后面的 RAG、论文阅读、Isaac 实验管理、机器人项目管理都会复用这一层。
