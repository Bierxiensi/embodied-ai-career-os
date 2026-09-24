# 项目长期记忆 · Embodied AI Career OS（第14版，2026-09-23）

## 战略现状
- v3.2（09-21 用户三裁决）：确认留任 → **当前模式 long_term_transition**（active=llm/vlm/phd，frozen=空）。在职转型窗口 2026.09–2027.03；关键节点 2026-12 答辩、PhD 申请季 26秋–27春。
- 赛道：llm 主攻 Post-Training（required_skills 13 项）；vlm 卡位；ai-algo 保底；embodied frozen。**phd 故意不进 TARGET_ROLES**（博士就绪度=六维研究匹配，归博士模块）。🔴 long_term 的 frozen_track_keys 必须为空（`test_only_career_mode_switch_changes_the_range`）。
- 匹配分**双轨**：match_pct=推进度 + strict_pct/qualified_count/required_count=达标率（api/job_hunt.py roles_out；前端 JobsBoard + Dashboard 双显）。实测 llm 67%/23%(3/13)、vlm 54%/14%、ai-algo 75%/20%、embodied 38%/0%。
- 内核突击收口 6 考点：KV Cache/FlashAttention/PagedAttention/FSDP-ZeRO/Quantization/MoE → level 3，绑 Mini Post-Training Lab。
- v2.1 四块：**Phase 1 博士模块已落地**（models/phd.py 三表 + 迁移 0021-0023 + 六维引擎 + /api/phd CRUD+match + /phd 页）；**Phase 2 风险雷达+Career ROI 已落地**（core/risk.py 七维 + career_roi.py + api/risk.py + RiskRadar/RoiTaskList；迁移 0024/0025=advisor contacted 两列）；**Phase 3 技能依赖图+统一落地页已落地（09-22）**——迁移 0027 `skill_dependency`（52 边）+ skill_profile 六域 + `services/readiness`（就绪度唯一实现，job_hunt/plan/risk/dashboard 共用）+ `/api/transition/dashboard` + /today 收口五区（①职业进度+雷达 ②当前工作 ③学术与博士 ④ROI ⑤Risk）。**Phase 3 收口后 v2.1 四块全齐**。
- **博士录入界面已建好（09-22 用户四裁决①）**：PhDEntryPanel（院校+导师双表单，router.refresh 联动）+ PhDAdvisorBoard 联系标记/删除按钮 + phdService CRUD。**用户自己录真实数据**：北航无联系人、北大过高、倾向北科大等 211；13 所 deadline 待补录。
- **hy3 协作协议**：授权 T0-T3 + T4 前端组件(<200行)；T5 留高端。任务包必附「完成后必做」：重启+curl、全量 pytest、tsc/eslint RC、日志写当天、git diff --stat。详见 docs/hy3质量审计与后续规划-2026-09-21.md。

