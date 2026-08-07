# Agent System 架构文档

> Phase 2 Week 1 产出：从单 Agent 升级为 Multi-Agent Supervisor 架构

## 一、架构总览

```
                 User Intent
                     │
                     ▼
              ┌─────────────┐
              │ Supervisor  │   ← 规则路由（Week 2 接 LLM）
              └──────┬──────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   Career Agent  Planner Agent  Research Agent
        │            │            │
        └────────────┼────────────┘
                     │
                     ▼
              ┌─────────────┐
              │  Reviewer   │   ← Learning Loop 闭环
              └─────────────┘
                     │
                     ▼
              Learning Loop
```

## 二、Agent 清单

| Agent | 职责 | 输入 | 输出 |
|---|---|---|---|
| Supervisor | 意图分析 + Agent 调度 | `user_input` | `intent` + `required_agents` |
| Career | 岗位分析 + Skill Gap | `target_role` + `current_skills` | `priority` + `recommendation` |
| Planner | 生成今日学习任务 | `available_minutes` + `skills` | `task`（含验收标准） |
| Research | 研究计划生成 | `topic` | `plan`（paper/code/experiment/verification） |
| Reviewer | 学习复盘评估 | `task_id` + `content` | `assessment` + 等级更新 |

## 三、LangGraph 设计

### 3.1 为什么用 LangGraph

LangGraph 的 `StateGraph` 适合 Multi-Agent 系统：

1. **状态显式化**：每个 Agent 用 TypedDict 定义 State，节点间传递清晰
2. **图结构可视**：节点 + 边明确表达执行流程，便于调试
3. **条件路由**：`add_conditional_edges` 支持基于状态的动态分支
4. **可扩展**：Week 2 接 LLM 时仅需替换节点实现，图结构不变

### 3.2 统一框架（core/）

```
agents/core/
├── agent.py       # BaseAgent 抽象基类（name/state_class/build_graph/invoke）
├── state.py       # AgentState 基类（agent_name/trace_id）
├── executor.py    # AgentExecutor（tracing + agent_runs 持久化）
└── registry.py    # AgentRegistry（register/get/list_agents）
```

**BaseAgent 契约**：
- `name`：Agent 唯一标识
- `state_class`：State TypedDict 类
- `build_graph()`：构建 LangGraph，返回 CompiledGraph
- `invoke(state)`：执行（默认 `build_graph().invoke(state)`）

### 3.3 各 Agent 图结构

**Supervisor**（规则路由）：
```
START → analyze_intent → select_agents → create_plan → END
```

**Career**（Gap 分析）：
```
START → analyze_target → compute_gaps → prioritize → recommend → END
```

**Research**（模板匹配）：
```
START → parse_topic → match_template → decompose_tasks → build_plan → END
```

## 四、Orchestrator 执行链

```
POST /api/agent/run
    │
    ▼
AgentWorkflow.run(user_input)
    │
    ├─ 1. Supervisor 决策 → required_agents
    │
    ├─ 2. 按 plan 顺序执行各 Agent（串行）
    │     └─ 失败隔离：单个失败不中断整链
    │
    └─ 3. 汇总 → summary（overall_status + counts + elapsed_ms）
```

**关键设计**：
- **顺序串行**：Day 5 不做并行调度
- **失败隔离**：单 Agent 失败记录 `status=failed`，继续执行后续
- **上下文传递**：`agent_inputs` 参数支持为特定 Agent 提供精确输入

## 五、Observability

### 5.1 AgentRun 模型

| 字段 | 说明 |
|---|---|
| `id` | UUID 主键（即 trace_id） |
| `agent_name` | planner/reviewer/career/research/supervisor |
| `input_context` | 输入 JSON |
| `output_result` | 输出 JSON（业务数据） |
| `status` | success / failed |
| `duration_ms` | 执行耗时（毫秒） |
| `trace_id` | 追踪 ID（关联调用链） |
| `created_at` | 创建时间 |

### 5.2 Tracing 流程

```
AgentExecutor.run()
    │
    ├─ 注入 agent_name + trace_id 到 state
    ├─ 调用 agent.invoke()
    ├─ 记录 start/end 时间 → duration_ms
    └─ 写入 agent_runs 表（status + duration_ms + trace_id）
```

### 5.3 Dashboard Agent Activity

`GET /api/agent/runs` 查询历史记录，Dashboard 面板展示：
- Agent 类型色条（planner 天蓝 / reviewer 紫 / career 琥珀 / research 玫红）
- 状态徽章（success 绿 / failed 红）
- 相对时间 + 耗时 + 输出摘要

## 六、路由规则（Supervisor）

| 意图 | 关键词 | 调度 Agent |
|---|---|---|
| `learn` | 学习/学/练习/learn/study | research + planner |
| `complete` | 完成/复盘/提交/done/review | reviewer |
| `career` | 成为/职业/规划/转型/岗位 | career |
| `unknown` | （未命中） | planner（fallback） |

优先级：`career > complete > learn`（避免"成为 X 工程师"被误判为学习）

## 七、Phase 2 后续演进

| 阶段 | 升级点 |
|---|---|
| Week 2 | LLM Provider + Prompt System（替换规则路由） |
| Week 3 | Agent Intelligence（LLM 驱动决策） |
| Week 4-6 | Knowledge Base + RAG（Research Agent 接入向量检索） |
| Week 7-9 | Robot Experiment OS |
| Week 10-12 | Career Portfolio Agent |

## 八、运行方式

```bash
# 启动后端
cd backend && uvicorn app.main:app --port 8000

# 触发 Multi-Agent 执行链
curl -X POST http://localhost:8000/api/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"user_input":"学习 Isaac Lab"}'

# 查询 Agent 执行历史
curl http://localhost:8000/api/agent/runs?limit=10

# 运行全量测试
cd backend && python tests/test_phase2_week1.py
```
