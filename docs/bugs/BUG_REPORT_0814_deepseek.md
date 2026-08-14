# Embodied AI Career OS 代码审查报告

- **日期**：2026-08-14
- **审查方式**：只读静态分析（未修改任何代码）
- **覆盖范围**：backend（models / schemas / api / agents / llm / research / services）、frontend（pages / components / services / types）、部署配置（docker-compose / Dockerfile / start.sh）、数据库脚本
- **验证手段**：
  - 5 路并行深度审查 + 前后端契约交叉核对
  - 实测运行后端测试套件：**112 个 pytest 全部通过**（3 分 16 秒，453 个弃用警告）——注：该"全绿"具环境敏感性：下文中等级 #7（`db/base.py:85` 仅处理 `sqlite:///./` 一种前缀）会使 `test_paper_rag_e2e.py` 的 `test_vector_store`（其 `DATABASE_URL=sqlite:///D:/...` 绝对路径）在部分环境/收集顺序下失败；复审复现为 **111 通过 + 1 失败**，故"112 全绿"不可稳定复现。
  - 实测 LangGraph **1.2.1** 运行时行为（本机安装版本，`requirements.txt` 只写 `>=0.2.0`）

---

## 结论摘要

| 严重度 | 数量 | 关键领域 |
|---|---|---|
| 🔴 严重 | 6 | 凭据泄露、Docker 部署不可用、GitHub 数据丢失、主流程返回错误数据、调度器生命周期 |
| 🟡 中等 | ~28 | State schema 契约、LLM 路径健壮性、前端契约/错误处理、RAG 数据质量 |
| 🟢 轻微 | 25+ | 弃用 API、依赖未钉版本、死配置、资源未关闭、提示词细节 |

**总体评价**：项目架构清晰（BaseAgent + Registry + Executor + 线性 LangGraph 子图），主链路**可用**（112 测试全绿、前后端 API 契约一致），但存在 1 个已泄露的凭据、1 个使 Docker 部署完全不可用的配置缺口、1 条会静默丢失数据的 GitHub 链路，以及一批被 LangGraph 静默语义掩盖的 State 契约问题。

---

## ⚠️ 核心系统性隐患：LangGraph 1.2.1 对"多余 key"静默丢弃（实测）

> 本机 `langgraph 1.2.1`（requirements 为 `>=0.2.0`，无上界）实测行为：
> - 输入 state 中**不在 State TypedDict 的 key** → 静默丢弃（仅 `logger.warning`），不报错；
> - 节点返回 dict 中**未声明的 key** → 按 schema channels 静默过滤，数据丢失，不报错。
>
> 因此本项目所有"State schema 与输入/返回不一致"的缺陷，全部以**静默数据丢失 / 功能失效**呈现——比直接报错更难排查；若未来升级 langgraph 或加 `strict=True`，会从"丢数据"升级为"报错"。

由此衍生的问题（详见中等 M1/L1/L2 与附注 S1）：

| # | 位置 | 问题 |
|---|---|---|
| S1 | `api/paper.py:284-290` + `agents/knowledge/state.py:14-33` | `/api/paper/ask` 注入的 `db` 不在 `KnowledgeState` schema 中 → 被静默丢弃 → `retrieve_node`（nodes.py:45）恒走 `db is None` 分支，**每次请求额外自建 `SessionLocal()`**，事务复用设计失效（`agents/knowledge/agent.py:24-27` 已定义含 `db` 的 `_KnowledgeAgentState` 却未被 `build_knowledge_graph` 使用） |
| M1 | `agents/career/nodes.py:75-78`、`agents/reviewer/nodes.py:71` | 节点返回 `llm_market_insights` / `llm_priority` / `llm_evaluation` 未在 State 声明 → 这些**额外洞察字段静默丢失**（核心 LLM 输出 `required_skills`/`evidence_score` 已在 State 声明、仍生效，故结果非"比规则版更少"，而是"LLM 附加信息被丢弃"） |
| L1 | `agents/core/state.py:18-29` + `agents/core/executor.py:68-72` | 实际驱动的 `CareerState`/`ReviewerState`/`PlannerState`/`KnowledgeState` 均未继承 `AgentState` → Executor 注入的 `agent_name`/`trace_id` 在这些路径被丢弃（注：`PaperAgentState` 与 `_KnowledgeAgentState` 确实继承了 `AgentState`，但后者未被 `build_knowledge_graph` 使用、前者不走 Executor 注入路径）→ `AgentState` 在核心链路是事实上的死代码（`_record` 用的是 enriched_input，tracing 记录仍完整，故无功能破坏） |
| L2 | `agents/orchestrator/workflow.py:178-183` | planner 默认输入 `"persist": False` 是 state key 而非 executor 参数 → 被丢弃，planner 经 orchestrator 仍会写 agent_runs，与"不写"意图矛盾 |

