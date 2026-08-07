# Embodied AI Career OS · Day6 Agent 闭环稳定性测试报告

| 项目 | 值 |
|------|-----|
| 报告生成时间 | 2026-08-03 14:30 (Asia/Shanghai) |
| 测试范围 | Day6 全部 Agent 闭环逻辑（Planner Agent + Task 状态机 + 前后端联通） |
| 后端地址 | http://localhost:8000 |
| 前端地址 | http://localhost:3000 |
| 数据库 | backend/data/app.db (SQLite) |
| 后端测试用例 | 27 例（7 套件）|
| 前端 E2E 检查点 | 10 项 |
| **总通过率** | **100% (27/27 后端 + 10/10 前端)** |

---

## 一、执行摘要

Day6 是 Phase 1 的关键节点，项目从「展示 Demo」进入「真实系统」，形成第一个完整闭环：

```
点击"生成今日任务" (Client Component)
  ↓
POST /api/planner/generate (Next.js rewrites 代理)
  ↓
FastAPI Planner Agent (LangGraph 状态机)
  ↓
tasks 表持久化 + agent_runs 决策记录
  ↓
router.refresh() → Server Component 重新获取数据
  ↓
Dashboard 显示新任务
```

**结论：✅ Agent 闭环逻辑稳定，可进入 Day7。**

关键验证点：
1. Planner Agent 的 4 节点状态机（analyze_skill_gap → select_learning_target → generate_task → validate_task）逻辑正确
2. 技能缺口排序、current_focus 强制聚焦、energy_level 难度选择、时长截断等核心算法符合预期
3. tasks ↔ agent_runs 数据一致性 100%
4. Task 状态机 todo → doing → done 流转正常，非法状态被 422 拒绝
5. 并发 5 请求全部成功，单次响应 8ms
6. 前端 React hydration 正常，按钮 onClick 触发 API，任务列表实时刷新

---

## 二、测试环境

| 组件 | 版本 |
|------|------|
| Python | 3.14.4 |
| FastAPI | 0.115.0 |
| SQLAlchemy | 2.0.51 |
| LangGraph | 1.2.10 |
| Next.js | 16.2.12 (Turbopack) |
| React | 19.2.4 |
| 数据库 | SQLite (开发态，Phase2 切 PostgreSQL) |

测试前基线：`agent_runs=5, tasks=8`（Day6 开发过程中累积的数据）

---

## 三、后端 API 测试结果（27 例）

### 套件 1：功能测试（3/3 PASS）

| 用例 | 名称 | 结果 | 耗时 | 关键证据 |
|------|------|------|------|----------|
| F-01 | 正常生成任务（Isaac 最大缺口）+ 持久化 + agent_runs | ✅ PASS | 22ms | selected_skill=Isaac, task_id=9, duration=45 |
| F-02 | current_focus 强制聚焦技能（覆盖自动选择） | ✅ PASS | 7ms | forced_skill=ROS2（Isaac 缺口更大但被 focus 覆盖） |
| F-03 | agent_runs 记录内容完整性（input + output JSON） | ✅ PASS | 0ms | input_keys=[available_minutes, skills, ...], output_keys=[title, skill, ...] |

**覆盖的逻辑分支**：
- `analyze_skill_gap`：gap 降序排序 ✓
- `select_learning_target`：自动选择（最大缺口）+ current_focus 强制覆盖 ✓
- `agent_runs` 写入：input_context + output_result 完整 ✓

### 套件 2：边界测试（7/7 PASS）

