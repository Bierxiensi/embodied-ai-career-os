# 回退学习法设计（Rollback Learning Method）

> 2026-08-17 · 基于 brainstorming 产出 · 把 V0 验证有效的「回退」学习模式固化成默认流程
> 前身：`2026-08-13-task-scaffolding-design.md`（本设计在其上补三块，不推翻）

---

## 一、背景

2026-08-13 的 task-scaffolding 设计提出「Baseline + 必改项」，方向对，但漏了三步，导致 AI 又把必改项的**答案**写进了 baseline——用户还是没动手写，学习落空。

V0 实测后发现：**「回退（把答案删掉，只留空壳）→ 我写 → Trae 求助 → 错题集 → 验收」**这条回路，才让学习"清晰、效果好"（证据：`so101/v0_mujoco/MISTAKES.md` 里真实 debug 了 NaN 失稳、惯量、PD 增益、ctrlrange 语义，远超"跑通 demo"的深度）。

本设计把这条回路固化成默认流程。

---

## 二、核心方法：回退学习法

```
Claude（Coach / Planner）
  1. 写 baseline —— 可运行的骨架 + 非核心脚本 + README（含必改项定义 + 验收命令）
  2. 写必改项的完整答案 —— 存进 reference/ 文件夹
  3. 回退 —— 把工作区里必改项对应的核心代码删成 stub（只留签名 + docstring + TODO）

你（Learner）
  4. 在 Trae 里手写核心逻辑
  5. 卡住 → 问 Trae（即时求助，落在你正在挣扎的上下文里）
  6. 实在卡死 20 分钟 → 瞄 reference/ 一眼 → 回来继续
  7. 踩坑 → 记进 MISTAKES.md（现象 → 根因 → 排查 → 修复 → 口诀）

Claude（Reviewer）
  8. 跑验收命令 + 看 git diff（真重写 vs 抄 reference/）+ 问「为什么」
  9. PASS → milestone complete + 技能升级；FAIL → 给具体反馈
```

**一句话**：读答案是"识别"，写代码才是"建构"。回退用物理手段把前者逼成后者——答案不在工作区，就没得抄，缺口变成必须自己填的东西。

---

## 三、关键设计决策

### 3.1 回退边界（删多干净）

| 类别 | 处理 | 举例 |
|------|------|------|
| **保留**（AI 写，可直接跑） | 模型/配置文件、非核心工具脚本、README | `so101_arm.xml` 原始 3-DOF、`state_reader.py`、`verify_model.py` |
| **回退成 stub**（你写） | 每条必改项对应的核心逻辑文件 | `control_trajectory.py` 只留 `def interpolate_waypoints(...)` 空函数 |
| **参考答案**（存 reference/） | AI 的完整可运行版本，和 stub 一一对应 | `reference/control_trajectory.py` |

**stub 约定**：只保留函数签名 + docstring（说明输入输出）+ `# TODO: 你来实现` + `raise NotImplementedError`，**不含任何可运行的实现**。

### 3.2 参考答案位置

- 放在 `<workspace>/reference/`（如 `so101/v1_ros2/reference/`），**git 保留**（commit）。
- README 顶部写一句：**"先自己写，实在卡死再看 reference/"**。
- 文件名与 stub 对应：`control_trajectory.py` 的答案就是 `reference/control_trajectory.py`。

### 3.3 分工写死（什么自己写 / 什么问 Trae / 什么问 Claude）

| 任务 | 谁 | 为什么 |
|------|-----|--------|
| 核心逻辑、算法、模型结构 | **你**（硬啃，卡死才瞄 reference/） | 这是学习点，必须自己建构 |
| 语法 / API / 报错排查 | **Trae**（即时求助） | 卡住才问，帮助落在挣扎上下文 |
| 规划 / 回退 / 验收 | **Claude Code**（Coach/Reviewer） | 领域智能 + 客观验收，不能替你写答案 |

---

## 四、相对 2026-08-13 的三块补丁

1. **新增「回退」步骤**（§3.1/§3.2）—— 2026-08-13 只说"baseline = 参考答案"，没说"必改项答案必须从 baseline 删掉、存 reference/"。这是本次翻车的根因。
2. **错题集升为一等交付物**（§5）—— 2026-08-13 里没有 MISTAKES.md 的位置，但它才是"学到东西"的证据。
3. **「我写 / Trae / Claude」分工写死**（§3.3）—— 2026-08-13 只写了一句"用户在 Trae 里干活"，太含糊。

---

## 五、机械固化（自动执行，不靠每次手动喊）

### 5.1 Claude 记忆：自动回退

更新现有 project memory（`so101-v0-baseline-workflow`），把回退学习法写进去，让 Claude Code 以后**生成 baseline 时自动执行**三步：写答案 → 存 `reference/` → 回退成 stub。用户不再需要手动喊"回退"。

### 5.2 模板：每个 milestone 复制

建 `so101/_template/`，放两份模板，以后每个 V(n) 复制：

```
so101/_template/
  ├── MISTAKES.md      # 错题集模板（现象→根因→排查→修复→口诀 空表）
  └── README.md        # 里程碑 README 模板（含「先自己写，卡死再看 reference/」提示 + 必改项清单 + 验收命令）
```

`reference/` 目录由 Claude 在生成 baseline 时按 §3.1 现场建，不预置。

---

## 六、验收更新（Reviewer 新增三条检查）

1. **回退是否彻底** —— 工作区（不含 `reference/`）里，必改项对应文件必须是 stub（含 `TODO`/`NotImplementedError`，无完整实现）。
2. **错题集是否真实** —— MISTAKES.md 非空、记录了真实踩坑（不是占位）。
3. **是否真重写** —— git diff 显示核心逻辑是你写的，不是从 `reference/` 复制（配合「问为什么」判断）。

---

## 七、实施范围

### 包含

- 本设计文档（spec）
- Claude 记忆：自动回退行为
- `so101/_template/` 模板（MISTAKES.md + README.md）

### 不包含

- 后端任何改动（幂等、状态机、验收自动化）—— 属于方案 C，等 V1 跑顺再上（YAGNI）
- 前端改动
- Reviewer Agent 自动化（仍由 Claude Code 手工判断）

---

## 八、设计决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| 固化形态 | spec + Claude 记忆 + 模板（方案 B） | 最小成本把"回退"变默认；后端自动化留到 V1 后 |
| 参考答案位置 | `<workspace>/reference/`，git 保留 | 简单直接、找得到；写清"先自己写再看"把自律交给用户 |
| 回退粒度 | 删到 stub（签名+docstring+TODO），不含实现 | 留骨架有抓手，删实现才有缺口 |
| 错题集地位 | 一等交付物，Reviewer 检查 | 它是"学到东西"的证据，不是可选项 |
| 分工 | 你硬啃核心 / Trae 即时求助 / Claude 规划回退验收 | 各司其职，避免 AI 又替你写答案 |
