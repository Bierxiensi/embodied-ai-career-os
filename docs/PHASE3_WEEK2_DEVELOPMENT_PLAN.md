# Embodied AI Career OS · Phase 3 Week 2 开发计划

> **Week 主题**：Agent Research Engineer —— 让系统从"人调用 Agent，Agent 调用工具"升级为"Agent 自主理解问题 → 检索知识 → 分析代码 → 制定实验 → 形成研究闭环"。

---

## 〇、系统建设现状（Phase 1-3 Week 1 已完成）

> 本节记录 Week 2 启动前的系统全貌，作为规划的基准线。统计日期：2026-08-05。

### 0.1 总体规模

| 维度 | 数量 | 说明 |
|---|---|---|
| Python 文件（app/） | 93 | 完整覆盖 Phase 1-3 模块 |
| ORM 模型 | 9 | Phase 1（6）+ Phase 3（3：Paper/PaperChunk/PaperChunkEmbedding） |
| 已注册 Agent | 6 | Supervisor + 5 执行 Agent（含 Phase 3 PaperKnowledge） |
| LangGraph 流程 | 7 套 | supervisor/planner/reviewer/career/research/knowledge + paper_agent |
| API Router | 8 | 统一 /api 前缀 |
| API 端点 | 19 业务 + 3 系统 = 22 | paper 模块端点最多（6 个） |
| 测试用例 | 45 个 test_ + 1 脚本式 E2E | 覆盖 Phase 1 Day6/7 + Phase 2 Week1 + Phase 3 Day1-5 |
| SQL 迁移 | 3 | 0001(observability) / 0002(papers+chunks) / 0003(embeddings) |
| 知识库论文 | 2 | ACT + Diffusion Policy（具身智能操控领域） |

### 0.2 模块架构（按层分组）

```
app/
├── core/                    # 基础设施层
│   ├── config.py            # 配置（database_url / cors / app_name）
│   └── response.py          # 统一响应 {success, data, message}
├── db/base.py               # engine + SessionLocal + Base + init_db
├── models/ (9 个 ORM)       # 数据层
│   ├── agent_run.py         # Agent 执行记录（含 status/duration_ms/trace_id）
│   ├── career.py            # 职业目标
│   ├── learning_log.py      # 学习日志（含 artifact_url）
│   ├── paper.py             # ★ 论文结构化摘要（method/dataset/contribution/relation）
│   ├── paper_chunk.py       # ★ 论文分块（section/page/char_offset）
│   ├── paper_chunk_embedding.py  # ★ 向量嵌入（JSON 存储，多模型共存）
│   ├── skill.py             # 技能图谱（level 0-5，evidence）
│   ├── skill_assessment.py  # 技能评估记录
│   └── task.py              # 任务（todo→doing→done 状态机）
├── schemas/ (6 个 Pydantic) # API 请求/响应模型
├── api/ (8 个 Router)       # 接口层
│   ├── paper.py             # ★ ingest/index/search/stats/ask/compare（6 端点）
│   ├── agent.py             # POST /run + GET /runs（Observability）
│   ├── planner.py / reviewer.py / career.py / skills.py / tasks.py / learning_logs.py
├── agents/                  # Agent 层（6 个注册 Agent + 1 个 PaperAgent）
│   ├── core/                # BaseAgent / AgentExecutor / AgentRegistry / AgentState
│   ├── supervisor/          # 意图路由（规则，Week 2 接 LLM）
│   ├── planner/             # 学习任务规划（含 generators/ 可插拔：rule 已实现，llm 预留）
│   ├── reviewer/            # 学习结果评估（Evidence Score 规则）
│   ├── career/              # 职业路径分析（岗位→技能 Gap）
│   ├── research/            # 研究计划生成（模板匹配，Week 2 升级为研究闭环）
│   ├── knowledge/           # ★ Phase 3 Day 3 论文问答（retrieve→answer）
│   └── orchestrator/        # Agent 工作流编排
└── research/                # 研究知识层
    ├── paper_agent/         # ★ Phase 3 核心
    │   ├── agent.py         # PaperAgent LangGraph: parse→chunk→summarize→persist→index
    │   ├── parser.py        # PDF(pypdf)/MD(frontmatter)/TXT 策略分发
    │   ├── chunker.py       # 结构切分→段落→滑窗，带 section 元数据
    │   ├── summarizer.py    # 规则摘要（Week 2 接 LLM）
    │   ├── comparator.py    # ★ Day 4 多论文字段级对比
    │   ├── schema.py        # PaperMeta/PaperChunk/PaperSummary
    │   └── rag/             # ★ Day 2 RAG 四件套
    │       ├── embedder.py      # HashEmbedder(开发) + SentenceTransformer(生产) + 工厂
    │       ├── vector_store.py  # SQLiteVectorStore（纯 Python 余弦，零依赖）
    │       ├── indexer.py       # 增量/全量索引构建
    │       └── retriever.py     # 语义检索 + section 过滤 + paper_title 富化
    └── knowledge/papers/    # 2 篇论文（ACT + Diffusion Policy）
```