---

## 🔴 严重级 BUG（6 项）

### 1. ServerChan 密钥明文提交到 Git 仓库（安全泄露）
- **位置**：`docker-compose.yml:37`（`REMINDER_CHANNEL_KEY=SCT394127...`，`git ls-files` 已确认该文件被跟踪）
- **问题**：微信推送通道 SendKey 随仓库公开，任何人可冒用推送。
- **修复**：改为 `${REMINDER_CHANNEL_KEY:-}` 引用 + `.env` 注入，并立即在 Server酱后台重置该 key。

### 2. Docker Compose 部署下前端必然连不上后端（主部署路径不可用）
- **位置**：`docker-compose.yml:51-52`、`frontend/next.config.ts:22`、`frontend/src/lib/apiClient.ts:39`
- **问题**：
  - compose 给 frontend 只设了 `NEXT_PUBLIC_API_URL=http://localhost:8000`，但**全项目无任何代码读取该变量**；
  - `/api` rewrites 代理与 Server Component 端 fetch 都读 `BACKEND_URL`（默认 `http://localhost:8000`），compose **未设置**；
  - 容器内 `localhost:8000` 指向 frontend 容器自身 → 浏览器端 `/api/*` 与 SSR 数据获取全部失败 → README 主推的 `docker compose up` 部署下 Dashboard 必然显示"后端连接失败"。
- **修复**：compose frontend environment 增加 `BACKEND_URL=http://backend:8000`（或 rewrites 目标改为 `http://backend:8000`）。

### 3. GitHub 同步链路三重致命问题叠加 → 提交被永久漏同步（数据丢失）
- **位置**：`services/github/client.py:37,69`（owner 硬编码 `prideandprejudice`）、`client.py:62,75`（`except Exception: pass` 吞掉所有错误且无日志）、`services/github/sync.py:60`（循环结束**无条件** `_save_last_sync(datetime.utcnow())`）
- **问题**：owner 硬编码（`prideandprejudice`，恰为作者本人 GitHub 用户名，**非必然 404**，但无法配置化/支持 `owner/repo`）；任何失败（401/403/429/网络异常）都被 `except Exception: pass` 静默吞掉且无日志；随后水位被**无条件**推进到当前时刻 → 失败窗口内的 commit **永久跳过**，且无任何失败标志。
- **修复**：owner 纳入配置（或支持 `owner/repo`）；区分 401/403/429 并记录日志；**仅在至少一个 repo 成功拉取时才推进水位**。

### 4. GitHub commit 建议无去重 → 重复插入
- **位置**：`services/github/sync.py:50-58` + `services/github/store.py:12-33` + `models/commit_suggestion.py:20`
- **问题**：`save_suggestion` 不检查 `commit_sha` 是否已存在，表无唯一约束；定时 job（30 分钟）+ 手动 `POST /api/github/sync` 并发时重复更严重（水位文件丢失则全量重拉，重复爆炸）。
- **修复**：按 `commit_sha` 查重/upsert，并加数据库唯一约束。

### 5. Reviewer 评估返回"全局最新"记录而非本次任务的（主流程返回错误数据）
- **位置**：`api/reviewer.py:102-109,115`；关联 `agents/reviewer/nodes.py:168`（无匹配技能时跳过写 SkillAssessment）
- **问题**：
  - 查询 `SkillAssessment` **不按 `task_id` 过滤** → 并发/多次复盘时返回**别的任务**的评估（`old_level/new_level/reason` 全错）；
  - 任务 `skill_name` 在 skills 表匹配不到时节点不写评估；若全表无记录，`SkillAssessmentOut.model_validate(None)` → **Pydantic ValidationError → 500**。
- **修复**：按 `SkillAssessment.task_id == req.task_id` 过滤；`assessment is None` 时显式兜底（404/422 或内存构造）。