| 用例 | 名称 | 结果 | 耗时 | 关键证据 |
|------|------|------|------|----------|
| B-01 | 空 skills 列表 → fallback 通用任务 | ✅ PASS | 7ms | title="Unknown 学习与实践", difficulty=beginner |
| B-02 | 未知技能（无模板）→ fallback 通用任务 | ✅ PASS | 7ms | title="QuantumComputing 学习与实践", acceptance=3 条 |
| B-03 | 极端时长 available_minutes=5（最小值截断） | ✅ PASS | 7ms | duration=5 (min(5, 60)=5) |
| B-04 | 极端时长 available_minutes=480（取模板基准） | ✅ PASS | 7ms | duration=60 (min(480, 60)=60) |
| B-05 | energy_level=low → beginner 难度 | ✅ PASS | 7ms | difficulty=beginner |
| B-06 | energy_level=high → intermediate 难度 | ✅ PASS | 6ms | difficulty=intermediate |
| B-07 | gap 相同时 level 低的优先（排序稳定性） | ✅ PASS | 6ms | selected=ROS2 (gap=2,level=1 优先于 gap=2,level=2) |

**覆盖的边界场景**：
- 空输入、未知技能 → `_fallback_task` 兜底 ✓
- 时长截断逻辑 `min(available, base_minutes)` ✓
- 能量→难度映射 `ENERGY_TO_DIFFICULTY` ✓
- 排序稳定性 `sort(key=(-gap, level))` ✓

### 套件 3：数据一致性测试（3/3 PASS）

| 用例 | 名称 | 结果 | 耗时 | 关键证据 |
|------|------|------|------|----------|
| C-01 | 持久化 task 字段与 Planner 输出完全一致 | ✅ PASS | 7ms | task_id=10, all_fields_match=true（7 个字段全部比对） |
| C-02 | agent_runs input/output 与请求/响应对应 | ✅ PASS | 8ms | input_match=true, output_match=true |
| C-03 | persist=False 时 tasks 不变 + agent_runs 仍记录 | ✅ PASS | 8ms | tasks_delta=0, agent_runs_delta=1 |

**验证的字段一致性**（C-01）：title / skill_name / duration / difficulty / status / acceptance / resources 全部匹配。

**关键设计验证**（C-03）：`persist=False` 仅跳过 tasks 表写入，agent_runs 决策记录始终保留——这正是「Agent 决策可追溯」设计的核心。

### 套件 4：Task 状态机测试（2/2 PASS）

| 用例 | 名称 | 结果 | 耗时 | 关键证据 |
|------|------|------|------|----------|
| S-01 | Task 状态机 todo → doing → done 完整流转 | ✅ PASS | 25ms | task_id=12, flow=todo→doing→done ✓ |
| S-02 | 非法状态 cancelled 被 422 拒绝 | ✅ PASS | 9ms | http=422 (pattern=^(todo\|doing\|done)$) |

**验证的状态机约束**：Pydantic `TaskStatusPatch.status` 的正则约束生效，非法状态无法写入数据库。

### 套件 5：稳定性测试（3/3 PASS）

| 用例 | 名称 | 结果 | 耗时 | 关键证据 |
|------|------|------|------|----------|
| ST-01 | 连续 5 次调用全部成功 | ✅ PASS | 34ms | success=5/5 |
| ST-02 | 并发 5 个请求（线程池）全部成功 | ✅ PASS | 31ms | concurrent_success=5/5 |
| ST-03 | 单次响应时间 < 2s | ✅ PASS | 7ms | elapsed_s=0.008 (8ms) |

**稳定性结论**：
- 连续调用无状态泄漏（Planner graph 编译一次复用，无状态设计正确）
- 并发安全：SQLite `check_same_thread=False` + FastAPI 同步路由 + SQLAlchemy 会话 per-request，5 并发无冲突
- 性能：8ms 响应（rule generator 无外部依赖，远低于 2s 阈值）

### 套件 6：错误处理测试（5/5 PASS）

| 用例 | 名称 | 结果 | 耗时 | 关键证据 |
|------|------|------|------|----------|
| E-01 | 缺少必填字段 skills → 422 | ✅ PASS | 2ms | http=422 |
| E-02 | available_minutes=1 超范围 → 422 | ✅ PASS | 2ms | http=422 (Field(ge=5)) |
| E-03 | available_minutes=500 超范围 → 422 | ✅ PASS | 1ms | http=422 (Field(le=480)) |
| E-04 | skill level=6 超范围 → 422 | ✅ PASS | 1ms | http=422 (Field(ge=0, le=5)) |
| E-05 | 不存在的 task_id 状态更新 → 404 | ✅ PASS | 2ms | http=404 |

