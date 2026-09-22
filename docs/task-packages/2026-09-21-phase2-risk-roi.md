# Phase 2 任务包 · 风险雷达 + Career ROI（下发 hy3 · 2026-09-21）

> 交付方式：把 §一～§六 整段复制给 hy3 会话即可开工。
> 设计依据：docs/CAREER_OS_V2_INCREMENTAL_PRD.md §3.2/3.3 + docs/CAREER_OS_V2_DEVELOPMENT_PLAN.md Phase 2。
> 本包已把全部口径决策（公式/阈值/数据源）定死——你只做翻译，不做设计。

---

## 一、任务包正文（复制给 hy3）

【目标】实现 v2.1 Phase 2：七维风险雷达 + Career ROI 任务排序，接入 /api/plan/today 与 /today 页面。规则纯函数驱动，无 LLM 依赖，LLM 未配置时全部功能可用。

【改动文件】（只许动这些）

新建：
- `backend/app/core/risk.py` —— 七维风险纯函数（含被 /api/job-hunt 复用的达标率计算）
- `backend/app/core/career_roi.py` —— ROI 纯函数
- `backend/app/api/risk.py` —— GET /api/risk
- `backend/app/schemas/risk.py` —— RiskOut / RoiTaskOut
- `backend/migrations/0024_phd_advisors_contacted.sql`
- `backend/migrations/0025_phd_advisors_contact_date.sql`
- `backend/tests/test_risk.py`、`backend/tests/test_career_roi.py`
- `frontend/src/components/RiskRadar.tsx`、`frontend/src/components/RoiTaskList.tsx`

修改：
- `backend/app/models/phd.py` —— PhDAdvisor 加 `contacted` / `contact_date` 两列
- `backend/app/schemas/phd.py` —— PhDAdvisorOut/Patch 加同名字段
- `backend/app/api/plan.py` —— get_today 附加 `risk` 与 `roi_ranked_tasks`
- `backend/app/schemas/plan.py` —— TodayView 加 `risk: RiskOut | None = None` 与 `roi_ranked_tasks: list[RoiTaskOut] = []`（向后兼容默认值）
- `backend/app/api/job_hunt.py` —— roles_out 的 strict 计算改调 core/risk.py 的共享函数（口径同源，行为不变）
- `backend/app/main.py` —— 注册 risk_router
- `frontend/src/services/planService.ts` —— TodayView 类型加 risk/roiRankedTasks 映射
- `frontend/src/app/today/page.tsx` —— 顶部插 RiskRadar、任务区后插 RoiTaskList
- `frontend/src/components/GlobalNav.tsx` —— 不动（today 已在导航）

【规格 A · 七维风险】`core/risk.py`

维度输出统一为 `{key, label, level, reason}`，level ∈ "green" | "amber" | "red"。函数签名（全部标量入参，today 可注入，模式镜像 agents/phd/agent.py 的 PhDMatchEngine）：

```python
def compute_risk(
    days_since_last_experiment: int | None,     # None = 从未有实验
    days_since_last_code_artifact: int | None,  # None = 从未有 code 产物
    defense_deadline_days: int,                 # 距 2026-12-31 答辩的天数
    has_defense_task: bool,                     # 是否存在标题/目标含"答辩"的任务
    contacted_advisors: int,                    # phd_advisors.contacted=True 计数
    phd_window_days: int,                       # 距 2026-11-01（导师联系窗口）天数
    main_track_strict_pct: int,                 # 主攻赛道严格达标率 0-100
    main_track_gap_ratio: float,                # 主攻赛道 gap>0 技能占比 0-1
    today: date | None = None,
) -> RiskResult   # .dimensions: list[dict], .overall_level: str（取最差维度）
```

规则（阈值已定死，不得自行调整）：

| 维度 | key | 规则 |
|------|-----|------|
| 执行力 | execution | 两项均 >7 天（或 None）→ red；任一 >3 天 → amber；否则 green |
| 学术 | academic | defense_deadline_days < 90 且无答辩任务 → red；<90 有任务 → amber；≥90 → green |
| 博士 | phd | phd_window_days < 45 且 contacted_advisors == 0 → red；<45 且 1-2 人 → amber；其余 green |
| 技能 | skill | main_track_strict_pct < 20 → red；<40 → amber；≥40 → green |
| 职业 | career | main_track_gap_ratio > 0.6 → amber；否则 green |
| 公司 | company | 恒 green，reason="已确认留任，在职转型窗口 2026.09–2027.03"（常量，配置在文件顶部） |
| 财务 | financial | 恒 green，reason="在职收入稳定"（常量） |

