# Phase 2 Week 1 成果总结

> 从「AI 学习 Dashboard」升级为「Multi-Agent Embodied AI Career Operating System」

## 一、目标达成

| 能力 | Phase 1 | Phase 2 Week 1 |
|---|---|---|
| Agent 数量 | 2 | 5 |
| Agent 调度 | ❌ | ✅ Supervisor |
| 任务生成 | 规则 | Agent 协作 |
| 职业分析 | 静态 | Career Agent |
| 学习规划 | 单轮 | Multi-Agent |
| LLM 支持 | ❌ | 准备接入 |
| Agent 运行记录 | 基础 | 完整 Tracing |

## 二、每日产出

### Day 1 · Agent Runtime 重构

**新增** `agents/core/`：
- `BaseAgent` 抽象基类（name / state_class / build_graph / invoke 契约）
- `AgentState` 通用状态基类（agent_name / trace_id）
- `AgentExecutor` 统一执行器（tracing + agent_runs 持久化）
- `AgentRegistry` 注册中心（register / get / list_agents）

**关键决策**：不改变现有 Planner/Reviewer 业务逻辑，框架与业务解耦。

### Day 2 · Supervisor Agent + 适配类

**新增** `agents/supervisor/`：
- `SupervisorState`（user_input / intent / required_agents / execution_plan / result）
- 3 节点图：`analyze_intent → select_agents → create_plan`
- 规则路由（4 意图：learn / complete / career / unknown）

**新增适配类**：`PlannerAgent` / `ReviewerAgent` / `SupervisorAgent` 继承 BaseAgent。

**注册**：`setup_default_agents()` 在应用 lifespan 启动时幂等注册。

### Day 3 · Career Agent

**新增** `agents/career/`：
- 岗位要求表（Skill Ontology 简化版，2 个岗位）
- Gap 计算 + 稳定排序（required > gap 大 > level 低 > 字典序）
- 推荐路线生成（focus + steps + rationale）

### Day 4 · Research Agent

**新增** `agents/research/`：
- 4 主题预设模板（ACT / VLA / Isaac Lab / ROS2）
- 别名匹配（大小写/缩写变体 → 标准 topic）
- Fallback 兜底（未命中主题生成通用模板）
- 4 类任务拆解（paper → code → experiment → verification）

### Day 5 · Agent Orchestrator

**新增** `agents/orchestrator/` + `api/agent.py`：
- `AgentWorkflow`：Supervisor 决策 → 按 plan 顺序执行 → 汇总
- 失败隔离：单 Agent 失败不中断整链
- `POST /api/agent/run`：统一 Multi-Agent 执行入口
- 上下文传递：`agent_inputs` 支持精确输入覆盖

### Day 6 · Agent Observability

**扩展 AgentRun 模型**：新增 `status` / `duration_ms` / `trace_id` 独立字段。

**新增迁移**：
- `migrations/0001_agent_runs_observability.sql`
- `migrations/run_migration.py`（支持 --status / --list / --only，幂等保护）

**新增**：
- `GET /api/agent/runs`：查询执行历史（支持 agent_name 过滤 + limit）
- `AgentActivity.tsx`：Dashboard 面板（色条 + 状态徽章 + 相对时间 + 摘要）
- `agentService.ts`：前端服务层

### Day 7 · Integration + Refactor

- 全量集成测试（`test_phase2_week1.py`，7 套件 18 用例）
- 架构文档（`agent-system.md`）
- 成果总结（本文档）

## 三、文件结构

```
backend/app/agents/
├── core/                  # Day 1：统一框架
│   ├── agent.py
│   ├── state.py
│   ├── executor.py
│   └── registry.py
├── supervisor/            # Day 2：Supervisor
├── career/                # Day 3：Career Agent
├── research/              # Day 4：Research Agent
├── planner/agent.py       # Day 2：Planner 适配类
├── reviewer/agent.py      # Day 2：Reviewer 适配类
├── orchestrator/          # Day 5：执行链
│   ├── workflow.py
│   └── executor.py
└── registry_setup.py      # 注册入口

backend/app/api/agent.py   # Day 5+6：POST /run + GET /runs
backend/migrations/        # Day 6：迁移脚本
backend/tests/test_phase2_week1.py  # Day 7：全量测试

frontend/src/
├── components/AgentActivity.tsx    # Day 6：Dashboard 面板
├── services/agentService.ts        # Day 6：前端服务
└── types/index.ts                  # Day 6：类型定义

docs/
├── agent-system.md                  # Day 7：架构文档
└── phase2-week1-summary.md          # Day 7：本文档
```

## 四、测试覆盖

`test_phase2_week1.py` 共 7 套件 18 用例：

| 套件 | 用例数 | 覆盖范围 |
|---|---|---|
| Agent Runtime | 3 | Registry / BaseAgent 契约 / Executor tracing |
| Supervisor | 4 | 4 种意图路由 |
| Career Agent | 2 | Gap 分析 + 已达标过滤 |
| Research Agent | 3 | 模板匹配 + 别名 + fallback |
| Orchestrator | 3 | 执行链 + 职业意图 + 空输入校验 |
| Observability | 4 | GET /runs + 过滤 + 新字段 + 边界 |
| 向后兼容 | 3 | /health / /api/skills / /api/planner/generate |

## 五、关键设计决策

1. **框架与业务解耦**：`core/` 框架不感知具体 Agent 实现，Planner/Reviewer 源码零改动。

2. **双编译实例隔离**：API 层与适配类各持一份 CompiledGraph，互不影响。

3. **规则路由先行**：Day 2 Supervisor 用规则路由，Week 2 接 LLM 时仅替换 `analyze_intent` 节点。

4. **失败隔离**：Orchestrator 单 Agent 失败不中断整链，记录 `status=failed` 后继续。

5. **迁移幂等**：`run_migration.py` 用 `_migrations_applied` 表 + duplicate column 捕获，支持安全重跑。

6. **Observability 字段独立**：`status` / `duration_ms` / `trace_id` 从 JSON 提升为独立列，便于 SQL 查询。

## 六、Phase 2 后续路线

```
Week 1（已完成）   Multi-Agent Runtime
        ↓
Week 2          LLM Provider + Prompt System
        ↓
Week 3          Agent Intelligence
        ↓
Week 4-6        Knowledge Base + RAG
        ↓
Week 7-9        Robot Experiment OS
        ↓
Week 10-12      Career Portfolio Agent
```