**验证的校验层**：Pydantic Field 约束（ge/le）+ FastAPI HTTPException（404）全部生效。

### 套件 7：CRUD 端点测试（4/4 PASS）

| 用例 | 名称 | 结果 | 耗时 | 关键证据 |
|------|------|------|------|----------|
| A-01 | GET /api/career 返回正确结构 | ✅ PASS | 3ms | target_role=Robot AI Engineer |
| A-02 | GET /api/skills 返回技能列表（≥10） | ✅ PASS | 3ms | skills_count=10 |
| A-03 | GET /api/tasks 返回任务列表 | ✅ PASS | 4ms | tasks_count=13 |
| A-04 | PATCH /api/skills/{id} 更新等级 + 恢复 | ✅ PASS | 19ms | skill_id=1, temp_level=4, restored=true |

**验证的 Day6 API 范围**（遵循用户调整1：Read + Minimal Update）：
- Career: GET + PUT ✓
- Skill: GET + PATCH ✓
- Task: GET + POST + PATCH ✓
- 无 DELETE（历史任务服务 Day7 Reviewer Agent）✓

---

## 四、前端 E2E 测试结果（10/10 PASS）

通过浏览器自动化验证前后端联通闭环：

| 检查项 | 结果 | 证据 |
|--------|------|------|
| 页面加载（/dashboard） | ✅ PASS | 标题、职业目标、雷达图、任务列表、按钮全部渲染 |
| React hydration | ✅ PASS | hasReactProps=true, onClickBound=true |
| 初始任务数量 | ✅ PASS | 8 项 |
| 点击"生成今日任务"按钮 | ✅ PASS | 按钮点击成功触发 |
| 成功提示显示 | ✅ PASS | "✓ 已生成任务：Isaac Sim 基础环境搭建（已入库 #14）" |
| 任务列表刷新 | ✅ PASS | 8 项 → 14 项（含历史累积任务） |
| POST /api/planner/generate 请求 | ✅ PASS | status=200, failed=false |
| 控制台错误检查 | ✅ PASS | 无 error 级别日志 |
| 最终状态截图 | ✅ PASS | 成功提示 + 任务列表更新一致 |
| **整体闭环** | ✅ **PASS** | 点击 → API → DB → 刷新 → 展示 |

---

## 五、发现的问题与修复记录

### 问题 1：React 未 hydrate（已修复）

| 项目 | 内容 |
|------|------|
| 现象 | 点击"生成今日任务"按钮无反应，按钮不变 disabled，不发出 API 请求 |
| 根因 | Next.js 16 默认阻止跨域 dev 资源（`/_next/webpack-hmr`），沙箱预览域名访问 localhost:3000 时 client component 的 JS chunk 被阻止加载，导致 React 无法 hydrate |
| 诊断证据 | `browser_evaluate` 检查按钮 `reactKeys=[]`, `hasPropsKey=false`, `onClickType="NO_PROPS_KEY"` |
| 修复 | `next.config.ts` 添加 `allowedDevOrigins` 放行沙箱预览域名 |
| 修复后验证 | `hasReactProps=true`, `onClickBound=true`, 点击触发 API 200 |

### 问题 2：Pydantic 验证错误（已修复，前序会话）

| 项目 | 内容 |
|------|------|
| 现象 | 数据库 JSON 字段为 None 时，`TaskOut.resources` / `SkillOut.evidence` 期望 list 报错 |
| 修复 | 添加 `field_validator(mode="before")` 将 None 转为空列表 |
| 验证 | F-01 / C-01 用例通过，acceptance/resources 字段正确返回列表 |

---

## 六、Planner Agent 状态机逻辑验证

测试覆盖了 LangGraph 4 节点的所有关键路径：

```
START → analyze_skill_gap → select_learning_target → generate_task → validate_task → END
```

