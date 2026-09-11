# 项目长期记忆 · Embodied AI Career OS

> 第三版（2026-09-10 二次精简）。**本文件只留结论与硬规则**；实施细节见
> `.workbuddy/memory/YYYY-MM-DD.md` 与 `docs/platform-direction-30day.md`。

## 一、战略与定位

- **战略 v2.0**：LLM 主攻 + VLM 卡位 + AI 算法保底；具身/VLA/ROS2/Isaac/SO101 **全 D 级冻结**
  （`target_roles.py` 标 frozen；`skill_profile.py` target=level → gap 恒 0）。
  **不要再推荐具身方向学习任务。** 优先级：求职 > LLM 核心能力 > 项目 > 博士准备 > 具身。
- **平台 = 30 天施工执行台**。唯一判据：顶栏有没有一个入口回答「我今天该干什么」。
  IA = `今日 / 施工 / 项目 / 题库 / 求职▾ / 复盘 / Agent`；`/today` 是默认落地页，
  `/dashboard` 降为二级「概览」（**不删**）。
- **路线图**：P0 ✅ / P1 ✅ / P2 ✅ / P3 ✅ / P4 求职包装 ✅ —— **P0–P4 全部完成**。
  硬约束：**单周平台工时 ≤ 2 个晚上**，超预算先砍 P4 再砍 P3，P0/P1 不可砍。
- **求职 Agent 四条线**：`/jd` `/resume` `/interview` `/reports`。引擎一律是**独立纯规则模块**
  （`agents/*/engine.py`、`services/*/engine.py`），**不套 BaseAgent / LangGraph** ——
  需可单测、可解释、不烧 token。新增业务 Agent 沿用。LLM 只做措辞增量，产出仍过规则校验。
- **P2 证据闭环**（doc §十三）：`experiments` 表 + `core/evidence.py` 四档 gate
  （L1 note/题 → L2 code+commit → L3 实验 → L4 对比实验+报告）写回 `skills.evidence_gate`；
  `TECH_BLACKLIST` 在 Planner 硬拒绝；前端 `/experiments` `/evidence`。
- **P3 题库生长**（doc §十四）：`coverage_matrix()`（目标 150 = LLM50/Multi30/Proj40/Code30，
  核心必达 80）；`GET /api/interview-questions/coverage`，**红格 = (技能,分类) 0 题**；前端 `/questions`。
- **P4 求职包装**（doc §十五）：`services/packaging/engine.py` 纯函数
  `build_readme_skeleton`（13 节论文体骨架：数据能填的自动填、只有人能写的留**带提示占位**）
  + `build_skill_lines`（**只收 `evidence_gate >= 1`**；自评 ≥3 无证据进 `pending` = 虚构风险）；
  接口 `GET/POST /api/projects/{id}/readme`、`GET /api/resume/skill-lines`。
  **`patch_project` 内联 README 拼接已删，统一走该构建器**；前端 `ReadmeDraftCard` / `SkillLinesCard`。
- **文档**：`docs/platform-direction-30day.md`（§十三 P2 / §十四 P3 / §十五 P4）、
  `docs/system-audit-and-role-switch.md`、`docs/app-mode-and-radar-analysis.md`（模式门控：
  **只改展示不改数据**）、`docs/agent-design/JOB_SEARCH_AGENT_DESIGN.md`（§0.1.3 记录有意偏离）。

## 二、技术栈与规范

- Next.js 16 App Router + React 19 + TS + Tailwind v4（CSS-first `@theme`）；FastAPI + SQLAlchemy + SQLite。
  **零第三方 UI 库、零图表库**（纯 SVG 雷达）、Geist 字体。Server Component 拉取 + `router.refresh()`。
- 组件 PascalCase.tsx 一文件一默认导出；`type Props` 内联；常量 UPPER_SNAKE_CASE；
  后端 snake_case → 前端 adapter 转 camelCase。卡片：白底 + hairline + 18px 圆角 + 24px padding，无阴影；
  徽章 pill。颜色：emerald=成功/当前、sky=Planner、violet=Reviewer、amber=待办、rose=失败。
  **一律引 `var(--color-*)` token，不硬编码 hex。**