### 6. 提醒调度器只启不停、可重复启动（双份推送 + 线程泄漏）
- **位置**：`services/reminder/scheduler.py:12,61`、`app/main.py:47-48`
- **问题**：模块文档自称"shutdown 时自动停止"但**没有 stop 函数**；lifespan 只调用 `start_scheduler()`，`yield` 后无清理；重复调用 `start_scheduler()`（热重载/测试）会替换全局 `_scheduler` 而旧调度器仍在跑 → 早/晚/回归推送**双份触发**。
- **修复**：补 `stop_scheduler()` + lifespan `finally` 调用 + `start_scheduler()` 幂等保护。

---

## 🟡 中等级 BUG（按模块）

### Agents / LLM

| # | 位置 | 问题 |
|---|---|---|
| S2 | `agents/career/nodes.py:72-74` | `list(set(llm_result["required_skills"]) \| set(fallback_skills))`：LLM 返回含不可哈希元素（嵌套 list/dict）时 `TypeError` 打穿节点（在 `_analyze_with_llm` 的 try/except **之外**），orchestrator 标记 failed、直调 500；且 `set` 并集**打乱优先级顺序**。修复：过滤 str 元素 + `dict.fromkeys` 保序 |
| S3 | `api/agent.py:90-103` + `agents/orchestrator/workflow.py:51-53,201` | `Depends(get_db)` 拿到的 `db` **从未传给 `run_workflow`**（死依赖）→ `OrchestratorExecutor(db=None)` → reviewer 经 `/api/agent/run` 永远内存模式：**SkillAssessment / Skill / AgentRun 全部不落库**，注释承诺的注入未实现。修复：`run_workflow`/`AgentWorkflow` 增加 `db` 参数并透传 |
| M2 | `agents/career/nodes.py:30` | 提示词用 `s.get('target_level', 5)`，但 `SkillStatus`（state.py:14-19）字段是 `target` → **LLM 看到的每个技能目标等级恒为 5**，缺口分析基于错误数据；`s.get('evidence', [])` 同理恒为 [] |
| M3 | `app/llm/factory.py:37-42,54-65` | fallback 出的 MockClient 被**缓存固化** → 启动时 provider 配置错误，整个进程生命周期都用 mock，之后补环境变量不生效（需重启） |
| M4 | `agents/planner/generators/llm_generator.py:103-104` | few-shot 示例把 Python 列表字面量（单引号 `['a','b']`）嵌进"JSON 示例"（非法 JSON）→ 诱导模型输出坏格式；且 `_validate_and_fill`（113-133）**不检查 `_parse_error`** → LLM 模式收益归零（静默回退规则） |
| M5 | `agents/core/executor.py:74-90` | `finally` 中 `_record()`（写 agent_runs）异常会**覆盖原始 agent 异常**（成功变失败、失败原因被替换）；`_record` 自身无 try/except |
| M6 | `app/llm/providers.py:156-161` | Ollama 错误提示第二条字符串**非 f-string** → `{self._config.ollama_model}` 原样输出；所有 API 异常统一包装成 `ConnectionError` 且无 `from e`，原始异常丢失 |
| M7 | `agents/reviewer/nodes.py:168-204,236-248` | DB 节点（add/commit/query）无 try/except，DB 故障打穿整个图（直调 500）；`record_agent_run` 内**提前 commit**，与 `api/reviewer.py:56` "全链路失败回滚"注释不符，部分写入残留 |
| — | `agents/orchestrator/workflow.py:106-121` | Supervisor 节点无 try/except → LLM 异常直接穿透成 500，与"失败隔离"设计承诺不符 |

### API / 模型层