## 硬规则
- 口径同源：services/action_planning/task_scope.py 唯一权威（排除制，禁白名单/禁路由再拼 track_key）。
- 🔴 **数字口径单一真源**：题库目标只手改 `agents/interview/engine.QUESTION_CATEGORY_TARGETS`（现 {LLM:61, MM:30, Project:26, Coding:30}，**描述性分布，非 KPI**）；CORE_TARGET/TARGET_TOTAL/plan.py 的 TARGET_QUESTIONS 全派生。护栏 `test_targets_are_single_sourced_and_derived`。
- 🔴 **接口"早就存在"≠接口正确**：所有 JSON 端点必须走 `ok(...)` 包装**包括空数据分支**（apiClient.ts:67 无 success 即抛错）。**接死代码前必须实测真实响应形状**——前端 getQuestionSources 指向的后端端点曾经从未存在（09-22 已连前端带后端一起删）。
- 🔴 测试隔离：`/api/plan/today` 只返回当天 artifacts；清空 helper 必须显式传 seq，不带参数的 `_today()` 清别的 day 会静默空操作。用例**不得依赖墙钟**（fixture 动态补种日历推导当天）。
- 🔴 **测试的输入必须由测试自己决定，禁依赖 `.env`（09-23 事故）**：`conftest.py` 模块级已同时钉死 `os.environ["DATABASE_URL"]=<临时库>` 与 **`os.environ["LLM_PROVIDER"]="mock"`**。事故经过：`.env` 把 provider 改 xiaomi 后全量 **5 failed**（`test_github_service` 2 例名即 `_mock`；`test_quiz_api::test_start_degrades_to_open_when_llm_unavailable` 前提被打破等）。**验证真实 provider 装配请用 `monkeypatch` 改 `settings`（见 `tests/test_llm_factory_providers.py`）。** 泛化教训：**任何"把外部依赖从 A 换成 B"的环境改动，都要先查测试是否隐式依赖旧值。**
- 🔴 测试不得写开发库；pytest 后核对开发库指纹 md5。**指纹不要与文档里的历史值比**（并发会话/种子/用户录数据都会改它）：正确姿势是**本次改动前后各取一次自比**。参考值（2026-09-23 实测）`533aa07435fdf724a59af0a564f2a608`（09-22 晚记录的是 `fb970ef3…`，期间变动来自并发会话/常驻后端，非本项目改动）。
- 🔴 **"看起来有规模"的数字先 GROUP BY 去重**：实测 `/api/paper/stats` 报 `paper_count=98`，`GROUP BY title` 实为 **3 个标题**（90×ACT + 7×Diffusion Policy + 1×Test Paper）→ 开发期反复 ingest 同一篇 inflate 98 倍。模板 `SELECT <name>,COUNT(*) c FROM <t> GROUP BY 1 ORDER BY c DESC LIMIT 20;`
- 🔴 **接现成接口时参数名/路径以源码为准**：`GET /api/paper/search` 的参数名是 **`query`**（不是 `q`）；学习日志路由是 **`/api/learning-logs`**（连字符，不是下划线）。抄错即 404/422，易误判成"接口没实现"。
- 🔴 **写死在前端文案里的数字是负债**：`TodayBoard.tsx` 的 `hint="只允许这 5 类来源"` 在 `RESOURCE_LOCK` 已扩到 **8 类**后仍写 5。正确姿势是**去掉数字**（"资源均来自资源锁"），不是把 5 改成 8。
- 🔴 **共享测试库会被同会话其他用例改**：依赖"库即种子态"的绝对锚点（如 llm 67%/23%）必须自己防污染，或让改库的用例自清理。实证：`test_e2e_v2_learning_loop` 的 reviewer 晋级把 DPO 1→2 不还原 → 锚点假失败 69!=67。定位手法：临时 pytest 插件在 `pytest_runtest_teardown` 逐用例比对表快照并打印 diff（`.workbuddy/tmp/detect_leak.py`）。
- 迁移：下一条 **0028**；单语句 SQLite 写法；必跑 test_migration_dialect_compat.py（按迁移文件参数化，新增迁移+1 用例属正常）。
- SKILL_PROFILE 是 **SkillProfile 对象列表**——匹配 `.name`，勿当字符串遍历。
- Pydantic v2 from_attributes + 未 flush ORM → `@field_validator(mode="before")` 回落 NULL。
- service 层不透传 payload；apiClient 不做 key 转换，create/patch 显式列 snake_case。
- 🔴 **回查原则**：题目发给用户前被改写/生成的流程，判分必须用**发出去的那一份**（quiz_session_questions 表，迁移 0026）；对外声明的题型必须与实际渲染一致，做不到就降级 open。
- 护栏测试先剥注释+命中哨兵断言；**重构改名后护栏断言要同步**。
- 同一文件禁止并行 Edit；改后 Grep 复读落盘。**多会话并行开发常发生，动手前必复读目标文件**。
- 联调一律 127.0.0.1；杀进程 `MSYS_NO_PATHCONV=1 taskkill /F /T /PID`；改 ORM/配置后重启后端（无 --reload）。
- .workbuddy/tmp/ 已在 .gitignore。岗位 tier 跟赛道；JobPostingPatch 无 PATCH 路由（改 tier 只能删了重录）。
- 🔴 **提交纪律（09-22 血泪）**：提交前必 `git status --short` 核对；**只 `git add <显式文件路径>`，禁 `git add -A` / `git add .`**。并发会话常同时改同一仓库，全量 add 会把别人未完成的工作捎带进自己的提交（今日 `2c7b01d`：57 文件混合提交，message 只写了 Phase 3）。若工作区有他人改动，只提交自己的并在 message 注明。

## 环境 / 门禁
- 后端启动（后台）：`backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000`；SQLite backend/data/app.db。
- pytest：chdir backend + venv python；**基线（09-24）= 437 passed / 0 failed / 2 skipped**（374 → 377 → 384 → 396 → 411 → 437〔+`test_chunker_sections.py` 12→26 例、+`test_summarizer_method.py` 12 例〕）。最稳姿势 `.workbuddy/tmp/run_pytest.py [目标...]`（顺带核对开发库指纹）。
  - ⚠️ **直接调 ORM/图脚本必须 cwd=backend**：`database_url` 是**相对路径** `sqlite:///./data/app.db`，在仓库根跑会 `unable to open database file`。
  - ⚠️ 全量跑会把 `%TEMP%\pytest-of-*` 的 garbage 累积到 >50 项，触发 safe-delete 护栏使 **pytest exit=1（进度全是点、无 F，纯误报）**；加 `--basetemp=../.workbuddy/tmp/pytest-base` 把临时根挪进工作区即恢复 exit=0。