### 0.3 Agent Registry（6 个已注册）

| # | Agent | name | LangGraph 流程 | 阶段 |
|---|---|---|---|---|
| 1 | SupervisorAgent | supervisor | analyze_intent → select_agents → create_plan | Phase 2 |
| 2 | PlannerAgent | planner | analyze_skill_gap → select_learning_target → generate_task → validate_task | Phase 2 |
| 3 | ReviewerAgent | reviewer | collect_context → evaluate_evidence → create_assessment → apply_skill_update → record_agent_run | Phase 2 |
| 4 | CareerAgent | career | analyze_target → compute_gaps → prioritize → recommend | Phase 2 |
| 5 | ResearchAgent | research | parse_topic → match_template → decompose_tasks → build_plan | Phase 2 |
| 6 | PaperKnowledgeAgent | knowledge | retrieve → answer | **Phase 3 Day 3** |

> 注：`PaperAgent`（research/paper_agent/agent.py）虽实现 BaseAgent，但通过 `/api/paper/ingest` 直接调用，未注册到 Registry（不走 Supervisor 调度）。

### 0.4 LLM 接入预留锚点（4 处代码注释明确预告 Week 2）

| 位置 | 当前状态 | Week 2 动作 |
|---|---|---|
| `paper_agent/summarizer.py:10` | 规则匹配 | 替换为 LLM 调用，签名不变 |
| `agents/knowledge/nodes.py:10` | 规则组答 | answer_node 替换为 LLM，图结构不变 |
| `agents/knowledge/agent.py:10` | 规则组答 | 仅 answer_node 内部替换，本类不变 |
| `planner/generators/llm_generator.py:4` | 抛 NotImplementedError | 实现 generate()，接入 DeepSeek/Qwen/Ollama |

### 0.5 未开始模块（Week 2 目标）

| 模块 | 状态 | 对应 Day |
|---|---|---|
| `app/llm/` | 不存在 | Day 1 新建 |
| `app/prompts/` | 不存在 | Day 2 新建 |
| `agents/supervisor/` LLM 路由 | 规则驱动 | Day 3 升级 |
| `research/code_agent/` | 不存在 | Day 4 新建 |
| `knowledge_graph/` | 不存在 | Day 5 新建 |
| `agents/research/` 研究闭环 | 模板匹配 | Day 6 升级 |

---

## 一、Week 总目标

### 1.1 定位：从"工具调用"到"研究闭环"

当前系统已具备完整链路：`Career OS → Skill Graph → Planner → Reviewer → Paper RAG`，但本质仍是**人调用 Agent，Agent 调用工具**。Week 2 的目标是升级为：

> **Agent 自主理解问题 → 检索知识 → 分析代码 → 制定实验 → 形成研究闭环**

这是从 **AI Agent Developer** 到 **Embodied AI Agent Engineer** 的关键一步。

### 1.2 目标架构