| # | 位置 | 问题 |
|---|---|---|
| 1 | `api/career.py:39-44` | upsert **创建路径**只写 `target_role`，静默丢弃 `salary_target/timeframe/notes`（前端首次保存即丢字段） |
| 2 | `api/paper.py:326-343` + `research/paper_agent/comparator.py:90-103` | `/paper/compare` 传入不存在的 paper_id 时 `ValueError` 未捕获 → **500**（应 400/404） |
| 3 | `api/paper.py:65-90` + `research/paper_agent/agent.py:99-179` | `/paper/ingest` 无异常处理（文件不存在/解析失败 → 500）；`persist_node` 已 commit 后 `index_node` 失败 → 500 但论文已入库，重试产生**重复论文**（非幂等） |
| 4 | `api/paper.py:46` + `research/paper_agent/parser.py:27-54` | `file_path` 完全由客户端控制、服务端不校验即读文件 → **服务端任意 .md/.txt/.pdf 文件读取**（安全缺陷） |
| 5 | `api/milestones.py:145-156` | 幂等检查是 check-then-insert → **并发请求重复生成任务** |
| 6 | `api/reviewer.py:64-97` | 写事务（`task.status="done"` + `db.flush()`）持有到图内 commit，期间同步 LLM 调用数秒 → **SQLite 写锁**阻塞其他写请求 |
| 7 | `db/base.py:85` | SQLite 路径仅 `replace("sqlite:///./", "")` 一种前缀；配置 `sqlite:///data/app.db` 时产生垃圾路径，Windows 下 `os.makedirs` → **启动崩溃** |
| 8 | `models/paper_chunk.py:25-27`、`models/paper_chunk_embedding.py:31-33` | 外键无 `ondelete`（全库其他 FK 均配置 CASCADE/SET NULL）→ 未来删除 Paper 会 `IntegrityError`（已开 `PRAGMA foreign_keys=ON`） |
| 9 | `api/dashboard.py:23-28` | 每项目单独查 milestones → N+1 查询 |
| 10 | `api/tasks.py:69-82` | 状态机仅约束取值（`TaskStatusPatch` pattern），**不校验转换合法性**（done→todo 均可） |
| 11 | `api/planner.py:125` | AgentRun `duration_ms` 硬编码 0（该路径无 Executor），`/api/agent/runs` 耗时恒为 0 |

### 前端

| # | 位置 | 问题 |
|---|---|---|
| 1 | `components/ProjectProgress.tsx:58-60` + `services/projectService.ts:77-80` | Dashboard 用 `GET /api/projects`（列表端点**不含 milestones/进度统计**，仅详情端点有）→ `p.milestones.find(...)` 恒 undefined → 项目进度**永远显示"全部完成"** |
| 2 | `app/projects/page.tsx:8`、`app/projects/[id]/page.tsx:15-19` | 无 try/catch：后端不可用 → 整页 500；项目不存在 → 404 被渲染成 500（未调 `notFound()`）；`app/` 下无 `error.tsx`/`not-found.tsx`/`loading.tsx` |
| 3 | `components/TaskCard.tsx:60,75` | `STATUS_CONFIG[task.status]` 对非法状态无兜底 → `config.className` TypeError → **整页渲染崩溃**（后端 status 是自由字符串） |
| 4 | `services/careerService.ts:30-32` + `app/dashboard/page.tsx:37-42` | Career 未配置时后端返回 `success=false` → apiClient 抛 ApiError → 渲染成"**后端连接失败**"（业务未初始化被误报为后端宕机） |
| 5 | `components/MilestoneTimeline.tsx:36-60` | 生成任务/切换状态两个 handler 无 catch、无进行中禁用 → 失败无提示 + 可连点重复请求 |
| 6 | `components/TaskCompleteForm.tsx:62-64` | success 态下按钮重新可用（`isSubmitting` 仅覆盖 submitting），刷新完成前可重复提交 → 重复 LearningLog + 重复 Reviewer 执行 |
| 7 | `components/PendingSuggestions.tsx:11-32` | useEffect 依赖缺 `fetchItems`（eslint 警告）+ 无 AbortController；confirm/reject 无 try/catch、无 loading 态 |

### RAG / 研究 / 服务