- 写后端测试两手法：①干净库用 contextmanager 覆盖 get_db 指**临时文件库**（**别用内存库**，TestClient 线程池连接不共享）；②共享隔离库只做增量断言+自清理。
- 前端门禁 node 直调：`node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json` + `node node_modules/eslint/bin/eslint.js <files>`（cwd=frontend，managed node 绝对路径）。**next build/dev 本机都跑不了（fonts.googleapis.com 不通）→ 验收 tsc + eslint「除基线外零新增」**。
  - 基线噪音实测（**09-23 重测更正**）：`src/app` 整目录 **65 个 error，全部是 `react-hooks/error-boundaries`，分布在 15 个文件**（旧记录写"16 个 page 全命中"不准确）。🔴 **该规则可完全避开**：只在 **JSX 写在 `try/catch` 内部**时才报；把 JSX 放到 try 外面（try 里只赋值 + 拿 errorMessage）→ **零报错**（见 `phd/page.tsx`、`knowledge/page.tsx`，两页 eslint 全绿）。**正确姿势是"避开"而非"自证"。**
  - components 侧既有噪音：`ResumeBoard.tsx:175` 的 **`react-hooks/set-state-in-effect`（error 级）** + 6 个 `no-unused-vars` 警告（ApplicationsBoard/JobsBoard/MilestoneTimeline×2/ReportsBoard×2/TaskList）。
  - 类型检查兜不住运行时行为时（如"六域雷达真的出 6 根轴"）：单独 `tsc src/services/xxx.ts --outDir` 编译成 JS，再让 node 直吃真实 HTTP 响应跑断言（见 `.workbuddy/tmp/radar_smoke.js`）。