```
                 User Question
                      │
                Supervisor Agent          ← Day 3 升级：LLM 判断意图
                      │
 ┌────────────────────┼────────────────────────┐
 ▼                    ▼                        ▼
Paper Agent      Code Agent              Research Agent      ← Day 4/6
(Week1 已完成)   (Day 4 新建)            (Day 6 研究闭环)
                      │
              ┌───────┴────────┐
              ▼                ▼
        Knowledge Graph    Vector DB        ← Day 5 新建
        (Paper/Code/       (Paper+Code
         Skill/Robot)       统一检索)
                      │
                      ▼
          Research Answer + Experiment Plan + Next Action
```

### 1.3 Day 划分总览

| Day | 主题 | 主线 | 依赖 | 与现状关系 |
|---|---|---|---|---|
| Day 1 | LLM Provider Layer | 基础设施 | 无 | 新建 `app/llm/`，替代 4 处锚点的 NotImplementedError |
| Day 2 | Prompt Engineering System | 基础设施 | Day 1 | 新建 `app/prompts/`，集中管理散落 prompt |
| Day 3 | Supervisor Agent 升级 | 智能化 | Day 1+2 | 升级 `agents/supervisor/`，规则路由→LLM 路由 |
| Day 4 | Code Repository Agent | 代码知识源 | 无（可并行） | 新建 `research/code_agent/`，复用 `rag/` |
| Day 5 | Embodied AI Knowledge Graph | 知识图谱 | Day 4 | 新建 `knowledge_graph/`，连接 Paper/Code/Skill/Robot |
| Day 6 | Research Agent 研究闭环 | 研究助手 | Day 1-5 | 升级 `agents/research/`，模板→LLM 多源检索 |
| Day 7 | Integration 集成验收 | 整合 | Day 1-6 | 端到端 Demo + 文档 |

### 1.4 能力跃升对照

| 能力 | Week 1（现状） | Week 2（目标） |
|---|---|---|
| LangGraph | ★★★★★（7 套流程） | ★★★★★（+LLM 路由 +研究闭环） |
| RAG | ★★★★★（Paper 单源） | ★★★★★（Paper + Code 双源） |
| LLM 驱动 | ☆（仅预留接口） | ★★★★★（Provider 层 + Prompt 系统） |
| Knowledge Graph | ☆（无） | ★★★★（实体关系图） |
| Code Agent | ☆（无） | ★★★★（AST 解析 + 代码 RAG） |
| Research Agent | ★★（模板匹配） | ★★★★（多源检索 + 研究闭环） |
| Robot Knowledge | ★（仅论文提及） | ★★★★（KG 实体 + 实验记忆） |

### 1.5 选型依据（基于用户硬件 RTX4060Ti 16GB / 64GB RAM）

- **本地默认**：Ollama + Qwen2.5-7B（16GB 显存可跑，离线可用）
- **API 备选**：DeepSeek（性价比）/ Qwen（阿里云）/ Kimi（长上下文）/ Claude（推理强）
- **统一协议**：OpenAI Compatible API（DeepSeek/Qwen/Kimi 均兼容，Claude 走适配层）
- **零依赖兜底**：MockClient（返回固定模板，参照 HashEmbedder 模式，确保 CI 无 LLM 也能跑）

---

## 二、Day 1：LLM Provider Layer

### 2.1 开发任务

**目标**：建立统一 LLM 服务层，解决当前 Agent 最大问题——规则驱动 → LLM 驱动。不绑定单一模型，支持多 Provider 切换。

**当前问题**：无统一 LLM 层，`planner/generators/llm_generator.py` 直接抛 NotImplementedError，4 处"Week 2 接 LLM"锚点无法落地。

**改造方案**：参照 `rag/embedder.py` 的抽象 + 多实现 + 工厂 fallback 模式：
- 统一基于 OpenAI Compatible 协议（DeepSeek/Qwen/Kimi 原生兼容，Claude 走适配）
- `LLMClient` 抽象：`chat(prompt) → str` / `chat_json(prompt, schema) → dict`
- `MockClient` 零依赖兜底（延续 HashEmbedder 哲学）

### 2.2 技术学习任务

**LLM Application Architecture**：
- Provider abstraction（统一接口屏蔽底层差异）
- Prompt template（Day 2 专题）
- Streaming（流式输出，先支持非流式，预留 stream 接口）
- Function calling（Day 3 Supervisor 路由用，先预留 schema）

