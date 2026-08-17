# 回退学习法固化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 V0 验证有效的「回退 → 我写 → Trae 求助 → 错题集 → 验收」学习回路固化为默认流程：Claude 生成 baseline 时自动回退，每个 milestone 有模板可复制。

**Architecture:** 三部分落地——(1) Claude 记忆：生成 baseline 时自动执行「写答案→存 reference/→回退成 stub」；(2) `so101/_template/` 物理模板目录：MISTAKES.md + README.md 模板，每个 V(n) 复制；(3) spec 文档已就位（2026-08-17-rollback-learning-method-design.md）。全部为文档/模板/记忆改动，零代码、零测试、零后端改动。

**Tech Stack:** Markdown · Claude Code project memory · 现有 `so101/` 目录结构

## Global Constraints

- 后端、前端、数据库**零改动**（spec §七「不包含」；方案 C 等 V1 后）
- 不做自动化验收（Reviewer 仍由 Claude Code 手工判断）
- 参考实现必须存 `<workspace>/reference/`，**git 保留**（commit），不能删除
- stub 只保留「函数签名 + docstring + `# TODO` + `raise NotImplementedError`」，**不含可运行实现**
- 模板文件命名：`MISTAKES.md`、`README.md`（与 V0 现有命名一致）
- README 模板顶部必须含「先自己写，卡死再看 reference/」提示

---

### Task 1: 更新 Claude 记忆（自动回退行为）

**Files:**
- Modify: `C:\Users\zxy_2\.claude\projects\d--work-embodied-ai-career-os\memory\so101-v0-baseline-workflow.md`
- Modify: `C:\Users\zxy_2\.claude\projects\d--work-embodied-ai-career-os\memory\MEMORY.md`

**Interfaces:**
- Consumes: 现有 `so101-v0-baseline-workflow.md`（memory，type: project）
- Produces: 一条可被后续所有 Claude 会话加载的工作流记忆，涵盖「回退学习法」完整行为

- [ ] **Step 1: 更新 `so101-v0-baseline-workflow.md`，加入回退学习法**

在文件的「3 个必改项」小节之后、`**Why:**` 之前，插入「回退学习法」小节。核心内容（照抄下面的实际文案，保持 `**Why:**`/`**How to apply:**` 风格一致）：

```markdown
## 回退学习法（Rollback Learning Method）

生成 baseline 时，Claude 必须自动执行三步，不需要用户手动喊「回退」：

1. **写完整答案**：每个必改项对应的核心代码完整可运行版
2. **存 reference/**：把答案放进 `<workspace>/reference/`，git commit 保留
3. **回退成 stub**：工作区对应文件只留 函数签名 + docstring + `# TODO: 你来实现` + `raise NotImplementedError`，删掉所有可运行实现

**分工**：核心逻辑 = 用户硬啃（卡死 20 分钟才瞄 reference/）；语法/API/报错 = 用户问 Trae；规划/回退/验收 = Claude Code。