- Git Bash 残缺（ls/head/cd/dirname/mkdir/tail/**sleep** 缺失）→ 文件操作走 Read/Write/Edit/Glob/Grep，命令用 managed python 绝对路径。
- ⚠️ 本机走系统代理 → 打 127.0.0.1:8000 须 `build_opener(ProxyHandler({}))` 直连；后端常驻必须 `run_in_background=true` + `Popen(...).wait()` 包装（单跑 os.execv 约 8s 被回收）。

## 学习闭环 / 知识库现状（09-23 v4 实测，决定下一阶段方向）

用户 09-23 两条产品判断："可以输入的地方很少、像记录系统不像成长系统" + "内容建设不足、不知道去哪搜集学习资料、是不是做个知识库+agent 接进来"。实测结论（v4 文档详述）：

- **写端点 64 个 / 读 51 个**（21 模块）→ "输入少"**不成立**；真问题是唯一的每日入口（今日施工单）**只收布尔值**：`createArtifact` 只写 `title="Day N · 代码"` 这类自动标题，无处写内容。实证 `day_artifacts=0`、`day_progress=0` → **四件套从未被使用过一次**。
- **知识库后端已存在且能跑**：`/api/paper/{ingest,index,search,ask,compare}` 5 端点（main.py:100 挂载）+ `agents/knowledge`（retrieve→answer 两节点 LangGraph）+ 向量库 + 索引。**但前端 0 消费**（无页面无 service，无 /knowledge 路由）。
- ✅ **语料已于 09-23 换成真料**：10 篇 Post-Training 论文（Attention/InstructGPT-RLHF/PPO/LoRA/QLoRA/DPO/DeepSeekMath-GRPO/Qwen2/Qwen2.5-VL/Llama2，与 `RESOURCE_LOCK` 对齐）→ `backend/data/corpus/`（27.8MB，`data/` 已 gitignore）。结果 **10 篇 / 10 distinct title / 1607 chunks / coverage 100%**（原 98 行=3 标题/583 块）。备份 `app.db.bak-20260923-corpus`。命名规则 **`<arxivID> <标题>.pdf`** —— `_parse_pdf` 用文件名作标题线索且剥掉 arxiv id，故这样能同时得到可追溯 id 与干净标题。灌料脚本 `.workbuddy/tmp/ingest_corpus.py`（**必须 cwd=backend**，因 `database_url` 是相对路径 `sqlite:///./data/app.db`）。
- ✅ **真语义嵌入已于 09-23 换好**（原 hash-384 伪嵌入）。**关键根因**：`huggingface.co` 本机走代理 **502**（`Tunnel connection failed`），模型根本拉不下来，而**没人试过镜像** —— 所以不是"没装包"，是**少一个 `HF_ENDPOINT`**。实测四源：PyPI ✅ / PyTorch CPU 源 ✅ / **huggingface.co ❌502** / **hf-mirror.com ✅**。
  - 配方（三步缺一不可）：①`pip install torch --index-url https://download.pytorch.org/whl/cpu`（**不能直接 `pip install torch`** —— PyPI 默认是 2.5GB CUDA 构建）+ `pip install sentence-transformers`（本机 `torch 2.14.0+cpu` / `sentence-transformers 6.1.0`）②`.env` 设 `HF_ENDPOINT=https://hf-mirror.com` ③**重建索引** `POST /api/paper/index {"force_rebuild": true}`（旧向量按 `model_name` 隔离，不会自动失效）。
  - **判据**：`GET /api/paper/stats` 的 `model_name` 必须是 `sentence-transformers/all-MiniLM-L6-v2`；若是 `hash-384` 说明又静默退化了（不报错，只是检索变差）。
  - 收益（同一组问题复测）：**top-1 正确论文 2/4 → 4/4**；DPO 问题从"4/5 命中 DeepSeekMath"变为"4/5 命中 DPO 论文"；GRPO 从"5/5 命中 PPO"变为"4/5 命中 DeepSeekMath"；分数从挤成一坨（0.21–0.46）变得有区分度（0.54–0.74）。已清残留 `hash-384` 旧向量。
  - **"换料"只解决"没内容"，"换嵌入"才解决"检索不准" —— 两件事必须都做。**
- ✅ **RAG 双硬伤均已于 09-23 修复**：①`HashEmbedder` 伪嵌入 → 换真语义嵌入（见上）；②`answer_node` 规则拼接 → **LLM 优先、规则兜底**（`_compose_with_llm`，沿用 `research:_match_with_llm` 同款契约"失败返回 None 由调用方降级"）。`KnowledgeAnswer`/`AskResponse` **追加** `answer_mode`（llm/rule）——**MockClient 必须触发回落**（Mock 模板绝不能冒充知识库答案）。
- 🔴 **置信度判据曾有个恒真条件（09-23 修复）**：原为 `if top_score >= 0.35 or len(chunks) >= 3` —— **检索总是返回 top_k 条**（默认 5），故 `len(chunks)>=3` **恒真 → 永远 high**（实测语料外问题"React 内存泄漏"也报 high）。重新标定（`.workbuddy/tmp/calibrate_confidence.py`）：相关 top 0.582–0.745 / 无关 0.215–0.399，间隙 0.183 → **`high≥0.50`、`medium≥0.35`，删掉命中数条件**。⚠️ **阈值与嵌入模型绑定，换嵌入模型必须重标**。
- ⚠️ **知识库问答延迟实测**：单问 9.6s / 12.5s，最长 **57.6s**（答案长时）→ **别放进"点击即需响应"的链路**。
- **另一个已修的真 bug（09-23）**：`chunker.py` 分节器两处正则口径不一致 —— `_SECTION_PATTERNS` 允许**无点编号**但剥编号的 `^[\dIVXLC]+\.\s*` **要求必须有点** → 学术 PDF 常态的 `1 Introduction` 剥不掉编号 → normalize 成 unknown → 被丢弃 → **整篇只剩 `Abstract`，范围延到文末，N 块全标 abstract**（DPO 论文 147 块中 146 块），也解释摘要 `method` 恒空。修复用 `^(?:\d+|[IVXLC]+)\.?\s+`（**`\s+` 兜底是关键**：用 `\.?` 会让 `Introduction` 的 I、`Conclusion` 的 C〔C=罗马 100〕被吃掉）。护栏 `tests/test_chunker_sections.py` 12 例。
- **`pypdf` 曾缺失**：`parser.py` 硬依赖它却不在 `requirements.txt` → PDF 通路一直是坏的（降级返回空文本）。09-23 已装 6.19.0 + 补进 requirements.txt。
- ✅ **PDF 语料质量已于 09-24 修复两项**（原三条限制）：
  - ①章节标签 ✅ **已修**：根因是 **PDF 把 LaTeX 小体大写拆开了** —— `\textsc{}` 标题抽取后首字母与其余字母间多空格（`1 Introduction` → `1 I NTRODUCTION`、`4 Our Method` → `4 O UR METHOD`），导致词面匹配全落空、整篇只剩 `ABSTRACT` 一个 section 吞掉全文（LoRA 的 abstract 段曾占 **28531 字符**）。修法：标题**压平**（去空格标点小写）后与规范名做子串比对（`ourmethod` 含 `method`）。另加"子节继承父标签"与"未识别顶层标 `unknown`（**不沿用上一节**，宁可诚实）"。效果：全库 abstract 196→26、experiment 105→484；`section` 过滤从不可用变可用。
  - ③`summarizer.method` ✅ **已修**：填充率 **2/10 → 10/10**。三级策略：method section 命中 → **全篇回落**（方法章节常以技术命名如 `3 QLoRA Finetuning`，任何词表盖不住）→ 末级兜底；三级**都过 `_is_prose_like` 闸门**（长度/词数/字母占比/非正文标记），挡掉附录模板与公式碎片。剩余小瑕疵：3 篇句子不理想（附录授权句/半句/从句中开始）。
  - ②**双栏抽取噪声仍在**（连字 `eﬃency`、跨行拆字 `harm\nony`）→ 可选绕法：改用 arXiv HTML（parser 支持 `.md/.txt`）。
- ⚠️ **改分节/summarizer 后必须重建语料**（库里存量标签是旧的）：`cd backend && python scripts/rebuild_paper_corpus.py --yes`（自动备份 + 清三表 + 重灌，实测 172s）。
- 🔴 **诊断工具本身会撒谎**（09-24 教训）：第一版诊断正则只捕一个 `\S`，把 `1 Introduction` 显示成 `1 I`，看起来像数据损坏 → 险些按错误结论动手。**诊断输出被截断时，先怀疑诊断本身，打印完整行。**
- **`learning_logs` 就是缺失的"内容位"**：表字段 `content`(Text 必填，含反思)/`duration_minutes`/`artifact_url`（模型注释："Reviewer 据此加分，未来作为 Portfolio 能力证据"）。API 已挂载但**无前端**；库里 14 条全是重复演示数据（"ROS2 publisher 节点" + `commit/test`）。
- **两个孤岛缺一座桥**：今天学什么(plan_days，有 UI) → 今天学到什么(learning_logs，**无 UI**) → 卡住问(paper/ask，**无 UI**；语料已真但检索不够准) → 谁来评(reviewer，有 UI) → 证据(artifact_url→Portfolio)。**下一阶段的活 = 连通这条链，不是再建模块。**
- 今日页**已**渲染 `验收标准`/`学习目标`/`面试题主题`/`指定资源`（数据来自 `PlanDayOut`，30/30 天都有）；但「指定资源」只渲染名字**无 URL**（"不知道去哪搜集"的直接原因）。

## LLM 接入层现状（09-23 实测并**已启用小米 MiMo**，🔴 最高杠杆的一条）

- **`backend/app/llm/` 已完整实现**（client/factory/providers/models，约 430 行）：`get_llm()` 工厂 + 单例缓存 + **失败静默 fallback 到 MockClient**；provider 五选一 `mock`/`ollama`/`deepseek`/**`xiaomi`**/`openai_compatible`；接口 `llm.chat([ChatMessage(...)])` 与 `llm.chat_json(msgs, output_schema)`。`openai>=1.0.0` 已装。
- **✅ 09-23 小米 MiMo 已接入并启用**：`config.py` 新增 `xiaomi_api_key`/`xiaomi_base_url`(默认 `https://token-plan-cn.xiaomimimo.com/v1`)/`xiaomi_model`；`factory.py` 新增 `xiaomi` 分支（含模型名校验、cache key 纳入模型）；`.env` 已设 `LLM_PROVIDER=xiaomi` + 用户填的 key。**小米另有 Anthropic 兼容端点 `.../anthropic`，但本层只实现 openai 协议 → 暂不可用**（要用需另加客户端）。
- **实测可用模型 8 个**：mimo-v2.5 / mimo-v2.5-asr / mimo-v2.5-pro / mimo-v2.5-tts / mimo-v2.5-tts-voiceclone / mimo-v2.5-tts-voicedesign / **mimo-v2.6-flash**（当前选用）/ **mimo-v2.6-pro**（重推理用）。`XIAOMI_MODEL` 可切换（改一行 + 重启）。
- **7 个调用点已接线且都有规则兜底**：career、planner(llm_generator)、research、reviewer、supervisor、practice×2、github analyzer。"LLM 是增强不是依赖"。
- 🔴 **验收必须断言 `llm.model_name == "mimo-v2.6-flash"`**（或对应模型名）：fallback 只 `warnings.warn`，key 错/欠费/网络问题都**静默退回模板**。复核脚本 `.workbuddy/tmp/verify_xiaomi.py`。
- **实测延迟：单次 chat 5-10 秒** → **不要让 LLM 进"点击即需响应"的主链路**（生成任务/仪表盘）。
- 🔴 **"接通"≠"生效"（09-23 调用计数取证）**：`supervisor` ✅ 真调；`research` ⚠️ 编排链路喂硬编码 `topic="ACT"` → 命中预设模板 → 0 次；**`planner` ❌ 不可达**（`generator` 默认 `"rule"`，显式传 `"llm"` 才走）；`career`/`reviewer`/`practice` ✅ LLM 优先。取证脚本 `.workbuddy/tmp/probe_llm_usage.py`。
- **`agents/knowledge/nodes.py` 零 `get_llm` 命中** —— 知识库 `answer_node` 没接 LLM（注释自述"Week 2+ 接 LLM 后替换，签名不变"=Y6 前半段）。
- **多 agent 体系已存在**（`agents/` 12 包）：`AgentRegistry`+`registry_setup.py`、`supervisor`（analyze_intent→select_agents→create_plan）、`orchestrator`（OrchestratorExecutor+AgentWorkflow，`POST /api/agent/run`）——**本身就是个小 harness**。
- 🔴 **不接 DeepSeek Harness（dsh）作为 runtime**：它是 Node 独立应用（`npx @deepseek-ai/dsh web` → Web UI :3080）、"Everything is a Plugin"(Cordis)、developer preview 且警告破坏性变更、无对外集成 API。理由：①形态不匹配 ②收益重复 ③**与"口径同源"纪律冲突**。**分野：招投标要召回率（harness 灵活性=资产）；Career OS 要口径可信（=负债）。**