理解分层：`Application → LLM Client → Model Provider`

### 2.3 文件变化

```
backend/app/llm/                      # 新增模块
├── __init__.py                       # 聚合导出 get_llm
├── client.py                         # LLMClient 抽象基类 + ChatMessage
├── provider.py                       # OpenAICompatibleClient（基类）+ 各 Provider 子类
│                                     #   - OllamaClient（本地）
│                                     #   - DeepSeekClient / QwenClient / KimiClient（API）
│                                     #   - ClaudeClient（适配层）
│                                     #   - MockClient（兜底）
├── config.py                         # LLMConfig（provider/model/api_key/base_url）
├── models.py                         # 请求/响应 dataclass
└── factory.py                        # get_llm() 工厂 + 健康检查 + fallback

backend/config/llm.yaml               # 新增：Provider 配置（不硬编码 key）
backend/tests/test_llm_provider.py    # 新增测试
```

### 2.4 Trae / Claude Code Prompt

```
项目：Embodied AI Career OS
目标：实现统一 LLM Provider Layer。
要求：
  - 支持 OpenAI Compatible 接口，不绑定单一模型
  - 支持 qwen / kimi / deepseek / ollama / claude / mock
  - 参照 rag/embedder.py 的抽象+工厂+fallback 模式
  - 配置走 config/llm.yaml，api_key 从环境变量读，不硬编码
先输出：架构设计、接口定义、文件变化。等待确认后编码。
```

### 2.5 验收标准

```python
from app.llm import get_llm

# 基础对话
llm = get_llm()                       # 按 LLM_PROVIDER 环境变量选择
print(llm.chat("解释 ACT 论文"))      # 返回模型回答

# 切换 Provider（环境变量或配置）
# LLM_PROVIDER=deepseek / qwen / kimi / ollama / mock

# Mock 兜底（无 API key 时自动 fallback）
# LLM_PROVIDER=mock python -c "..."   → 返回固定模板，不报错

# 结构化输出
result = llm.chat_json("摘要这段论文", {"title": "str", "method": "str"})
# → {"title": "...", "method": "..."}
```

**可行性分析**：当前环境无外网，Day 1 主要验证 MockClient + 接口契约；Ollama/DeepSeek 等 API 客户端代码就绪，真实连通在用户提供 key/本地模型后即用。

---

## 三、Day 2：Prompt Engineering System

### 3.1 开发任务

**目标**：从"代码里写 prompt"升级为 Prompt Registry（模板 + 版本 + 变量注入）。

**当前问题**：prompt 散落在各 `nodes.py` 内嵌字符串，无法统一管理、版本追溯、A/B 测试。

**改造方案**：
- YAML 模板文件按 Agent 维度组织，含 `system` + `user_template`（`str.format` 占位）
- `PromptManager` 加载 YAML，支持版本字段 + 变量注入 + 按名加载
- 保持简单：纯函数渲染，无副作用

### 3.2 技术学习任务

- System Prompt 设计（角色设定 + 约束 + 输出格式）
- Chain of Thought 控制（引导推理过程）
- Structured Output（JSON mode / schema 约束 + 容错解析）

### 3.3 文件变化

```
backend/app/prompts/                  # 新增
├── __init__.py
├── prompt_manager.py                 # PromptManager（加载/渲染/版本）
├── planner.yaml                      # 任务生成 prompt
├── reviewer.yaml                     # 评估 prompt
├── research.yaml                     # 研究闭环 prompt（Day 6 用）
├── paper.yaml                        # 论文摘要/问答 prompt
├── code.yaml                         # 代码分析 prompt（Day 4 用）
└── supervisor.yaml                   # 意图路由 prompt（Day 3 用）

backend/tests/test_prompts.py         # 新增测试
```

### 3.4 Trae / Claude Code Prompt

```
设计 Prompt Management 系统。
要求：
  - 支持：版本管理（version 字段）、变量注入（str.format）、Agent 调用
  - YAML 模板按 Agent 维度组织
  - 保持简单，纯函数渲染
覆盖场景：planner / reviewer / research / paper / code / supervisor
```

