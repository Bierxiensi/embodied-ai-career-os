# Embodied AI Career OS v2.1 架构设计（增量）

> 配套：`CAREER_OS_V2_INCREMENTAL_PRD.md`
> 方法：基于真实代码映射，凡已有的一律复用，只列净新增与接缝点。

---

## 0. 模式机制（先定 canonical，已核实）

- **唯一实现**：`career_mode` 模块 = `models/career_mode.py` + `services/career_mode/{presets,service}.py` + `api/career_mode.py`（GET `/api/career-mode`、POST `/switch`、GET `/transitions`）。
- **已排除冲突**：旧的 `app-mode-and-radar-analysis.md` 配置方案（`APP_MODE` in config.py）**从未落地**——`core/config.py` 无 `app_mode` 字段，其阶段 2/3 被 `career_mode` 取代。审计中提到的"两套机制"顾虑不成立，特此更正。
- **当前缺口**：`LONG_TERM_TRANSITION` 在 `presets.py` 是空壳（`active_track_keys=()`/`frozen_track_keys=()`，注释"首期未定义"）。v2.1 必须补其赛道策略（见 PRD §1.2）。

```
                 CareerMode（当前阶段，单条 is_current）
                   ├─ Strategy：active_track_keys / frozen_track_keys / deadline
                   ├─ Action：/today 任务（受赛道过滤）
                   └─ Evidence：project/code/paper/experiment/interview
                        │
         ┌──────────────┼───────────────────────┐
         ▼              ▼                       ▼
      job_hunt      long_term_transition      （未来可加）
      (已激活)       (v2.1 激活+补赛道)         (留接口)
```

---

## 1. 数据模型增量

### 1.1 现有模型（复用，不重建）
career_goal / skill / skill_assessment / task / project / milestone / plan_day / day_artifact / day_progress / experiment / interview_question / interview_log / job_posting / job_match / job_application / resume_fact / paper / paper_chunk / career_mode / practice_record …（共 27+ 张）。

### 1.2 净新增模型（`models/phd.py`）
```python
class PhDTarget(Base):
    __tablename__ = "phd_target"
    id, university, school, department, program,
    study_mode,          # 全日制 / 非全
    admission_type,      # 申请-考核 / 统考
    requirements,        # 文本
    deadline,            # ISO 或 None
    note

class Advisor(Base):
    __tablename__ = "advisor"
    id, phd_target_id(FK), name, lab,
    research_directions(JSON),   # ["VLA","Robot Learning",...]
    robotics_resources(JSON),    # 机器人平台/机械臂等
    contacted(bool), contact_date,
    match_json(JSON)             # 六维匹配 + overall

class ResearchDirection(Base):
    __tablename__ = "research_direction"
    id, name, category,          # 计算机/控制/自动化/AI/机器人
    related_skills(JSON), embodied_relevance(0-5)
```

### 1.3 净新增模型（`models/skill_graph.py`）
```python
class SkillDependency(Base):
    __tablename__ = "skill_dependency"
    id, parent_skill, child_skill   # 如 ("PyTorch","Transformer")
```
> `skill_profile.SkillProfile` 增加可选 `domain: str | None` 字段（6 域），用于 R2 域聚合雷达。不破坏现有序列化（提供默认值）。

### 1.4 风险/ROI（不建表，纯函数）
`core/risk.py`、`core/career_roi.py` 为无状态计算，结果走现有 `/today` 与 `/dashboard` 响应，不新增持久化（除非后续要留历史，再加 `risk_snapshot` 表）。

---

## 2. API 增量

| 端点 | 方法 | 说明 | 文件 |
|---|---|---|---|
| `/api/career-mode` 等 | 已有 | 切 `long_term_transition` 用现成 `/switch` | `api/career_mode.py` |
| `/api/phd/targets` | GET/POST | 博士院校/项目 CRUD | 新增 `api/phd.py` |
| `/api/phd/advisors` | GET/POST | 导师 CRUD + 触发匹配 | 新增 `api/phd.py` |
| `/api/phd/match` | POST | 计算某 advisor 六维匹配 | 复用 `agents/match/engine.py` |
| `/api/risk` | GET | 七维风险快照 | 新增 `api/risk.py`（调 `core/risk.py`） |
| `/api/today` | 已有 | 增加 `roi_ranked_tasks` 与 `risk` 字段 | 改 `api/planner.py` 或 today 聚合 |
| `/api/dashboard` | 已有 | 增加 `phd_summary` / `academic` / `roi_top` | 改 `api/dashboard.py` |

> 所有写接口必须 Pydantic 入参 + 失败状态码 + 测试（继承 `CODEBUDDY_IMPLEMENTATION_CONSTRAINTS.md`）。

---

## 3. 前端增量

目录约定：`src/app/<route>/page.tsx` + `src/components/<Name>.tsx`（与现有一致）。

| 新增/改动 | 文件 | 说明 |
|---|---|---|
| 新增 | `src/app/phd/page.tsx` + `src/components/PhDAdvisorBoard.tsx` | 导师库、匹配度、联系倒计时、材料清单 |
| 改动 | `src/app/today/page.tsx` + `TodayTasks` | 顶部加 Risk Radar 条；任务区改 ROI 排序；academic/phd 卡片 |
| 改动 | `src/components/SkillRadarCard.tsx` | 支持 R2 域聚合（long_term 模式）；R1 岗位对齐（job_hunt） |
| 新增 | `src/components/RiskRadar.tsx` | 七维风险可视化（SVG，沿用现有零图表库约定） |
| 新增 | `src/components/RoiTaskList.tsx` | 今日最高 ROI 任务列表 |
| 改动 | `src/components/GlobalNav.tsx` | 模式切换器已存在？若不存在则加；增 phd 入口 |
| 新增 | `src/services/phdService.ts` / `riskService.ts` | API 客户端 |

---

## 4. 接缝点（最容易写错的地方）

1. **模式数据源唯一性**：赛道策略只能来自 `target_roles.py` + `career_mode/presets.py`，前端不得硬编码赛道清单（继承 `app-mode-and-radar-analysis.md` 的教训）。
2. **long_term_transition 激活前置**：`presets.py` 必须先填 `phd` 赛道，否则切过去无任务可推。
3. **ROI/风险不改数据只改展示**：与模式同理，纯函数输出，避免污染 `task` 表。
4. **SkillRadar R1/R2 口径一致性**：`readiness` 指标若随模式换轴，必须同步 `KpiCards`，否则两处数字对不上（历史 bug 类型）。
5. **博士匹配复用 match/engine**：不要为 PhD 新建一套相似度，调用现有 `agents/match/engine.py`。

---

## 5. 技术栈与门禁（不变）
- 后端 FastAPI + SQLAlchemy + SQLite（本地）/ PG（Compose）。迁移需 SQLite+PG 双跑（`tests/test_migration_dialect_compat.py`）。
- 前端 Next.js 16 + React 19 + TS + Tailwind v4（CSS-first）。
- 零第三方 UI/图表库（纯 SVG）；LLM 未配置时核心页面仍可工作。
- 静态门禁：后端 `py_compile`+`pytest`；前端 `tsc --noEmit` + `eslint` + `next build`。