同文件提供（供 job_hunt 复用，消除双实现）：

```python
def track_strict_pct(required_skills: list[str], required_level: int,
                     skill_levels: dict[str, int]) -> tuple[int, int, int]:
    """返回 (strict_pct, qualified_count, required_count)。skill_levels 键为小写规范名。"""
```
`api/job_hunt.py` 的 roles_out 改调此函数，**输出字段名与数值必须与现状完全一致**（llm 当前 67%/23%/3/13，改完不得变）。

API 层取数（`api/risk.py`）：experiments 表 max(created_at)；day_artifacts 中 kind='code' 的 max(created_at)；tasks 里 title/objective 含"答辩"的 exists；phd_advisors contacted 计数；主攻赛道（TARGET_ROLES priority=="主攻"）strict/gap 用 track_strict_pct + Skill 表。

【规格 B · Career ROI】`core/career_roi.py`

```python
WEIGHTS = {"skill_delta": 0.3, "goal_relevance": 0.3, "evidence_value": 0.2, "real_project": 0.2}

def compute_task_roi(
    skill_name: str | None,
    skill_gap: int,                # 该技能 target_level - level（无技能传 0）
    track_keys_active: tuple[str, ...],       # 当前 CareerMode 的 active_track_keys
    main_track_required: list[str],           # 主攻赛道 required_skills（小写比较）
    task_source: str,              # user / seed / planner
    duration_minutes: int | None,
) -> RoiResult   # .roi: float, .reasons: list[str]
```

各维归一 0-1（启发式 v1，注释标注"可配置"）：
- skill_delta = min(skill_gap, 3) / 3（gap 越大越值钱；无关联技能 = 0.2 保底）
- goal_relevance = skill ∈ main_track_required → 1.0；task 带 track_key 且 ∈ active → 0.6；其余 0.3
- evidence_value = skill_name 非空 → 0.7；空 → 0.3
- real_project = source == "planner" → 0.8；"user" → 0.6；"seed" → 0.5
- roi = (Σ weight×dim) × (40 / max(duration or 40, 20))  —— 短任务增益、长任务打折，cap 1.5

`get_today` 里对当日 tasks 计算 roi，取 Top5 降序放 `roi_ranked_tasks`（元素含 task id/title/skill_name/roi/reasons）。**不改 tasks 原有排序**，ROI 列表是附加视图。

【规格 C · 迁移】

`0024_phd_advisors_contacted.sql`：单语句 `ALTER TABLE phd_advisors ADD COLUMN contacted BOOLEAN NOT NULL DEFAULT FALSE;`
`0025_phd_advisors_contact_date.sql`：单语句 `ALTER TABLE phd_advisors ADD COLUMN contact_date TIMESTAMP;`
（单语句/无分号注释/SQLite 写法，镜像 0021-0023；跑前 `cp backend/data/app.db backend/data/app.db.bak-20260921-phase2`）

【规格 D · 前端】

- RiskRadar.tsx：纯 SVG 七轴雷达（镜像 SkillRadarCard 的画法），轴色按 level：red=var(--color-rose) amber=var(--color-amber) green=var(--color-emerald)，白底卡片+hairline+18px 圆角，禁硬编码 hex；下挂每维一行 reason 文本。
- RoiTaskList.tsx：Top5 列表，每行 title + skill + roi 两位小数 + reasons chips。
- today/page.tsx：RiskRadar 放 PageHeader 之后、TodayBoard 之前；RoiTaskList 放 TodayBoard 之后。TodayBoard.tsx 本身**不许改**。

【验收命令】（全部贴输出）