| # | 位置 | 问题 |
|---|---|---|
| 1 | `research/paper_agent/chunker.py:91-99` | 小于 `MIN_CHUNK_TOKENS`（50）的段落被**静默丢弃**（注释说"合并到上一 chunk"但未实现）→ RAG 语料丢内容 |
| 2 | `chunker.py:21` | `MAX_TOKENS=800` 远超 all-MiniLM-L6-v2 的 **256 token 截断上限** → chunk 尾部不参与向量化，检索质量系统性下降；中文用 `len//4` 估算偏差更大 |
| 3 | `chunker.py:94-108` | 同 section 所有段落共用 section 起始 `char_offset` → **页码估算失真**（声明的 `char_cursor` 从未使用） |
| 4 | `rag/retriever.py:98-102` | `search_by_paper` 先全局取 top_k*2 再按 paper_id 过滤 → 目标论文最佳 chunk 可能被截掉（召回缺失） |
| 5 | `rag/indexer.py:83-95` + `research/paper_agent/agent.py:164-179` | `build_index` 无异常处理：中途失败不回滚，注入的共享 session 留下"事务已中止"状态 |
| 6 | `services/reminder/channels.py:43-57` | ServerChan 只检查 HTTP 不抛异常就返回 True，**不校验响应体 `errno`**（每日 5 条额度用尽时假成功）；`resp` 未 close |
| 7 | `services/reminder/engine.py:35-52` | 早/晚推送取"最新任务"而非"今日任务"（无日期过滤）；`current_level=1, target_level=4` **硬编码**，忽略 Skill 表真实等级 |
| 8 | `engine.py:82-97` | `send_comeback` 无"已提醒"状态 → 中断超 3 天后**每天重复推送** |
| 9 | `scheduler.py:36` + `engine.py:95` | cron 按 Asia/Shanghai 触发，`days` 用 naive UTC 计算 → 实际"3 天 + 8 小时"才触发，时区语义混用 |
| 10 | `services/github/sync.py:18-35` + `core/config.py:59` | `.github_last_sync` 水位文件为**相对路径**，依赖 cwd（本地与 Docker 不同）→ 路径一换水位"丢失"→ 全量重拉 + 重复建议 |
| 11 | `services/github/client.py:37,39` | 无分页（`per_page=10` 只拉第一页，窗口内 >10 条 commit 静默漏掉）；`since.isoformat()` 无 `Z` 时区后缀 |
| 12 | `research/paper_agent/comparator.py:150,197` | 以论文 **title 作 dict key** → 重名论文被合并丢失（对比矩阵/项目关联缺失） |
| 13 | `research/paper_agent/summarizer.py:216-217,259` | relation 无命中时返回 17 字默认文案 → `_assess_confidence` 计数恒 +1 → **置信度系统性虚高**（low 被标 medium） |
| 14 | `rag/embedder.py:133-143` | `_ensure_model` 检查-再赋值非原子 → 并发首次 embed 重复加载数 GB 大模型 |

---

## 🟢 轻微级（概述）

- **`datetime.utcnow` 弃用**：全部 13 个模型 + `reminder/engine.py:95`、`github/store.py:71`、`github/sync.py:60`、`tools/context.py:44` 等 20+ 处（Python 3.12+ 已弃用，3.14 将移除；当前 naive UTC 用法内部一致，无功能性错误，属维护性隐患）。
- **依赖未钉版本**：`requirements.txt` 写 `langgraph>=0.2.0` 但实际解析到 **1.2.1**（大版本跳跃，未来安装行为不可复现）；未显式声明 `pydantic`（schema 全依赖 v2 语法，建议钉 `pydantic>=2.0`）。
- **死配置**：compose 设 `RELOAD=true` 但 `settings.reload` 无任何代码消费（Docker 内热重载从未生效）；`github_last_sync_file` 未从 env 读取。
- **`start.sh:25`**：`taskkill //f //im python.exe` 可能误杀无关 Python 进程。
- **Supervisor 单字误匹配**：`agents/supervisor/nodes.py:41` 关键词 `"学"` 使"数学"等词被误判为 learn 意图。
- **Planner 负 gap**：`agents/planner/nodes.py:24` 允许负 gap，全部技能超标时 `select_learning_target` 选中已掌握技能（建议 `max(gap, 0)`）。
- **Reviewer 摘要恒 `?→?`**：`api/agent.py:201-205` `_extract_summary` 从输出顶层取 `old_level/new_level`，实际嵌套在 `assessment` 里 → Dashboard 显示 `level ?→?`。
- **知识库死分支**：`agents/knowledge/nodes.py:144-151` 的 `else: confidence="low"` 不可达（`not chunks` 已提前 return）。
- **注册幂等非原子**：`agents/registry_setup.py:45-48` check-then-register TOCTOU，多线程并发调用可能抛 ValueError（当前启动期单线程，风险低）。
- **Reviewer 硬编码特判**：`orchestrator/executor.py:67-68` 按 agent 名硬编码 `persist=False`，未来新增内部写库 agent 需扩展。
- **`tools/prompts.py:15-83`**：`generate_tool_prompt` 仅接受 ORM 对象（传 dict 会 AttributeError；当前调用方均传 ORM，无实际风险）。
- **资源未关闭**：`github/client.py:43-44,72-73`、`reminder/channels.py:54` urlopen 响应未 close；`parser.py:70` `PdfReader(str(path))` 文件句柄未显式关闭。
- **向量维度混入**：`rag/vector_store.py:206-219` 维度不匹配静默给 0 分，search 不按 dim 过滤，可能占据 top_k 尾部。
- **章节正则局限**：`chunker.py:29-36` 要求标题独占一行，`"Abstract: ..."` 同行格式不识别 → 整段归 unknown。
- **配置校验缺失**：`scheduler.py:68-71` `_parse_time` 无格式校验（非法值启动崩溃）；`github_poll_interval_minutes<=0` 使 APScheduler 启动抛错。
- **前端细节**：`lang="en"` 应为 `zh-CN`（layout.tsx:27）；子列表索引 key（SkillCard/TaskCard/MilestoneTimeline/PendingSuggestions）；`apiClient` 无超时/未解析 422 detail/非 JSON 响应 `res.json()` 抛错无兜底；Server 端 fetch 未显式 `no-store`（靠各页 `force-dynamic` 兜底）；`GenerateTaskButton` 的 `targetRole` 硬编码；`SkillOverview` 缺口计算用 `radarSkills` 子集（可能漏掉最大缺口）。
- **测试脚本问题**：`test_e2e_*.py`、`test_agent_closure.py` 等硬编码 Linux 路径 `/workspace/...` 且依赖真实后端（`BACKEND_URL`），Windows 下被 pytest 误收集为脚本（`TestResult` 类收集警告）。