- **语料管线已脚本化入库（09-24，别再往 `.workbuddy/tmp/` 重写）**：`backend/scripts/fetch_paper_corpus.py`（下载，幂等/`--dry-run`/`--force`）+ `backend/scripts/rebuild_paper_corpus.py`（重建，**破坏性 → 默认只预演、须 `--yes`、自动带时间戳备份**）。两脚本 docstring 写明命名约定 `<arxivID> <论文标题>.pdf` 及其原因。⚠️ 两者都须 **cwd=backend**（`database_url` 是相对路径）。
- **09-24 收尾**：09-23 的 8 个批次积压（17 改+9 新）已按主题拆成 **4 个提交**入库，合计 32 文件/+3780−64（`ff036bc` 后端 llm+知识库修复 / `af86005` 前端三件 / `b8d5fb0` 文档记忆 / `3f26d01` 语料脚本）。纪律：只 add 显式路径 + 逐个核对 `git diff --cached --name-only`；提交信息写文件再 `git commit -F`（避免中文+反引号被 shell 解释）。

## 数据与缺陷
- 单一源：skill_profile.py + target_roles.py + plan_30d.py（seq 不绑日历）；**skill_graph.py 的 SKILL_EDGES（52 边）是依赖图单一真源**（投影进 skill_dependency 表，禁止反向从表推）；**transition_context.py 是答辩日/导师窗口/在职事实单一真源**（core/risk.py 也用它）。
- 开发库基线：skills 50（43 标六域 / 7 未标=冻结具身）/ skill_dependency 52 / plan_days 30 / **interview_questions 147（09-22 D1/D2 手术：删近重复 74/75/76 + 11 道 LLM 内容题 Project→LLM；终态 LLM 61/MM 30/Project 26/Coding 30，gap 全 0；备份 app.db.bak-20260922-d1）** / tasks 23 / **job_applications 3（09-22 晚清理：id 8-11 经用户确认是演示数据已删，余 3 条真实：华夏泰科/电价预测J10856 均 rejected、大禹节水 applied）** / research_directions 6 / **phd_targets 8（09-22 晚瘦身：删 985 五所 北大/清华/人大×2/北理工；余 211×4 北邮/中石大/北科大/北交大 + 市属 北信科 + 中科院 国科大自动化所 + 985 北航本校〔有意保留：本校通道〕。**⚠️ deadline 仍多为 NULL 或已过期，须用户补录 2027 周期**）** / **phd_advisors 5（4 条占位 + 王恒〔北科大真实导师，09-22 录入，match 89 分/A 级〕；contacted 全 0）** / practice_records 7 / quiz_session_questions 表已建（空表）。
- ✅ 09-22 四裁决已落地：①博士录入界面（用户自录数据）；②死接口 getQuestionSources/getRecommendations 前后端全删；③ViewRole 整体删除（lib/viewRole.ts 删、护栏改为"不得复活"断言）；④D1/D2 题库手术一次性完成。
- ✅ 09-22 Phase 3 已落地：技能依赖图（迁移 0027 + 种子脚本 + 18 例护栏）+ 统一落地页五区（today 页四路并行取数；`test_transition_dashboard` 19 例，核心是 `test_readiness_is_identical_to_job_hunt` 断言落地页与求职看板逐字同源）。
- 🔴 **剩余缺陷全清单（v3 实测口径，2026-09-22 傍晚）**——v1 的 D1-D10 中 D1/D2/D3/D4/D9/D10 已全部偿清：
  - **D5** 中科院地理所 2 年 5 个月不在 `resume_facts`（`db/base.py` 种子缺该段）→ 需用户提供事实
  - **D6** ✅ **已封口（09-22 晚实测：缺陷早已不存在**——job_postings 8 条 track 全合法、tasks 零漂移**）**；已补护栏 `tests/test_p3_target_track_integrity.py`（赛道集合哨兵 + 岗位 track + 任务 track_key 三层断言）。**教训：缺陷清单本身也会过时，护栏比清单可靠。**
  - **D7** 巨型组件 **8 个 >400 行**：JobsBoard 708 / QuestionBoard 678 / ResumeBoard 647 / JDBoard 610 / TodayBoard 605 / ApplicationsBoard 452 / PlanBoard 425 / ReportsBoard 424
  - **D8** 硬编码色值：**180 处 / 32 文件**，其中 **95 处已令牌化（09-22 晚，25 文件，同值替换=浅色零变化）**；余 **85 处无令牌**（见 X5）
  - **X1** 博士库时间维度失效（deadline 全过期）→ 用户补数据 + 前端区分"已过期/未录入"两态
  - **X2** ✅ 已修：`career-os-milestone` skill 过时（基线 326→374、旧指纹、node 22.12→22.22.2-3、ViewRole 整节改为"已删除存证"）
  - **X3** 提交卫生：今日 `2c7b01d` 是 **57 文件 / +5078 行**的混合提交（并发会话把另一会话的四裁决工作一并 `git add -A` 捎带，message 只写 Phase 3）→ 纪律：**提交前必 `git status --short` 核对，只 add 显式文件路径，禁 `git add -A` / `git add .`**
  - **X4** 🔴 **六维匹配引擎奖励数据缺失（09-22 晚实测发现，未修，待用户裁决）**：`agents/phd/agent.py:_timeline_score` 对 `deadline is None` 返回 **70**，而"已过期"只给 **20** → **越不录截止日，排名越靠前**。实测对照：北邮（录了、已过期）timeline=20，王恒（未录）timeline=70。建议修法 `None → 50` + 输出 gap"截止日未录入"。**另一发现：六维中 geo/publication/in_service 三维在同池候选里近乎恒定（全北京、全 none），0.40 权重是常量 → 实际只有 direction_fit(0.30)+tier(0.15) 在排序**。
  - **X5** 色值债务的真实结构：180 处里只有 95 处有对应令牌；剩 85 处是项目**从未定义**的 Tailwind 原色（`#3b82f6`/`#ef4444`/`#22c55e`/`#6b7280`/`#e5e7eb` 等）→ 属"设计系统扩容"而非"清偿债务"，**不可派低端模型硬替换**（会诱导自造令牌）
  - **D3** `is_verified` 全库 0（需用户闭卷答题，非代码可修）
