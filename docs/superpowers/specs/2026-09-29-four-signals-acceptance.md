# 四信号硬指标验收记录（spec §2.3）

> 2026-09-29 · 对应 spec 2026-09-24-mastery-unit-dual-loop-design.md §2.3
> 执行证据：backend/tests/e2e/ 四脚本（复跑方式见各信号）· pytest 523 passed / 2 skipped

## 逐信号打钩

| 信号 | 指标 | 机器验收 | 状态 |
|------|------|---------|------|
| 每天用得动 | 连续 14 天日流 | e2e_signal1（14 天模拟，≤25 调用/天代理 + 无死路=全 200） | ✅ PASS |
| 每天用得动 | OS 操作 ≤15 分钟/天 | 无法机器度量（步数代理见上）；体验目标待人工 | ⚠️ 代理达成，人工待跑 |
| 差距可量化 | 每条主张带证据引用 | e2e_signal2（26 条 gate≥1 主张全带 ref） | ✅ PASS |
| 差距可量化 | 缺口自动转明日施工单项 | **机制未实现**（现状：planner 缺口分析为通用分析，非证据缺口驱动） | ⏳ 缓：plan-3 后票据「evidence-gap→施工单项」 |
| 作品集说话 | 01_sft/02_lora/03_dpo 各 L2+ | e2e_signal3（经 record_evidence_event 直驱验证组装链路；真实性由日常流承担） | ✅ PASS（链路），真实素材日常积累中 |
| 作品集说话 | 13 节 README 非空 | e2e_signal3 | ✅ PASS |
| 考得住 | is_verified 单调不减 + 曲线记录 | e2e_signal4（0→1 + review_logs≥1） | ✅ PASS |
| 考得住 | 核心题库 is_verified 覆盖率 30 天内 ≥50% | 未度量（当前 dev DB verified=0） | ⏳ 缓：plan-3 后票据「覆盖率报表」 |

## 已绑定的后续票据
1. evidence-gap → 明日施工单项（spec §4.5 闭环最后一箭）
2. is_verified 覆盖率报表与 ≥50% 追踪
3. 半确认 suggestion UI（github confirm 现为 API-only）
4. （承接）rule→llm 重生成增强票

## 已知 E2E 代理口径（诚实声明）
- 信号 1 的「≤25 调用/天」是步数代理（脚本固定 ~6 调用/天），真实含义是"日流无死路且步数预算宽松"
- 信号 3 的 L2 证据由脚本直驱 record_evidence_event 造出——验证的是组装链路，不是素材真实性

## 复跑方式（执行证据）

```
cd backend && .venv/Scripts/python.exe tests/e2e/e2e_signal1_daily_flow.py   # → SIGNAL 1: PASS（14 天日流 ≤25 调用/天，无死路）
cd backend && .venv/Scripts/python.exe tests/e2e/e2e_signal2_gap.py          # → SIGNAL 2: PASS（26 条 gate≥1 主张全部带 evidence ref 引用）
cd backend && .venv/Scripts/python.exe tests/e2e/e2e_signal3_portfolio.py    # → SIGNAL 3: PASS（三模块 L2+，13 节 README 非空）
cd backend && .venv/Scripts/python.exe tests/e2e/e2e_signal4_verified.py     # → SIGNAL 4: PASS（is_verified 单调不减 0→1，review_logs=1）
```

四脚本输出见 `.superpowers/sdd/plan3-task-6-report.md`（各 EXIT=0、开发库指纹一致）。
e2e 脚本为手动验收单，不进 pytest 收集；pytest 门禁（2026-09-29 fix-wave 后）：

```
cd backend && .venv/Scripts/python.exe -m pytest tests/ -q --basetemp=../.workbuddy/tmp/pytest-base
→ 523 passed, 2 skipped（+1 = 门值响应 pin：test_event_promoted_gate_visible_in_evidence_responses）
```