**验收**：Reviewer 跑验收命令 + 看 git diff（真重写 vs 抄 reference/）+ 问「为什么」。错题集 MISTAKES.md 非空且记录真实踩坑。
```

- [ ] **Step 2: 更新 `MEMORY.md` 索引行，补充回退学习法**

把现有行改为（一行一条）：

```markdown
- [SO101 V0 Baseline 工作流](so101-v0-baseline-workflow.md) — AI Coach 模式：AI 写 baseline，用户动手改代码，3 个必改项
- [回退学习法](so101-v0-baseline-workflow.md#回退学习法rollback-learning-method) — baseline 生成时自动存 reference/ + 回退成 stub；错题集一等交付物
```

- [ ] **Step 3: 验证**

打开更新后的 `so101-v0-baseline-workflow.md`，确认：(a) 新增小节含完整三步；(b) 无遗漏的 TODO；(c) `**Why:**` 和 `**How to apply:**` 保持原样。memory 文件不在 git 仓库内，无需 commit。

---

### Task 2: 建 `so101/_template/` 模板目录

**Files:**
- Create: `so101/_template/MISTAKES.md`
- Create: `so101/_template/README.md`

**Interfaces:**
- Consumes: V0 的 `so101/v0_mujoco/MISTAKES.md` 结构（现象→根因→排查→修复→口诀）与 `README.md` 结构
- Produces: 两个模板文件，供每个 V(n) milestone 复制

- [ ] **Step 1: 创建 `so101/_template/MISTAKES.md`**

写错题集模板（空表 + 示例，沿用 V0 的「坑 N」编号结构）。内容：

```markdown
# {Milestone} 错题集

> 记录踩过的坑、根因分析、排查思路，供回顾复盘。
> 每一条都包含：现象 → 根因 → 排查步骤 → 修复方案 → 预防口诀。

---

## 坑 1：{一句话概括现象}

### 现象
```
{贴报错/输出/行为}
```

### 根因
{分析真正原因，勿停在表面}

### 排查步骤
1. {第一步，如看 WARNING}
2. {第二步，如打印诊断值}
3. {第三步}

### 修复
```{语言}
{修前错代码 → 修后对代码}
```

### 预防口诀
> **{一句可复用的原则/顺口溜}**

---

## 知识点速查表

| 概念 | 公式/属性 | 说明 |
|------|----------|------|
| {概念} | {公式} | {一句话} |

---

## 调试工具箱

```python
{可复用的诊断脚本/命令}
```
```

- [ ] **Step 2: 创建 `so101/_template/README.md`**

写里程碑 README 模板。内容：

```markdown
# {Milestone 名}: {一句话目标}

> **目标**：{一句话}
> **状态**：🔒 Baseline（当前代码是 AI 写的参考实现，**等待你动手修改**）
> **关联技能**：{技能} (Lv{x}→Lv{y})
>
> **工作流**：AI 规划 + 提供 baseline → **你动手改代码** → AI Reviewer 验收 → 技能升级
>
> **⚠️ 先自己写，实在卡死再看 reference/**：必改项的答案在 `reference/` 文件夹里，卡死 20 分钟才允许瞄一眼，然后回来接着写。

## 架构

{ASCII 架构图}

## 必改项（你必须完成的修改，证明你理解了代码）

> **AI 不是 Doer**：以下代码的答案是 AI 写的，但已回退成 stub。你需要**亲自写核心逻辑**，提交 git，由 AI Reviewer 验收。

### 必改 1：{标题}
**目标**：{证明理解什么}
**要求**：
- [ ] {子任务 a}
- [ ] {子任务 b}
**验收标准**：
```bash
{可运行的验收命令}
```
**涉及文件**：{文件列表}

---

## 验收流程

```
你 git commit → 告诉 AI「{Milestone} 必改项完成」→ AI Reviewer 检查：
  1. 回退是否彻底（stub 是否被真实现替代）
  2. git diff 是否符合必改项要求、是否真重写（vs 抄 reference/）
  3. 错题集 MISTAKES.md 是否记录真实踩坑
  4. 运行验收命令是否通过
→ PASS → {Milestone} 解锁 → 技能升级
→ FAIL → 给出具体反馈 → 你修改 → 重新提交
```

## 下一步 → {下一个里程碑}
```

- [ ] **Step 3: 验证**

```bash
ls -la so101/_template/
# 预期：MISTAKES.md  README.md 两个文件
```

- [ ] **Step 4: Commit**

```bash
git add so101/_template/
git commit -m "feat(template): add rollback learning templates (错题集 + README)"
```

---

### Task 3: 落地 V1 试点（验证方法）

**Files:**
- Create: `so101/v1_ros2/reference/.gitkeep`（占位，表明 reference/ 目录约定）
- Create: `so101/v1_ros2/README.md`（从 `so101/_template/README.md` 复制，替换 V1 内容）

**Interfaces:**
- Consumes: Task 2 的模板 + 项目已知 roadmap（V1 = ROS2 基础控制）
- Produces: V1 里程碑的真实起点，验证回退学习法在下一个 milestone 可用

- [ ] **Step 1: 复制模板到 `so101/v1_ros2/`**

从 `so101/_template/README.md` 复制为 `so101/v1_ros2/README.md`，把 `{占位}` 替换为 V1 实值：Milestone 名「V1: ROS2 基础控制」、技能「ROS2 (Lv1→Lv2)」、目标「用 ROS2 实现机械臂关节控制」。必改项留待真正生成 baseline 时由 Claude 按 spec 设计（本任务只建骨架，不预设答案）。

- [ ] **Step 2: 建 `reference/` 占位目录**

```bash
mkdir -p so101/v1_ros2/reference
touch so101/v1_ros2/reference/.gitkeep
```

- [ ] **Step 3: 验证**

```bash
ls -la so101/v1_ros2/
# 预期：README.md  reference/ 存在
```

- [ ] **Step 4: Commit**

```bash
git add so101/v1_ros2/
git commit -m "feat(v1): scaffold V1 workspace from rollback template"
```

---

## Self-Review 记录

**1. Spec 覆盖**：
- §5.1 Claude 记忆自动回退 → Task 1
- §5.2 `_template/` 模板（MISTAKES + README）→ Task 2
- §三 回退边界（stub 约定 / reference 位置 / 分工）→ 全部写进 Task 1 记忆文案
- §六 Reviewer 三条检查 → 写进 Task 1 记忆 + Task 2 README 验收流程
- §七 不包含后端/前端改动 → 本计划零代码改动 ✅
- 试点 V1 → Task 3（将 spec 的"机械固化"落到真实下一里程碑）

**2. 占位符扫描**：Task 2 模板内的 `{占位}` 是模板自身的待填字段（面向未来 V(n) 用户），非计划缺陷；Task 3 明确把 V1 的 `{占位}` 替换为实值。无 "TBD/TODO/implement later"。

**3. 类型一致性**：记忆文案中的「三步」（写答案→存 reference/→回退成 stub）在 Task 1 记忆、Task 2 README 模板、spec §三 三处表述一致；stub 约定（签名+docstring+TODO+NotImplementedError）三处一致；路径 `so101/_template/`、`so101/v1_ros2/reference/` 全文一致。
