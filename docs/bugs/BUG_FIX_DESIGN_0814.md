# Bug 修复设计方案（按报告 8 步顺序）

> **日期**：2026-08-14
> **来源**：[BUG_REPORT_0814_deepseek.md](file:///workspace/embodied-ai-career-os/docs/bugs/BUG_REPORT_0814_deepseek.md)
> **范围**：6 项严重 + ~28 项中等 + 25 项轻微中与 8 步建议相关的部分
> **策略**：单一 spec，8 步顺序实现，每步独立 commit

---

## 总体原则

1. **每步独立 commit**，message 前缀 `fix(<scope>): <description>`
2. **每步完成后跑回归测试**，确保既有 112 个测试不退化（允许 1 个已知环境敏感的 `test_vector_store` 波动）
3. **向后兼容**：不改变 API 公开契约（路径/方法/响应结构），仅修内部实现
4. **不引入新依赖**：用标准库或已声明依赖解决

---

## Step 1：Docker 部署 + 凭据安全

### 1.1 凭据泄露（严重 #1）

**位置**：`docker-compose.yml:37`

**修复**：
- `REMINDER_CHANNEL_KEY=SCT394127...` → `REMINDER_CHANNEL_KEY=${REMINDER_CHANNEL_KEY:-}`
- 新增 `.env.example` 模板（不含真实 key），`.env` 已在 `.gitignore`
- 附加：`POSTGRES_PASSWORD` 同理改 `${POSTGRES_PASSWORD:-career}`（弱口令至少不随仓库泄露）

**注意**：报告要求"立即在 Server酱后台重置该 key"——这是**用户侧操作**，代码层只能移除明文，无法替用户重置。spec 中标注为用户后续动作。

### 1.2 Docker 前端连不上后端（严重 #2）

**位置**：`docker-compose.yml:51-52`（frontend environment 缺 `BACKEND_URL`）

**修复**：
- frontend environment 增加 `BACKEND_URL=http://backend:8000`
- `NEXT_PUBLIC_API_URL` 保留（虽然当前无代码消费，但不破坏现有配置语义）

### 1.3 文件变化

```
docker-compose.yml          # 修改：凭据走环境变量 + 补 BACKEND_URL
.env.example                # 新增：配置模板（不含真实 key）
```

### 1.4 验收

```bash
# 确认无明文 key
git grep "SCT394127" -- docker-compose.yml  # 应无输出
# 确认 BACKEND_URL 已设
grep "BACKEND_URL" docker-compose.yml       # 应输出 http://backend:8000
```

---

## Step 2：Reviewer 评估查询修复（严重 #5）

### 2.1 问题

`api/reviewer.py:105-108` 全局查询 `SkillAssessment`（无 `task_id` 过滤）→ 返回别的任务的评估；`assessment is None` 时 `model_validate(None)` → Pydantic ValidationError → 500。

### 2.2 修复方案

**api/reviewer.py**：
1. 查询加 `.filter(SkillAssessment.task_id == task.id)` 过滤
2. `assessment is None` 时构造兜底响应（不抛 500），返回明确的"无评估记录"结构

**reviewer/nodes.py:168**：
3. `apply_skill_update` 节点在 `skill_id is None`（技能未注册）时，不再静默跳过，而是把"未注册技能"信息写入 state，让 API 层能区分"评估了但无技能"vs"完全没评估"

### 2.3 具体改动

```python
# api/reviewer.py:102-116 修改
assessment = (
    db.query(SkillAssessment)
    .filter(SkillAssessment.task_id == task.id)      # ← 加 task_id 过滤
    .order_by(SkillAssessment.created_at.desc())
    .first()
)
# assessment 为 None 时兜底
assessment_out = (
    SkillAssessmentOut.model_validate(assessment)
    if assessment is not None
    else SkillAssessmentOut(
        skill_id=None, task_id=task.id,
        old_level=None, new_level=None, reason="无匹配技能或未生成评估",
    )
)
```

### 2.4 文件变化

```
backend/app/api/reviewer.py              # 修改：查询加 task_id 过滤 + None 兜底
backend/app/agents/reviewer/nodes.py     # 修改：skill_id 为 None 时写入状态信息
```

### 2.5 验收

```bash
.venv/bin/python -m pytest backend/tests/ -k "reviewer" -v
# 多次复盘同一 task，确认返回的是本任务的评估而非全局最新
```

---

## Step 3：GitHub 同步链路修复（严重 #3 + #4）

### 3.1 owner 硬编码（严重 #3）

**位置**：`services/github/client.py:37,69`

**修复**：
- `config.py` 新增 `github_owner: str = "prideandprejudice"`（保持当前默认，但可配置）
- `from_env` 读取 `GITHUB_OWNER` 环境变量
- `client.py` 构造时 `self._owner = settings.github_owner`，URL 用 `f"{self.BASE}/repos/{self._owner}/{repo}/commits"`

### 3.2 异常静默吞掉（严重 #3）

**位置**：`client.py:62-63`（`except Exception: pass`）

**修复**：
- 移除 `except Exception: pass`，改为 `except Exception as e: logger.warning(...)` 并 `raise`（让调用方感知失败）
- `_fetch_commit_files` 同理：失败时记录日志并返回 `[]`（单 commit 文件拉取失败不应中断整批，但要有日志）

### 3.3 水位无条件推进（严重 #3）

**位置**：`sync.py:60`（`_save_last_sync(datetime.utcnow())` 在循环外无条件执行）

**修复**：
- 用 try/except 包裹同步循环
- **仅在实际成功处理（无异常）时才推进水位**
- 异常时记录日志、保留旧水位，下次 sync 重试

```python
# sync.py 修改
def sync_new_commits() -> int:
    ...
    try:
        for repo in settings.github_repos:
            commits = client.fetch_commits(repo.strip(), since=last_sync)
            for commit in commits:
                ...
                total_new += 1
        # 仅成功时推进水位
        _save_last_sync(datetime.utcnow())
    except Exception as e:
        logger.error(f"GitHub sync 失败，水位未推进: {e}")
        # 不推进水位，下次重试
    return total_new
```

### 3.4 commit_sha 去重（严重 #4）

**位置**：`store.py:12-33`（`save_suggestion` 无查重）

**修复**：
- 插入前按 `commit_sha` 查重，已存在则跳过（返回已有 id）
- 新增迁移 `0006_commit_suggestion_unique.sql`：`CREATE UNIQUE INDEX idx_commit_suggestion_sha ON commit_suggestions(commit_sha)`

### 3.5 水位文件相对路径（RAG #10）

**位置**：`sync.py:34` + `config.py:59`

**修复**：
- `config.py`：`github_last_sync_file` 默认改为绝对路径（基于 `os.path.dirname(os.path.abspath(__file__))` 或项目根）
- `from_env` 读取 `GITHUB_LAST_SYNC_FILE` 环境变量

### 3.6 文件变化

```
backend/app/core/config.py                              # 修改：新增 github_owner + 水位绝对路径
backend/app/services/github/client.py                   # 修改：owner 配置化 + 异常不吞
backend/app/services/github/sync.py                     # 修改：条件推进水位 + try/except
backend/app/services/github/store.py                    # 修改：commit_sha 去重
backend/migrations/0006_commit_suggestion_unique.sql    # 新增：唯一索引
```

### 3.7 验收

```bash
# owner 可配置
GITHUB_OWNER=myorg python -c "from app.core.config import settings; print(settings.github_owner)"
# 去重：重复 save_suggestion 同一 sha 不重复插入
# 水位：模拟 client 异常，确认水位不推进
```

---

## Step 4：State Schema 契约修复（S1 / M1 / L1 / L2 / S3）

### 4.1 KnowledgeState 缺 db 字段（S1）

**位置**：`agents/knowledge/state.py` + `graph.py:24`

**修复**：
- `KnowledgeState` 补充 `db: Any` 字段
- `graph.py` 第 24 行 `StateGraph(KnowledgeState)` → `StateGraph(_KnowledgeAgentState)`（用含 db 的完整 state）
- 确保 `retrieve_node` 的 `state.get("db")` 能拿到 API 注入的 db

### 4.2 CareerState 缺 LLM 输出字段（M1）

**位置**：`agents/career/state.py` + `nodes.py:77-78`

**修复**：
- `CareerState` 补充 `llm_market_insights: str` + `llm_priority: list[str]` 字段
- 这样 `analyze_target` 返回的这两个字段不会被 LangGraph 静默丢弃

### 4.3 CareerState 字段名不匹配（M2）

**位置**：`career/nodes.py:30`（`s.get('target_level', 5)` vs `SkillStatus.target`）

**修复**：
- `nodes.py:30` 改 `s.get('target', 5)`（对齐 `SkillStatus.target` 字段名）
- `s.get('evidence', [])` 同理：`SkillStatus` 无 evidence 字段，改为 `s.get('evidence', [])` 保留（容错，因上层可能传含 evidence 的 dict）——但需确认 `SkillStatus` 是否应补 evidence 字段。研读发现 `SkillStatus` 只有 name/level/target，**补 evidence 字段**更合理（与 `Skill` ORM 的 evidence 对齐）

### 4.4 Planner persist 被丢弃（L2）

**位置**：`orchestrator/workflow.py:183`（`"persist": False`）

**修复**：
- planner 默认输入 `"persist": True`（planner 生成任务应落库，否则前端看不到）
- 注意：这是 state key 而非 executor 参数，需确认 `PlannerState` 是否声明了 `persist` 字段——若未声明需补充

### 4.5 Orchestrator db 未透传（S3）

**位置**：`orchestrator/workflow.py:55-104,201`

**修复**：
- `AgentWorkflow.run()` 增加 `db: Session` 参数
- 默认输入 reviewer 的 `"db": db`（从参数注入，而非硬编码 None）
- `api/agent.py:90-103` 调用 `run_workflow` 时传入 `Depends(get_db)` 拿到的 db

### 4.6 文件变化

```
backend/app/agents/knowledge/state.py          # 修改：补 db 字段
backend/app/agents/knowledge/graph.py          # 修改：用 _KnowledgeAgentState
backend/app/agents/career/state.py             # 修改：补 llm_market_insights/llm_priority + SkillStatus.evidence
backend/app/agents/career/nodes.py             # 修改：target_level→target
backend/app/agents/orchestrator/workflow.py    # 修改：run() 加 db 参数 + persist=True + reviewer db 注入
backend/app/api/agent.py                       # 修改：run_workflow 传 db
```

### 4.7 验收

```bash
# Knowledge Agent retrieve_node 不再自建 session
.venv/bin/python -m pytest backend/tests/test_paper_knowledge_e2e.py -v
# Career LLM 字段不丢失（需 mock LLM 验证）
# Orchestrator reviewer 落库
.venv/bin/python -m pytest backend/tests/ -k "orchestrator or agent_run" -v
```

---

## Step 5：LLM 路径健壮性（M2/M3/M4/M6/S2）

### 5.1 Mock 被缓存固化（M3）

**位置**：`llm/factory.py:34-42,54-65`

**修复**：
- fallback 出的 MockClient **不缓存**（cache_key 仍记，但只缓存成功构建的真实 client）
- 新增 `reset_llm_cache()` 函数，供配置变更/测试时调用

```python
# factory.py 修改
def get_llm() -> LLMClient:
    provider = settings.llm_provider
    cache_key = _cache_key(provider)
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]
    try:
        client = _try_build(provider)    # 不再吞异常 fallback
        _llm_cache[cache_key] = client   # 仅成功才缓存
        return client
    except Exception as e:
        warnings.warn(f"LLM provider {provider} 构建失败，fallback Mock: {e}")
        return MockClient()              # Mock 不缓存，下次重试真实 provider
```

### 5.2 Ollama 错误提示 f-string 缺失（M6）

**位置**：`llm/providers.py:160`

**修复**：第 160 行字符串补 `f` 前缀；`OpenAICompatibleClient.chat` 加 try/except 包装为 `ConnectionError`（保留 `from e`）

### 5.3 few-shot JSON 格式错误（M4-1）

**位置**：`planner/generators/llm_generator.py:103-104`

**修复**：`{t["acceptance"]}` → `{json.dumps(t["acceptance"], ensure_ascii=False)}`，resources 同理

### 5.4 _validate_and_fill 不检查 _parse_error（M4-2）

**位置**：`llm_generator.py:113-133,162-165`

**修复**：
- `_validate_and_fill` 开头检查 `task_dict.get("_parse_error")`，命中则抛 `ValueError("LLM JSON 解析失败")`
- `generate()` 的 `except` 捕获后降级到 `RuleGenerator`

### 5.5 Career set 合并 TypeError（S2）

**位置**：`career/nodes.py:72-74`

**修复**：
- `set(llm_result["required_skills"])` → 过滤 str 元素：`{s for s in llm_result["required_skills"] if isinstance(s, str)}`
- `set` 并集打乱顺序 → 改用 `dict.fromkeys` 保序去重

### 5.6 文件变化

```
backend/app/llm/factory.py                              # 修改：Mock 不缓存 + reset_llm_cache
backend/app/llm/providers.py                            # 修改：f-string + try/except
backend/app/agents/planner/generators/llm_generator.py  # 修改：json.dumps + _parse_error 检查
backend/app/agents/career/nodes.py                      # 修改：set 合并保护 + 保序去重
```

### 5.7 验收

```bash
# M3: Mock 不缓存，补设 key 后同进程可切换
# M4: LLM 返回非法 JSON 时降级到 RuleGenerator
# S2: LLM 返回含嵌套 list 时不崩溃
.venv/bin/python -m pytest backend/tests/ -k "llm or planner or career" -v
```

---

## Step 6：调度器生命周期（严重 #6）

### 6.1 无 stop_scheduler + 重复启动

**位置**：`services/reminder/scheduler.py` + `main.py:48-50`

**修复**：
- 新增 `stop_scheduler()` 函数：`if _scheduler: _scheduler.shutdown(wait=False); _scheduler = None`
- `start_scheduler()` 幂等：开头 `if _scheduler is not None: return`（已启动则跳过）
- `main.py` lifespan `yield` 后加 `finally: stop_scheduler()`

### 6.2 提醒数据不准（RAG #7/#8）

**位置**：`reminder/engine.py:49-50,35-37,63-65,111`

**修复**：
- `send_morning`/`send_evening`：查 Skill 表取真实 level/target（替换硬编码 1/4）
- 加日期过滤：`func.date(Task.created_at) == func.date(datetime.utcnow())`（早间推送今日任务）
- `send_comeback`：加"已提醒"状态（用内存标记或文件标记，避免每天重复推）——简化方案：查最近一条 LearningLog 的 `created_at` 是否在 comeback 推送后

### 6.3 ServerChan 不校验 errno（RAG #6）

**位置**：`reminder/channels.py:54-55`

**修复**：
- `with urlopen(...) as resp:` 确保关闭
- 读 body，解析 JSON，校验 `errno == 0`

### 6.4 文件变化

```
backend/app/services/reminder/scheduler.py    # 修改：stop_scheduler + 幂等
backend/app/services/reminder/engine.py       # 修改：真实 level + 日期过滤 + comeback 防重复
backend/app/services/reminder/channels.py     # 修改：resp close + errno 校验
backend/app/main.py                           # 修改：lifespan finally stop
```

### 6.5 验收

```bash
# 调度器幂等
python -c "from app.services.reminder.scheduler import start_scheduler; start_scheduler(); start_scheduler(); print('ok')"
# lifespan 退出时调度器停止
```

---

## Step 7：前端修复（前端 #1/#3/#4）

### 7.1 GET /api/projects 不含 milestones（前端 #1）

**位置**：`api/projects.py:22-26` + `projectService.ts:58-80`

**修复**（后端侧）：`list_projects` 返回时附加 milestones 统计（一次 join 查询，顺带修 API #9 N+1）

```python
# projects.py 修改：list 附 milestones 统计
from sqlalchemy import func
# 一次查询获取所有项目的里程碑统计
milestone_stats = dict(
    db.query(Milestone.project_id, func.count(Milestone.id), 
             func.sum(Milestone.status == "completed"))
    .group_by(Milestone.project_id).all()
)
# 构造响应时附加统计
```

### 7.2 TaskCard STATUS_CONFIG 无兜底（前端 #3）

**位置**：`TaskCard.tsx:60,75-77`

**修复**：
- `STATUS_CONFIG[task.status]` → `STATUS_CONFIG[task.status] || STATUS_CONFIG.todo`（兜底到 todo 样式）
- 或更明确：兜底到 `{ label: task.status, className: "bg-zinc-100 ..." }`（显示原始状态值）

### 7.3 Career 未配置误报后端失败（前端 #4）

**位置**：`dashboard/page.tsx:37-54`

**修复**：
- `getDashboardData` 内部对 `getCareer()` 单独 try/catch，失败时返回 `null` 而非抛出
- Dashboard 渲染时 `career` 为 null 显示"未配置职业目标"而非"后端连接失败"

### 7.4 文件变化

```
backend/app/api/projects.py                    # 修改：list 附 milestones 统计（修前端#1 + API#9）
frontend/src/components/TaskCard.tsx           # 修改：STATUS_CONFIG 兜底
frontend/src/services/dashboardService.ts      # 修改：getCareer 单独 try/catch
frontend/src/app/dashboard/page.tsx            # 修改：career null 时显示"未配置"
```

### 7.5 验收

```bash
# 后端 list_projects 含进度
curl localhost:8000/api/projects | python -m json.tool | grep progress_pct
# 前端 TaskCard 不崩
# Career 未配置时不显示"后端连接失败"
```

---

## Step 8：RAG 质量修复（RAG #1/#2/#3/#4/#5/#12/#13/#14 + API #2/#3/#4）

### 8.1 chunker 段落丢弃（RAG #1）

**位置**：`chunker.py:88-99`

**修复**：`para_tokens < MIN_CHUNK_TOKENS` 且 `chunks` 非空时，合并到上一 chunk（追加文本 + 更新 token 计数），而非跳过

### 8.2 MAX_TOKENS 超限（RAG #2）

**位置**：`chunker.py:21`

**修复**：`MAX_TOKENS = 800` → `MAX_TOKENS = 256`（对齐 MiniLM 截断上限）

### 8.3 char_offset 失真（RAG #3）

**位置**：`chunker.py:81,84-108`

**修复**：`char_cursor` 在每个段落处理后递增 `len(para)`，`char_offset` 传 `char_cursor` 而非 `section_offset`

### 8.4 search_by_paper 召回缺失（RAG #4）

**位置**：`rag/retriever.py:85-102`

**修复**：`paper_id` 下推到 `store.search`（向量库层过滤），而非全局取再过滤

### 8.5 build_index 无异常处理（RAG #5）

**位置**：`rag/indexer.py:83-95`

**修复**：`embed_batch` + `upsert` 包裹 try/except，异常时 rollback + 记录已成功计数 + 抛出（让调用方感知部分失败）

### 8.6 comparator title 作 key（RAG #12）

**位置**：`comparator.py:70,150,197`

**修复**：dict key 从 `b.title` → `b.paper_id`，展示时用 title（key 与展示分离）

### 8.7 summarizer 置信度虚高（RAG #13）

**位置**：`summarizer.py:216-217,259`

**修复**：`_extract_project_relation` 无命中时返回空字符串 `""`（而非 17 字默认文案），`_assess_confidence` 的 `if v and len(v) > 5` 自然不计入空字符串

### 8.8 embedder 并发重复加载（RAG #14）

**位置**：`rag/embedder.py:133-143`

**修复**：`_ensure_model` 加 `threading.Lock` 保护

### 8.9 ingest 异常处理 + file_path 校验 + compare ValueError（API #2/#3/#4）

**位置**：`api/paper.py:65-90,326-343` + `agent.py:144-179`

**修复**：
- `ingest_paper` 包裹 try/except，区分"文件不存在"(404)、"解析失败"(422)、"内部错误"(500)
- `IngestRequest.file_path` 校验：限制扩展名（pdf/md/txt）+ 路径必须在允许目录内（如 `knowledge/papers/` 或配置的白名单目录）
- `compare_papers_endpoint` 捕获 `ValueError` 返回 400
- `index_node` 加 try/except：index 失败不中断已 persist 的论文（返回 partial success）

### 8.10 文件变化

```
backend/app/research/paper_agent/chunker.py          # 修改：段落合并 + MAX_TOKENS + char_offset
backend/app/research/paper_agent/rag/retriever.py    # 修改：paper_id 下推
backend/app/research/paper_agent/rag/indexer.py      # 修改：异常处理
backend/app/research/paper_agent/rag/embedder.py     # 修改：Lock 保护
backend/app/research/paper_agent/comparator.py       # 修改：paper_id 作 key
backend/app/research/paper_agent/summarizer.py       # 修改：relation 无命中返回空
backend/app/research/paper_agent/agent.py            # 修改：index_node 异常隔离
backend/app/api/paper.py                             # 修改：ingest 异常处理 + file_path 校验 + compare 400
```

### 8.11 验收

```bash
.venv/bin/python -m pytest backend/tests/ -k "paper or rag or chunker" -v
# 全量回归
.venv/bin/python -m pytest backend/tests/ -v
```

---

## 不在本次范围内（轻微级，后续处理）

以下属维护性隐患，不影响功能正确性，本次不修（避免 scope 膨胀）：
- `datetime.utcnow()` 弃用（13 个模型 + 4 处服务层）——需统一迁移到 `datetime.now(timezone.utc)`，工作量大且当前功能正常
- 依赖未钉版本（`langgraph>=0.2.0` 等）——需全量测试验证钉版本后的兼容性
- 死配置（`RELOAD=true` 无消费）——无害
- `start.sh` 误杀进程——开发脚本，非生产路径
- Supervisor 单字误匹配（"学"匹配"数学"）——影响路由准确性但不崩溃
- 前端 `lang="en"` → `zh-CN`、子列表 index key、apiClient 无超时——前端代码质量
- 测试脚本硬编码路径——测试基础设施

---

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| State schema 改动可能破坏 LangGraph 行为 | 每步跑回归测试，`total=False` 保证向后兼容 |
| chunker MAX_TOKENS 改 256 影响现有 chunk 分布 | 测试验证 chunk 数量变化在合理范围 |
| GitHub 去重唯一索引在已有重复数据时创建失败 | 迁移前先 `DELETE FROM commit_suggestions WHERE id NOT IN (SELECT MIN(id) FROM commit_suggestions GROUP BY commit_sha)` |
| 前端改动需验证构建 | `cd frontend && npm run build` |

---

## 实施顺序与 commit 规划

| Step | Commit Message | 预估文件数 |
|---|---|---|
| 1 | `fix(deploy): 移除明文凭据 + 补 Docker BACKEND_URL` | 2 |
| 2 | `fix(reviewer): 评估查询按 task_id 过滤 + None 兜底` | 2 |
| 3 | `fix(github): owner 配置化 + 水位条件推进 + commit_sha 去重` | 6 |
| 4 | `fix(state): KnowledgeState 补 db + Career LLM 字段 + Orchestrator db 透传` | 6 |
| 5 | `fix(llm): Mock 不缓存 + few-shot JSON + _parse_error 检查 + set 保护` | 4 |
| 6 | `fix(scheduler): stop_scheduler + 幂等 + 提醒数据准确 + ServerChan 校验` | 4 |
| 7 | `fix(frontend): 项目进度统计 + TaskCard 兜底 + Career 误报` | 4 |
| 8 | `fix(rag): chunker 段落不丢弃 + retriever paper_id 下推 + 异常处理 + 置信度` | 8 |

**总计**：~36 个文件改动，8 个 commit，覆盖 6 项严重 + ~20 项中等 + 8 项 RAG 质量。