- **`GlobalNav` 只出现在 `app/layout.tsx`**；子页外层 `flex flex-1 flex-col`，**不要 `min-h-screen`**；
  页头统一 `components/PageHeader.tsx`。
- **雷达图必须岗位对齐**：取主攻赛道 `required_skills` 出 8 轴，**不要回全量技能轴**（46 轴版已删，
  别再造第二套实现）；Dashboard `readiness` = 主攻 `matchPct`，**不是**全技能加权和，须与看板同源。
  `SkillRadarCard` 支持任意 `axes[]`，换赛道无需改它。
- Planner 默认目标岗位来自 `TARGET_ROLES`，**不要硬编码**（曾写死 "Robot AI Engineer" 一直产具身任务）。

## 三、数据模型：三个正交轴

| 字段 | 回答 | 取值 |
|---|---|---|
| `tasks.source`（0007） | 谁写的 | user / seed / planner / test |
| `tasks.track_key`（0008） | 属于哪条赛道 | llm / vlm / ai-algo / embodied / NULL |
| `tasks.plan_day_id`（0011） | 属于课程第几天 | plan_days.id / NULL |

互不替代。`GET /api/tasks?track_key=&plan_day_id=&include_untracked=&include_test=`；
赛道判定口径在 `target_roles.py`，**声明顺序优先**。

**30 天执行台**：`app/core/plan_30d.py` 是课程**唯一事实来源**（`PlanDaySeed` × 30 +
`RESOURCE_LOCK` + `SKILL_TO_DAY_SEQ`）；改计划 = 改该文件 + 重跑 `scripts/seed_plan_30d.py`
（`--dry-run` / `--rebind`），**不做 CRUD 界面**。表 `plan_days` / `day_artifacts` + `/api/plan`。
**`PlanDay.seq` 是不可变课程序号，绝不与日历日期绑定**：`/today` 同返 `day.seq`（课程序号）
与 `day_index`（日历推导）；滑期只提示、不自动顺延。
**每日四件套** `kind ∈ {code, note, questions, commit}`。总账：代码/笔记/commit 各 30、
面试题取真实条数（150）、齐全日 30。

## 四、环境

- **本地 SQLite** `backend/data/app.db`；Docker Compose 内覆盖 DATABASE_URL 用 PG。
  `.env` 由 `config.py` 顶部 `load_dotenv` 加载（根 `.env` 优先，**不覆盖已存在环境变量**）。
- 会话内启动：后台跑 `backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
  与 `cd frontend && npx next dev -p 3000`；`start.sh` 的 Windows detach 会随任务回收退出。
- pytest 用 `backend/.venv/Scripts/python.exe`（managed python 无 pytest）。全量 ≈15s / **198 项**，
  验时优先定点文件；**pytest 后必须核对开发库指纹不变**。
- **Git Bash 残缺**（`cd/ls/wc/tail/dirname` 缺失；PowerShell stdout 抓不到）→ 文件操作走
  Read/Write/Edit/Glob/Grep；需要度量/跑命令时用 managed python 绝对路径。
  **跑 pytest 要 chdir**（cwd 不是 backend 时相对 `sqlite:///./data/app.db` 会打不开）：
  `python -c "import os,sys;os.chdir(r'D:\...\backend');sys.path.insert(0,'.');import pytest;sys.exit(pytest.main(['tests','-q']))"`
  用 `backend/.venv/Scripts/python.exe`。**netstat 输出要 `decode('gbk')`**（中文 Windows 非 UTF-8）。

## 五、避坑清单

**Windows / 进程**
- 联调**一律 `127.0.0.1`，不要 `localhost`**（Node → IPv6 ::1，uvicorn 只绑 IPv4 → ECONNREFUSED）。
- 杀进程用 `MSYS_NO_PATHCONV=1 taskkill /F /T /PID`；Git Bash `kill <winPID>` **静默返回 0 却不生效**，
  `taskkill //F` 斜杠会被改写。
- **改 ORM/schema 后必须重启后端**（无 `--reload`），否则前端字段渲染为 null。
- `next build` 可能被 safe-delete shim 拦（`.next/trace`）；不是代码错误，临时
  `CODEBUDDY_SAFE_DELETE_ENABLED=0`（仅影响 `.next` 缓存）。