- 🔴 **Y 系列（09-23 v4 实测新增，聚焦"学习闭环缺失"；Y2/Y3/Y6 是重点）**：
  - **Y1** ✅ **已于 09-23 完成**：学习日志表单接进今日施工单（`LearningLogCard` 插在四件套之后，`TodayBoard` 加可选 `learningLogs` prop，`today/page.tsx` 第 5 路并行取数 `.catch(()=>[])`）。四件套只记"勾没勾"、日志记"做了什么" —— **记录系统 → 成长系统的分界就是"存状态 vs 存实质"**。
  - **Y2** ✅ **已于 09-23 完成**：建了 `/knowledge` 页（`services/knowledgeService.ts` + `components/KnowledgeBoard.tsx` + `app/knowledge/page.tsx`），并加入 `GlobalNav.LEARN_ROUTES` 与 **`SectionNav` 学习区二级导航**（⚠️ **后者才是真正能点到的入口**，只改前者新页只能靠 URL 访问）。两个「降级可见」设计：嵌入模型含 `hash` 时页面顶部告警；`answerMode=rule` 时标注「片段兜底（LLM 不可用）」。
  - **Y3** ✅ **已于 09-23 完成**（原：语料是假的 98→3）→ 已换 10 篇真 Post-Training 论文（见上）
  - **Y4** ✅ 同批完成：`learningLogService`（list/create/isToday）。🔴 **naive UTC 陷阱**：后端 `created_at` 是 `"2026-09-10T07:07:20.815959"`（**无时区后缀**，因 `datetime.utcnow()`）；JS `new Date()` 会当**本地时间**解析 → 上海**差 8 小时** → **凌晨日志会被算到前一天、在"今日"里消失**。修法：service 层 `normalizeUtc()` 补 `Z`；"今天"用**本地日历日**比（不是 ISO 串前缀比较）。
  - **Y5** ✅ **已于 09-23 完成**：新建 `components/ResourceList.tsx`（映射表 3 条 + **arXiv 编号自动链接**，后者让未来加论文无需改前端），TodayBoard 15 行渲染块 → 1 行；**hint 硬编码"这 5 类"改为"均来自资源锁，不得自选"**（去掉数字，不是改成 8）。⚠️ 实测 `docs.vllm.ai`/`arxiv.org` 可达，但 **huggingface.co 两条 502**（本机代理）→ 保留官方 URL 不找替身（`github.com/huggingface/llm-course` **是空壳仓**，换过去比不可点更差）。
  - **Y6** ✅ **已于 09-23 全部完成**：前半段 HashEmbedder → ST 真语义嵌入（top-1 命中 2/4→4/4）；后半段 `answer_node` 接 LLM（`answer_mode=llm`，成句回答 + 引用，防臆造生效）
  - **Y7** 🟡 `learning_logs` 14 条重复演示数据 → 清理（先备份）
  - **Y8** 🟡 讲义覆盖 3/30（`docs/带你学-00/01/02` 应用内 grep 0 引用）→ 用户的活
  - v4 任务包 A/B/C 已写好可直接下发（A=学习日志表单、B=/knowledge 页、C=资源链接化），D=RAG 升级需先裁决