---

## ✅ 专项核查无问题

- **前后端 API 契约**：13 个路由的路径/方法/请求字段与前端 services 调用**逐一核对完全一致**；snake_case↔camelCase 映射统一正确。
- **LangGraph 图结构**：全部 8 个图为线性链，**无条件边、无循环、无 State 类型冲突**；节点均返回 dict 且有默认值兜底，无必现 KeyError/AttributeError。
- **LLM JSON 容错**：`llm/client.py:60-74` 已处理 markdown 代码块 + 最外层花括号提取 + `_parse_error` 标记（career/supervisor 两处未检查 `_parse_error` 属隐患，当前因 `get()` 语义恰好安全）。
- **数据库会话**：`get_db` / `store.py` / `tools/context.py` 等均 `finally: db.close()`，未发现会话泄漏；SQLite 已正确配置 `check_same_thread=False` + `PRAGMA foreign_keys=ON`。
- **模型与 schema**：字段逐一比对一致（含 JSON 字段 None 处理校验器）；`default=`/`onupdate=` 均为函数引用（无导入时求值 bug）；Pydantic v2 写法统一正确。
- **向量检索**：排序方向（降序）、余弦归一化除零保护、维度对齐（hash-384 = MiniLM-384）均正确。
- **前端**：`'use client'` 边界、App Router `params: Promise` + `await`、`router.refresh()` 刷新链路、空数据判空均正确。
- **测试**：112 个 pytest 全部通过（主链路可用性背书）。

---

## 建议修复顺序（按性价比）

1. **compose 两处**：移除明文 key + 补 `BACKEND_URL=http://backend:8000`（解锁 Docker 部署，一行改动）；
2. **Reviewer 评估查询**：按 `task_id` 过滤 + `assessment is None` 兜底（学习闭环主流程）；
3. **GitHub 链路四项**：owner 配置化、失败不推进水位、`commit_sha` 去重、错误日志；
4. **State schema 契约**（S1/M1/L1）：`KnowledgeState` 补 `db`、career/reviewer State 补声明的输出字段——把"静默丢失"变为"可预期"；
5. **LLM 路径健壮性**：M2（`target_level`→`target`）、M4（`json.dumps` 生成合法 few-shot）、M3（Mock 不入缓存）、S2（set 合并保护）；
6. **scheduler**：补 `stop_scheduler()` + 幂等保护 + lifespan finally；
7. **前端**：`/api/projects` 列表补里程碑统计（或前端空值处理）+ 错误边界文件 + TaskCard 状态兜底；
8. **RAG**：chunker 三项（段落不丢弃、对齐 256 token、真实 char_offset）+ `file_path` 限制为受控上传目录。

---

*本报告由静态审查 + 测试实测生成，仅供修复参考；如需按上述顺序逐项修复，可另行安排。*