```bash
# 1. 迁移（从 backend/ 目录运行；或用绝对路径 backend/.venv/Scripts/python.exe 避开 Git Bash shim 缺 cd）
.venv/Scripts/python.exe migrations/run_migration.py   # 0024/0025 applied
# 2. 后端全量（不是子集！从 backend/ 目录运行）
.venv/Scripts/python.exe -m pytest tests/ -q           # 基线 288 passed / 4 failed（test_plan_api 日期驱动）/ 2 skipped，不得新增失败
# 3. 重启后端后 curl 新端点（127.0.0.1，不用 localhost）
curl http://127.0.0.1:8000/api/risk                    # 200，data.dimensions 长 7，含 overall_level
curl "http://127.0.0.1:8000/api/plan/today"            # 200，data.risk 非空，data.roi_ranked_tasks 数组
curl http://127.0.0.1:8000/api/job-hunt                # llm match_pct=67 / strict_pct=23（口径回归锚点，变了即错）
# 4. 前端门禁（本机 Git Bash shim 既无 node 又缺 cd；用 managed node 绝对路径 + python chdir 包装）
#    标准 shell（node on PATH + cwd=frontend）可直接用：node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json
C:/Users/zxy_2/.workbuddy/binaries/python/versions/3.13.12/python.exe -c "import os,subprocess; os.chdir('D:/work/embodied-ai-career-os/frontend'); subprocess.run(['C:/Users/zxy_2/.workbuddy/binaries/node/versions/22.22.2-3/node.exe','node_modules/typescript/bin/tsc','--noEmit','-p','tsconfig.json'])"
C:/Users/zxy_2/.workbuddy/binaries/python/versions/3.13.12/python.exe -c "import os,subprocess; os.chdir('D:/work/embodied-ai-career-os/frontend'); subprocess.run(['C:/Users/zxy_2/.workbuddy/binaries/node/versions/22.22.2-3/node.exe','node_modules/eslint/bin/eslint.js','-c','eslint.config.mjs','src/components/RiskRadar.tsx','src/components/RoiTaskList.tsx','src/app/today/page.tsx','src/services/planService.ts'])"
```

【禁止事项】

1. 不得改 TodayBoard.tsx / task_scope.py / presets.py / target_roles.py / skill_profile.py
2. 不得改 match_pct 的算法；job_hunt 改造后 llm 67%/23% 必须逐字节不变
3. 不得给 risk/roi 接 LLM（纯规则，PRD 非目标第 4 条）
4. 迁移禁 PG 专属语法；改迁移必跑 tests/test_migration_dialect_compat.py
5. 测试不得写开发库（conftest 已处理，勿自建临时库、勿 import 期 unlink）
6. Pydantic v2 from_attributes 的 NULL → before 回落；service 层不透传 payload
7. 样式一律 var(--color-*)；组件单默认导出 PascalCase
8. 同一文件禁止并行 Edit；改完 Grep 复读关键行
9. next build 不用跑（当前环境 fonts.googleapis.com 不通，已知环境问题）

【完成后必做】（缺一即视为未完成）

1. 杀掉 8000 端口旧进程重启 uvicorn，curl 实测 /api/risk、/api/plan/today、/api/job-hunt 三条全 200（先跑 `date` 确认今天日期）
2. 全量 pytest 结果贴出（对照基线 288/4/2）
3. tsc + eslint 的 RC 贴出
4. `git diff --stat` 核对改动文件 = 【改动文件】清单，多一个都要说明
5. 日志写入 `.workbuddy/memory/当天日期.md`（今天几号先确认，别写错）

---

## 二、验收复核清单（高端模型/人工抽查用，不给 hy3）

| # | 抽查点 | 预期 |
|---|--------|------|
| 1 | `git diff --stat` 范围 | 与改动文件清单一致，TodayBoard/task_scope/presets/target_roles 零改动 |
| 2 | /api/job-hunt llm 三元组 | 67 / 23 / 3（13）逐项不变（口径回归锚点） |
| 3 | 人为造数验证 execution 维 | 库里最近实验 >7 天时 execution=red（当前库实测即应 red） |
| 4 | risk 测试的 today 注入 | 测试用固定 date，不依赖真实日历 |
| 5 | 迁移双跑 | test_migration_dialect_compat 全绿 + PG 方言翻译零残留 |
| 6 | 前端 RiskRadar | 无 hex 硬编码（grep `#[0-9a-fA-F]{3,6}` 应零命中） |