- 🔴 **Y9/Y10（09-23 接入小米后实测新增，属"接通≠生效"类）**：
  - **Y9** `/api/agent/run` 的 `orchestrator/workflow.py:_resolve_input` 是**硬编码占位输入**（`research.topic="ACT"`、`planner.skills=[{Isaac}]`、`career.target_role="Robot AI Engineer"`、reviewer 固定日志）→ **`user_input` 只影响 supervisor 的意图路由，不传给子 agent**。该端点=冒烟级；Dashboard「Agent Activity」展示的正是这些占位运行（`agent_runs=17`）。原文注释自述"Day 5 默认输入仅保证 Agent 不报错"。
  - **Y10** `LLMGenerator`（planner 的 LLM 生成器）**死代码**：`generator` 三处默认全 `"rule"`（`orchestrator` 不设 / `api/planner.py:76` 默认 / 前端 `plannerService.ts` 从不传 → 全前端 grep generator 零命中）。显式传 `"llm"` 才可达。
- 历史执行记录（E1-E7 口径修复、题库去 KPI 化 `4a3982f`、小测验接通 D4 等）详见 docs/口径与题库问题清单-2026-09-22.md 与 docs/项目梳理与迭代指导-2026-09-22.md §四。

## 文档索引
- 全量梳理+任务包：docs/项目梳理与迭代指导-2026-09-21.md（v1，含 6 个四元组任务包）
- 09-22 梳理 v2 + 四裁决执行结果：docs/项目梳理与迭代指导-2026-09-22.md
- **⭐ 09-23 下一步工作指导（小米接入验证后）**：docs/下一步工作指导-2026-09-23.md —— LLM 已真正接通（8 模型 / chat 10.65s / 384 测试全绿 / 开发库未写）+ "接通≠生效"三处发现（Y9/Y10）+ 测试事故与 conftest 修复 + P0-P2 工作规划 + 三个必须注意（延迟/口径会变/静默降级）
- **⭐ 09-23 深度分析（DeepSeek/Harness/知识库三条路线）**：docs/深度分析-DeepSeek接入与知识库可行性-2026-09-23.md —— 结论：①DeepSeek 当 LLM 已就绪只差 key（2 行 .env，P0 立刻做）②不接 dsh 当 runtime ③知识库先换料再接线
- **⭐⭐ 09-23 梳理 v4（最新，回应"输入少/内容不足"两条产品判断）**：docs/项目梳理与迭代指导-2026-09-23-v4.md —— 定位：**不是缺功能，是缺通路**。含 4 个可测量命题的实测判定（64 写端点 / `day_artifacts=0` / 98→3 语料 / 知识库已存在）、Y1-Y8 缺陷清单、P0-P3 路线、4 个四元组任务包、防坑清单 14-16 条
- **⭐ 09-22 梳理 v3（实测快照 + 剩余工作派发包）**：docs/项目梳理与迭代指导-2026-09-22-v3.md —— 定位：v2.1 四块收口后，边际价值转向「真数据 / 技术债 / 协作卫生」三条腿；含 D5-D8+X1-X5 全清单、P0-P3 路线、3 个可直接下发的四元组任务包、防坑清单 11-13 条
- 背景与能力结构：docs/候选人背景分析-2026-09-17.md；产品诊断：docs/产品设计诊断-2026-09-17.md
- v2.1 四件套：docs/CAREER_OS_V2_{INCREMENTAL_PRD,ARCHITECTURE,AGENT_SPEC,DEVELOPMENT_PLAN}.md
- 模式 PRD：docs/PRD_CAREER_OS_MODES.md；实施约束：docs/CODEBUDDY_IMPLEMENTATION_CONSTRAINTS.md / CODEX_MODULAR_DESIGN_STANDARD.md / CODEX_READABILITY_STANDARD.md
- 口径与题库问题清单（09-22）：docs/口径与题库问题清单-2026-09-22.md（E1-E7/D1-D4 全收口，留档备查）
- Spec 工作流：docs/superpowers/specs/（审 spec 一律先实测代码/DB，别信 spec 自述）