### 3.5 验收标准

```python
from app.prompts import PromptManager

pm = PromptManager()
prompt = pm.load("research_agent")              # 返回完整 prompt（system + user）
assert prompt.version                            # 含版本字段
msg = pm.render("paper_qa", question="ACT方法", context="...")  # 变量注入
assert "ACT方法" in msg
```

---

## 四、Day 3：Supervisor Agent 升级

### 4.1 开发任务

**目标**：将 Supervisor 从"固定 router"升级为"LLM 判断 → 选择 Agent"。

**当前状态**：`agents/supervisor/nodes.py` 用关键词匹配做意图路由（4 个固定意图），无法处理复合问题。

**升级方案**：
- LLM 分析用户问题 → 输出需要的 Agent 列表 + 选择原因
- 保留规则路由作 fallback（`auto_llm=False` 或 LLM 异常时回退，延续 `auto_index` 模式）

### 4.2 Agent 选择逻辑示例

```
输入：SO101 ACT 训练失败
LLM 判断 → 需要：
  - Paper Agent（查 ACT 论文方法）
  - Code Agent（查 LeRobot ACT 实现）
  - Research Agent（综合建议）
选择原因：问题涉及论文方法 + 代码实现 + 故障排查
```

### 4.3 技术学习任务

- Agent routing（LLM 作为路由器）
- Tool calling / Function calling（Agent 即工具，输出结构化调用列表）
- Function schema（定义可用 Agent 的描述）

### 4.4 文件变化

```
backend/app/agents/supervisor/        # 修改
├── router.py                         # 新增：LLM 路由（原 nodes.py 的规则抽离）
├── decision.py                       # 新增：决策数据结构（Agent 选择 + 原因）
├── tools.py                          # 新增：Agent 工具描述（供 LLM function calling）
├── nodes.py                          # 修改：调用 router，规则作 fallback
└── state.py                          # 修改：增 selected_agents + reasoning

backend/app/agents/agent_tools/       # 新增：Agent 工具描述聚合
└── __init__.py                       # 各 Agent 的 name/description/when_to_use

backend/tests/test_supervisor_llm.py  # 新增
```

### 4.5 Trae / Claude Code Prompt

```
升级 Supervisor Agent。
要求：
  - 根据用户问题动态选择 Agent（LLM 判断）
  - 输出：选择原因 + 调用 Agent 列表
  - auto_llm=False 或 LLM 异常时回退规则路由
  - 复用 Day 1 get_llm + Day 2 supervisor.yaml prompt
```

### 4.6 验收标准

```
输入：ACT泛化不好怎么办？
输出：
  调用：Paper Agent, Code Agent, Research Agent
  原因：涉及论文方法 + 代码实现 + 优化建议
```

**可行性分析**：Mock LLM 下回退规则路由，确保现有 Phase 2 测试（test_phase2_week1.py 的 4 意图路由）全绿不受影响。

---

## 五、Day 4：Code Repository Agent

### 5.1 开发任务

**目标**：让 AI 理解机器人代码，重点覆盖 LeRobot / IsaacLab / ROS2 packages。

**当前状态**：`research/` 下仅 `paper_agent/`，无代码知识源。

**改造方案**：参照 Paper Agent 模式，复用 `rag/` 基础设施：
- Repository → File Parser（AST 解析）→ Code Chunk（带 symbol 元数据）→ Embedding → Search
- Python 用 `ast` 模块按函数/类切分；其他语言按签名正则兜底

### 5.2 技术学习任务

- Code RAG（代码语义嵌入 vs 纯文本嵌入）
- AST parsing（Python `ast` 模块：FunctionDef / ClassDef / docstring）
- Repository indexing（目录结构 + 模块依赖）

### 5.3 文件变化

