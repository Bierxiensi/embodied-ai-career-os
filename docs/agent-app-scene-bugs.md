# "Agent 应用" 场景界面分析 + Bug 修复

> 场景对应前端路由：`frontend/src/app/agents/page.tsx`（Server Component）
> 渲染链：`agents/page.tsx` → `GlobalNav` + `AgentOverview` → `AgentActivityCard`

## 一、界面设计评估

整体采用项目的 Apple 风格设计 token（light 主题、`--color-canvas` / `--color-card` / 圆角 18px / 发丝边框），布局合理：

- 顶部黑色 GlobalNav + 次级标题栏
- 页面头：kicker `MULTI-AGENT SYSTEM` + H1 `Agent 工作台` + 副标题
- `AgentOverview`：概览统计条（总调用 / 成功率 / 失败数 / 平均耗时）+ Agent 过滤 chips
- `AgentActivityCard`（`interactive` 模式）：可展开 trace、失败项一键重试

**设计亮点**：统计条 + 过滤 + 可展开 trace/重试 的组合是合格的可观测性入口；trace 用 `inputContext` / `outputResult` 的 JSON 展示，信息密度合适。

## 二、发现的 Bug 与修复

| # | 问题 | 严重程度 | 位置 | 修复 |
|---|------|---------|------|------|
| 1 | **导航无当前页高亮**：`GlobalNav` 把"概览"硬编码为白色高亮，进入 `/agents`、`/projects` 后仍高亮"概览"，其余链接永远灰色 | 高 | `components/GlobalNav.tsx` | 改用 `usePathname` 按路由计算 active 态（`/agents`、`/projects`、`/dashboard` 正确高亮） |
| 2 | **执行动态被截断**：`AgentActivityCard` 用 `runs.slice(0,5)`，Agents 页拉取 50 条却只显示 5 条，主入口看不到全部数据 | 高 | `components/AgentActivityCard.tsx` | 新增 `limit` 属性（默认不限制）；Dashboard 显式传 `limit={5}` 保持紧凑，Agents 页不传 → 显示全部 |
| 3 | **React key 用数组下标**：`key={idx}` 在展开/重试状态按 `run.id` 维护时存在协调隐患 | 中 | `components/AgentActivityCard.tsx` | 改为 `key={run.id}` |
| 4 | **副标题误导**："本周 X 次调用"在按 Agent 过滤后展示的是过滤子集数量，措辞失真 | 中 | `components/AgentActivityCard.tsx` | 改为准确的"X 条记录 · 成功率 Y%" |
| 5 | **次级标题与场景名不一致**：页面次级栏标题为 "Agent"，与场景名"Agent 应用"脱节 | 低 | `app/agents/page.tsx` | 次级栏标题改为 "Agent 应用" |

## 三、改动文件清单

- `frontend/src/components/GlobalNav.tsx` — 加 `"use client"` + `usePathname`，active 态逻辑
- `frontend/src/components/AgentActivityCard.tsx` — 加 `limit` prop、`key={run.id}`、副标题措辞
- `frontend/src/components/Dashboard.tsx` — `<AgentActivityCard limit={5} />`
- `frontend/src/app/agents/page.tsx` — 次级栏标题 "Agent 应用"
- `frontend/src/components/SubNav.tsx` — 加可选 `title` prop（默认 "概览"）
- `frontend/src/app/agents/page.tsx` — 复用 `<SubNav title="Agent 应用" skills={skills} />`

## 四、验证

- `tsc --noEmit` 通过（exit 0，无类型错误）。
- 未做整包 `next build`（改动为纯展示层，类型已校验）；建议 `cd frontend && npm run dev` 后在 `/agents` 目测：导航高亮、列表不再截断、过滤后副标题准确。

## 五、设计一致性改进（已实施）

用户确认后，将上一轮"可选后续"两项落地：

| # | 改进 | 位置 | 做法 |
|---|------|------|------|
| 6 | **Agents 次级栏补齐日期 + 生成今日任务按钮** | `app/agents/page.tsx` + `components/SubNav.tsx` | `SubNav` 增加可选 `title` prop（默认 "概览"）；Agents 页改渲染 `<SubNav title="Agent 应用" skills={skills} />`，与 Dashboard 次级栏视觉一致 |
| 7 | **副标题补 `Supervisor`** | `app/agents/page.tsx` | 副标题改为 `· Planner / Reviewer / Career / Research / Supervisor`，与 `KNOWN_AGENTS` / `AgentName` 一致 |

**健壮性**：Agents 页并发拉 `getSkills()`，并用 `.catch(() => [] as Skill[])` 隔离——即使技能接口故障，也不会击穿整个 Agent 页面（执行动态照常展示）。

二次 `tsc --noEmit` 仍通过（exit 0）。