| 节点 | 验证用例 | 逻辑 |
|------|----------|------|
| analyze_skill_gap | B-07 | gap 降序，gap 相同时 level 升序（更薄弱优先） |
| select_learning_target | F-02, B-01 | current_focus 非空→强制聚焦；否则取 gaps[0]；空→"Unknown" |
| generate_task | B-01~B-06 | rule generator：模板匹配 / fallback 兜底 / 时长截断 / 能量→难度 |
| validate_task | F-01 | 必填字段校验（title/skill/duration/acceptance/status） |

**可插拔生成器验证**：`generator="rule"` 正常工作，`generator="llm"` 预留（LLMGenerator 已有骨架，需配置 API key 后启用）。

---

## 七、稳定性结论

| 维度 | 结论 | 依据 |
|------|------|------|
| 功能正确性 | ✅ 稳定 | 27 例 API 测试 + 10 项 E2E 全通过 |
| 边界鲁棒性 | ✅ 稳定 | 空输入/未知技能/极端时长/非法状态全部正确处理 |
| 数据一致性 | ✅ 稳定 | tasks ↔ agent_runs 字段 100% 匹配，persist 语义正确 |
| 并发安全 | ✅ 稳定 | 5 并发请求无冲突（SQLite + per-request session） |
| 性能 | ✅ 优秀 | 单次响应 8ms（rule generator，无外部依赖） |
| 错误处理 | ✅ 稳定 | 422/404 状态码正确返回，Pydantic 约束生效 |
| 前后端联通 | ✅ 稳定 | Next.js rewrites 代理 + React hydration 正常 |

---

## 八、待优化项（非阻塞，建议 Day7+ 处理）

| 优先级 | 项目 | 说明 |
|--------|------|------|
| 低 | agent_runs 查询 API | Day6 仅建表写入，Day7+ 需增加 GET /api/agent_runs 供 Debug UI 展示 |
| 低 | LLM Generator | rule generator 确定性高但模板有限，Phase2 接入 LLM 后需补充 LLM 专用测试 |
| 低 | PostgreSQL 迁移 | SQLite 并发写入有限，Phase2 切 PostgreSQL 后需重跑 ST-02 并发测试 |
| 低 | 响应结构升级 | Phase3 升级 ApiResponse 增加 trace_id / token_usage（当前简化版满足 Day6） |

---

## 九、附录

### 测试脚本
- 后端测试套件：[backend/tests/test_agent_closure.py](file:///workspace/embodied-ai-career-os/backend/tests/test_agent_closure.py)
- JSON 报告：[backend/reports/day6_agent_test_20260803_142945.json](file:///workspace/embodied-ai-career-os/backend/reports/day6_agent_test_20260803_142945.json)

### 复现命令
```bash
# 启动后端
cd backend && uvicorn app.main:app --port 8000

# 启动前端
cd frontend && npm run dev

# 执行后端测试套件
cd backend && python tests/test_agent_closure.py
```

### 测试覆盖的文件
- [backend/app/api/planner.py](file:///workspace/embodied-ai-career-os/backend/app/api/planner.py) — Planner API 路由
- [backend/app/agents/planner/graph.py](file:///workspace/embodied-ai-career-os/backend/app/agents/planner/graph.py) — LangGraph 状态机
- [backend/app/agents/planner/nodes.py](file:///workspace/embodied-ai-career-os/backend/app/agents/planner/nodes.py) — 4 节点逻辑
- [backend/app/agents/planner/generators/rule_generator.py](file:///workspace/embodied-ai-career-os/backend/app/agents/planner/generators/rule_generator.py) — 规则生成器
- [backend/app/api/tasks.py](file:///workspace/embodied-ai-career-os/backend/app/api/tasks.py) — Task 状态机 API
- [backend/app/models/agent_run.py](file:///workspace/embodied-ai-career-os/backend/app/models/agent_run.py) — Agent 执行记录
- [frontend/src/components/GenerateTaskButton.tsx](file:///workspace/embodied-ai-career-os/frontend/src/components/GenerateTaskButton.tsx) — 前端触发组件
- [frontend/src/app/dashboard/page.tsx](file:///workspace/embodied-ai-career-os/frontend/src/app/dashboard/page.tsx) — Server Component