```
backend/app/research/code_agent/      # 新增（参照 paper_agent 模式）
├── __init__.py
├── parser.py                         # 代码解析：.py(ast) / .js/.ts(正则) / 其他(纯文本)
├── chunker.py                        # 代码分块：函数/类级，带 symbol/symbol_type/line_range
├── indexer.py                        # 复用 rag.embedder + vector_store，source_type=code
├── retriever.py                      # 代码检索：query → top-k code chunks
├── analyzer.py                       # 代码分析：项目结构/核心模块/调用关系
└── schema.py                         # CodeMeta / CodeChunk 数据契约

backend/app/models/code_repo.py       # 新增 ORM（CodeRepo + CodeChunk）
backend/migrations/0004_code_repos.sql # 新增
backend/app/api/code_repo.py          # 新增 API（ingest/index/search/analyze）
backend/tests/test_code_agent.py      # 新增
```

### 5.4 Trae / Claude Code Prompt

```
实现 Code Repository Agent。
输入：Github repo（或本地仓库路径）
输出：项目结构 + 核心模块 + 调用关系
要求：
  - Python 优先用 ast 模块按函数/类分块
  - 复用 rag/embedder + rag/vector_store，不重复造轮子
  - vector_store 增 source_type 区分 paper/code
  - 失败降级为纯文本分块
```

### 5.5 验收标准

```
输入：分析 LeRobot 目录结构
输出：
  dataset
  policy
  training
  environment
```

**可行性分析**：Github repo 需本地预置或 clone。当前沙箱无外网，Day 4 用预置的 LeRobot/IsaacLab 代码样本（精简版）验证；真实 clone 在用户提供网络环境后即用。`analyzer.py` 的"调用关系"分析为简化版（import 关系 + 函数定义统计），深度调用图留待后续。

---

## 六、Day 5：Embodied AI Knowledge Graph

### 6.1 开发任务

**目标**：把 Paper、Code、Skill、Robot 连接起来，形成具身智能领域知识图谱。

**当前状态**：Phase 1 有 Skill Graph（`skill.py`，level 0-5），Phase 3 有 Paper/Code，但彼此孤立，无关系连接。

**改造方案**：新建 `knowledge_graph/` 模块，定义实体 + 关系，构建图谱，支持关联查询。

### 6.2 实体与关系设计

```
实体：Paper / Algorithm / Code / Robot / Skill

关系：
  Paper --implements--> Algorithm
  Algorithm --uses--> Skill
  Code --implements--> Algorithm
  Code --runs_on--> Robot
  Skill --requires--> Skill（前置依赖）
```

### 6.3 技术学习任务

- Knowledge Graph 基础（实体 / 关系 / 属性）
- Entity Relation Extraction（从 Paper/Code 自动抽取关系）
- 图查询（多跳关联：Paper → Algorithm → Skill）

### 6.4 文件变化

```
backend/app/knowledge_graph/          # 新增
├── __init__.py
├── entity.py                         # 实体定义（Paper/Algorithm/Code/Robot/Skill）
├── relation.py                       # 关系定义（implements/uses/runs_on/requires）
├── graph_builder.py                  # 图谱构建（从现有 Paper/Code/Skill 数据抽取实体关系）
├── query.py                          # 图查询（多跳关联：ACT需要哪些技能）

backend/app/models/knowledge_edge.py  # 新增 ORM（实体关系边表）
backend/migrations/0005_knowledge_graph.sql
backend/tests/test_knowledge_graph.py # 新增
```

### 6.5 Trae / Claude Code Prompt

```
设计 Embodied AI Knowledge Graph。
实体：Paper / Algorithm / Code / Robot / Skill
关系：uses / requires / implements / runs_on
要求：
  - 从现有 Paper/Code/Skill 数据自动抽取实体关系（graph_builder）
  - 支持多跳查询（query：ACT → Algorithm → Skill）
  - 复用现有 ORM（Paper/Skill），新增关系边表
```

### 6.6 验收标准

```
查询：ACT 需要哪些技能？
返回：
  Transformer
  PyTorch
  Dataset
  LeRobot
  Robot Control
```

**可行性分析**：实体关系初期用规则抽取（Paper.method 含关键词 → 关联 Algorithm/Skill），LLM 抽取作增强（Day 1 LLM 就绪后）。Robot 实体本周为静态预置（SO101/LeRobot），真实机器人控制留待 Phase 4。