**测试**
- 🔴 **测试不得写开发库**：`tests/conftest.py` 模块级把 `DATABASE_URL` 指向临时库，session guard 内
  直接调 `init_db()`（不能依赖 TestClient lifespan）。**新增测试不自建临时库、不在 import 期
  `unlink()`**；依赖实时 :8000 的脚本放 `collect_ignore`。
- 幂等用例用**增量断言**（前后 count 对比），不断言绝对行数（共享临时库会被污染 → 单跑过、全量挂）。

**DB / 迁移 / 契约**
- **迁移 SQL 注释禁止出现分号**（`run_migration.py` 裸切 `;`）；多语句同事务，一句失败整批回滚 →
  **一条迁移只做一件事**。
- `Pydantic v2 from_attributes` + 未 flush 的 ORM 实例：列 `default` 只在 INSERT 生效，内存属性为
  `None` → 校验失败。**修法**：`@field_validator(<f>, mode="before")` 回落默认值。
- **Out 模型的必填字段要覆盖所有构造分支**（`GeneratedTaskOut.duration` 无默认，黑名单拒绝分支不传
  → 真请求 500）；非主路径也要给默认值。前端 DTO 漏字段会被 `tsc` 拦。
  **新端点要么测试覆盖、要么类型覆盖。**
- **service 层不要透传 payload**：`apiClient` 不做 key 转换，camelCase 的 `answerOutline` 直传后端
  （字段 `answer_outline`）会被 Pydantic 当未知字段**静默丢弃**。
  **create / patch 一律显式列 snake_case 字段。**
- **summary 必须与它描述的列表同源生成**：`build_skill_lines` 首版把 `pending` 截断到 12，
  却报 `summary.pending = 16` → 前端"16 项却只有 12 个"。**截断/分页高发此错**；
  加断言 `summary.x == len(list)` 钉死。单测没抓到、**实时冒烟的自洽断言抓到了**。
- 开发库基线（白名单，清理脏数据时**一律不动**）：`projects` 2 / `milestones` 12 /
  `job_applications` 4 / `resume_facts` 9 / `interview_logs` 1 / `skills` 48 / `plan_days` 30。

**数据回填**
- **通用技能不可映射到具体课程日**（首版 `Python→Day2` 等导致「数据库层」挂到「Attention」那天）。
  **只保留课程特有技能**（Transformer/Attention/RoPE/SFT/LoRA/QLoRA/vLLM/ViT/CLIP/VLM/Pretraining/
  Inference Optimization）。**宁可少绑，不可错绑** —— 平台价值建立在因果可信上。
- 规则收紧后**必须 `--rebind`**（默认只填 `plan_day_id IS NULL`，旧错绑不会自动消失）。

**工具行为**
- ⚠️ **同一文件禁止并行 Edit**：写盘竞争 → 后提交者按旧快照整体覆盖，先提交的被**静默回滚**
  （工具仍报 success）。同文件多处修改必须**串行**；怀疑没落盘就 Grep 复读。
- **替换 docstring 片段时不要带 `"""`**：old/new_string 里出现收尾 `"""` 会提前闭合 docstring，
  余下 Args/Returns 变成裸代码 → `SyntaxError: invalid character '。'`。
  改完立刻 `py_compile.compile(f, doraise=True)` 验一遍再跑测试。
- Ardot SVG 对退化几何敏感：纯水平/垂直段报 "degenerate geometry"，**轴线加 1px 偏移**（`M180 180L181 40`）。

## 六、真实数据源

- 技能等级/证据单一源：`app/core/skill_profile.py`（改完跑 `scripts/seed_job_hunt.py` 校准）；
  `app/db/base.py` 只引用它，**不改副本**；`docs/MY_CONTEXT.md` 只写背景策略，不写等级。
- 赛道配置：`app/core/target_roles.py`（含 `SPRINT_START/END`、`TECH_BLACKLIST`）。
- 简历防虚构锚点：`resume_facts`（9）+ `/api/resume` 诊断。**EI 会议严禁虚标 SCI**。