---

## 七、Day 6：Research Agent 研究闭环

### 7.1 开发任务

**目标**：形成科研助手，结合 Paper + Code + Experiment 生成研究建议。

**当前状态**：`agents/research/` 是模板匹配（4 个固定主题），不联网、不检索、无 LLM。

**升级方案**：升级为 ReAct 模式研究闭环：
```
搜索论文（Paper RAG）→ 分析代码（Code RAG）→ 读取实验记录 → 生成方案
```

### 7.2 工作流

```
输入：我要优化 SO101 ACT 泛化

Research Agent：
  1. 搜索论文 → ACT 原始方法 + 泛化相关论文
  2. 分析代码 → LeRobot ACT 实现的关键模块
  3. 读取实验记录 → 历史训练参数与结果
  4. 生成方案 → 论文依据 + 代码建议 + 实验建议
```

### 7.3 技术学习任务

- Research Agent 模式（多步检索 + 综合）
- ReAct Pattern（Reason + Act 循环）
- Agent Memory（实验记录的上下文记忆）

### 7.4 文件变化

```
backend/app/agents/research/          # 升级现有
├── graph.py                          # 修改：retrieve_papers → analyze_code → read_experiments → synthesize_answer
├── planner.py                        # 新增：研究步骤规划（LLM 决定检索策略）
├── answer.py                         # 新增：多源综合答案生成（LLM）
├── nodes.py                          # 修改：各节点接 RAG/KG/实验记录
├── state.py                          # 修改：增 papers/code/experiments/synthesis
└── templates.py                      # 保留：规则 fallback

backend/tests/test_research_agent.py  # 新增
```

### 7.5 Trae / Claude Code Prompt

```
实现 Research Agent（研究闭环）。
要求：
  - 结合 Paper RAG + Code RAG + Knowledge Graph + 实验记录
  - LLM 驱动（Day 1）+ research.yaml prompt（Day 2）
  - 生成：论文依据 + 代码建议 + 实验建议
  - auto_llm=False 回退模板模式（向后兼容 Phase 2 测试）
```

### 7.6 验收标准

```
问题：ACT 为什么泛化差？
回答包含：
  - 论文依据：ACT 的 CVAE 假设单模态，多模态数据泛化受限
  - 代码建议：检查 LeRobot ACT 实现的 chunk_size 参数
  - 实验建议：尝试 Diffusion Policy 对比，记录 success_rate
```

**可行性分析**：实验记录本周复用 Phase 1 的 `learning_log`（含 artifact_url）作实验记忆，真正的 Experiment Memory 系统（MLflow/WandB）留待 Phase 3 Week 3。Day 6 依赖 Day 1-5 全部就绪，是 Week 2 最复杂的一天。

---

## 八、Day 7：Phase 3 Week 2 Integration

### 8.1 开发任务

**目标**：形成 Embodied AI Research Copilot，端到端集成验收。

### 8.2 最终架构

```
                 User
                  │
            Supervisor Agent          ← Day 3
                  │
 ┌────────────────┼──────────────────────────┐
 ▼                ▼                          ▼
Paper Agent   Code Agent               Research Agent    ← Day 4/6
(Week1)       (Day 4)                  (Day 6)
                  │
          ┌───────┴────────┐
          ▼                ▼
    Knowledge Graph    Vector DB        ← Day 5
    (Paper/Code/       (Paper+Code
     Skill/Robot)       统一检索)
```

### 8.3 文件变化

```
backend/docs/
├── phase3-week2-summary.md           # 新增：Week 2 成果总结
└── architecture-v2.md                # 新增：升级后架构文档

backend/tests/
└── research_agent_test.py            # 新增：端到端研究闭环测试

backend/app/api/
└── research.py                       # 新增：POST /api/research/ask 研究助手入口
```

### 8.4 验收 Demo

**Case 1：故障排查闭环**
```
用户：SO101 ACT 训练失败
系统自动：
  Paper Agent → ACT 论文方法回顾
  Code Agent → LeRobot ACT 实现检查
  Experiment Memory → 历史训练记录
  → 优化建议（参数调整 + 备选方案）
```

**Case 2：职业路线规划**
```
用户：如何成为 Robot AI Engineer?
输出结合：
  - 当前 Skill（Skill Graph）
  - Gap（Career Agent）
  - Paper（相关论文）
  - 项目经验（LearningLog）
  → 下一阶段路线
```

### 8.5 能力提升总结

| 能力 | 状态 |
|---|---|
| LangGraph | ★★★★★ |
| RAG | ★★★★★ |
| Knowledge Graph | ★★★★ |
| Code Agent | ★★★★ |
| Research Agent | ★★★★ |
| Robot Knowledge | ★★★★ |

---

## 九、可行性分析与风险控制

### 9.1 环境约束应对

| 约束 | 影响 | 应对 |
|---|---|---|
| 沙箱无外网 | 无法调真实 LLM API / clone Github | MockClient 兜底 + 预置代码样本，真实连通待用户环境 |
| 无 GPU | 无法跑本地大模型 | Ollama 代码就绪，MockClient 保证流程可测 |
| 无 sentence-transformers | 代码 RAG 嵌入 | 沿用 HashEmbedder（Week 1 已验证） |

### 9.2 向后兼容策略

- **每处 LLM 替换都有规则 fallback**（`auto_llm=False`），延续 Week 1 `auto_index` 模式
- **Supervisor 升级不破坏 Phase 2 测试**：4 意图规则路由保留，LLM 路由作增强
- **Research Agent 升级保留模板模式**：`agents/research/templates.py` 不删，作 fallback
- **Week 1 的 63 个测试用例必须全绿**：每个 Day 完成后跑回归

### 9.3 工作量风险

Day 5（Knowledge Graph）和 Day 6（Research Agent）工作量较大，若 7 天紧张，可：
- Day 5 KG 先实现核心实体关系（Paper↔Algorithm↔Skill），Robot/Code 关系简化
- Day 6 Research Agent 先打通单源（Paper RAG），多源融合（Code + KG）作为增强

---

## 十、后续路线衔接

```
Phase 3 Week 1（已完成）  Paper Knowledge Agent（规则驱动）
Phase 3 Week 2（本周）    Agent Research Engineer（LLM 驱动 + 研究闭环）
Phase 3 Week 3            Autonomous Experiment Engineer
                          （Research Agent → Experiment Agent → Robot Experiment OS）
                          加入：MLflow / WandB / LeRobot dataset tracking /
                                Isaac Lab experiment / 自动实验报告
Phase 4                   Robot Experiment OS
                          真正连接：SO101 + ROS2 + Isaac Lab + LeRobot + Career OS
```

Week 2 的 LLM 基础设施 + Knowledge Graph + Research Agent 是 Phase 3 Week 3 "Autonomous Experiment Engineer" 的前置——实验 Agent 的决策依赖 LLM 推理与知识图谱关联。Week 2 完成后，系统从"Agent 应用开发"迈向"具身智能工程师"的关键转折点，之后进入 Phase 4 真正连接机器人硬件。

---

## 设计原则

1. **基础设施先行**：LLM Provider（Day 1）+ Prompt（Day 2）先于应用层（Day 3-6），避免边改边补基础
2. **图结构不变**：4 处锚点替换仅改节点内部，LangGraph 拓扑与 state 签名不动（Week 1 已预留）
3. **零依赖兜底**：MockClient 确保 CI/无 GPU 环境全流程可测（延续 HashEmbedder 哲学）
4. **复用优先**：Code Agent 复用 `rag/`，Knowledge Graph 复用现有 Paper/Skill ORM，不重复造轮子
5. **向后兼容**：每处 LLM 替换都有 `auto_llm=False` 规则回退，Week 1 测试全绿不受影响
6. **渐进式智能化**：先 Mock 验证流程 → 再接 Ollama 验证语义 → 最后生产 API，每层独立可测
7. **研究闭环导向**：所有 Day 的产出最终服务于 Day 6 Research Agent 的"论文+代码+实验→建议"闭环
