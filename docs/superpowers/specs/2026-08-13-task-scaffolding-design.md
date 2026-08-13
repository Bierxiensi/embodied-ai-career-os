# 任务脚手架系统设计（Baseline + 必改项 + 物理工作空间）

> 2026-08-13 · 基于 brainstorming 产出 · 把 V0 验证有效的学习模式系统化

---

## 一、设计理念

**问题**：AI 直接写完整代码 → 用户没参与，学不到东西。纯任务描述 → 用户没抓手，无从下手。

**答案**：V0 已经验证 —— AI 给「Baseline（参考实现）+ 必改项（必须自己做的核心决策）」，用户重写核心逻辑证明理解。

核心架构是把 **「智能」和「记录」分开**：

| 层 | 谁做 | 干什么 | 为什么 |
|----|------|--------|--------|
| **智能层** | Claude Code（Coach） | 写 baseline 代码、设计触及核心的必改项、Reviewer 判断"真重写 vs 复制粘贴" | 后端 LLM 默认 mock，写不对机器人代码；V0 的 baseline 是手工精心写的 |
| **记录层** | 后端 + Reviewer Agent | 幂等生成、任务状态机、workspace 路径、必改项清单、技能升级、评分留痕 | 这是纯状态追踪，规则能做 |

**核心规则**：
- baseline = 「参考答案」，但 Reviewer 考的不是"能不能抄对"，而是"能不能不看答案重写出来 + 解释为什么"
- 每条必改项必须锚定核心学习点 + 带可运行的验收命令（客观 pass/fail）
- 必改项要求「重写」而非「微调」，Reviewer 看 git diff 判断

---

## 二、数据模型改动

### 2.1 Milestone 表新增两个字段

workspace 和必改项是 **milestone 级别**的（V0 的 3 个任务共享 `v0_mujoco/` 目录 + 3 个整体性必改项），故放 Milestone 而非 Task。

```python
class Milestone(Base):
    # ...现有字段...
    workspace: str | None               # 物理路径，如 "so101/v1_ros2/"
    required_modifications: list | None # 必改项清单（JSON）
```

### 2.2 required_modifications 结构

```json
[
  {
    "title": "加第 4 个关节 wrist_roll",
    "goal": "证明理解 MJCF 模型结构（joint/body/actuator 关系）",
    "files": ["so101_arm.xml", "control_demo.py", "state_reader.py"],
    "verification": "python verify_model.py  # 输出 4 joints, 4 actuators"
  }
]
```

### 2.3 workspace 命名规范

```
格式：so101/v{version_lower}_{slug}/
示例：so101/v1_ros2/、so101/v2_moveit2/
```

slug 由 Claude Code 生成（智能），后端只存储。

---

## 三、API 改动

### 3.1 幂等生成（修 BUG）

`POST /api/milestones/{id}/tasks` 增加幂等检查：

```
生成前查 Task.milestone_id == milestone_id 的已有数量
  → count > 0：返回已有任务 + message="该里程碑已生成过任务"
  → count == 0：正常拆解生成
```

### 3.2 写脚手架字段

`PATCH /api/milestones/{id}` 的 `MilestonePatch` 扩展两个可选字段，供 Claude Code 生成 baseline 后回填：

```python
class MilestonePatch(BaseModel):
    # ...现有字段...
    workspace: str | None = None
    required_modifications: list | None = None
```

---

## 四、前端改动

### 4.1 类型

`Milestone` 接口新增：

```typescript
workspace?: string | null;
requiredModifications?: Array<{
  title: string; goal: string; files: string[]; verification: string;
}>;
```

### 4.2 生成任务按钮幂等

`MilestoneTimeline` 中，某 milestone 已生成任务（`milestoneId` 已有 task）时，按钮显示「任务已生成」并禁用，不再可重复点击。

### 4.3 里程碑详情展示

in_progress 里程碑展开显示：workspace 路径（可点击跳转/复制）+ 必改项清单（title + goal + files + verification 命令）。

---

## 五、完整工作流（闭环）

```
1. 用户解锁 V1（locked → in_progress）
2. 用户点「生成任务」
     → 后端幂等检查 → _decompose_milestone 生成 3 个「任务壳」
     → （title/objective/acceptance/resources，规则可做）
3. 用户回到 Claude Code：「开始 V1」
     → Claude Code 物理建 so101/v1_ros2/ 目录 + baseline 代码 + README
     → 设计必改项（触及核心 + 验收命令）
     → PATCH milestone 回填 workspace + required_modifications
4. 用户在 Trae 里干活（改 baseline、写核心逻辑）
5. 提交 → 告知 Claude Code「V1 必改项完成」
6. Claude Code（Reviewer）验收：
     → 逐条对照 required_modifications 跑 verification 命令
     → 看 git diff 判断是否「真重写」
     → 问「为什么」验证理解
     → PASS：标记 milestone complete + 解锁 V2 + 技能升级
     → FAIL：给出具体反馈，用户改后重提交
```

---

## 六、BUG 修复清单

| BUG | 根因 | 修复 |
|-----|------|------|
| 点「生成任务」重复生成同名任务 | `generate_tasks_from_milestone` 无条件 `db.add`，无幂等检查 | 生成前查 `milestone_id` 已有任务则跳过 |

---

## 七、实施范围

### 包含

- Milestone 模型 + schema + 前端类型：`workspace` + `required_modifications`
- `generate_tasks_from_milestone` 幂等检查
- 前端「生成任务」按钮幂等状态
- 前端里程碑详情展示 workspace + 必改项

### 不包含

- 后端 LLM 自动生成 baseline（由 Claude Code 做，后端只登记）
- 后端自动建目录/写 README（Claude Code 物理操作）
- Reviewer Agent 自动检查 git diff（Claude Code 手工判断）

---

## 八、不变更的部分

- Skill / Task / Reviewer / Reminder 模块保持不动
- Task 表不加字段（幂等用现有 milestone_id）
- `_decompose_milestone` 的规则拆解逻辑保持（产出"任务壳"）
- 前端现有组件保留

---

## 九、设计决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| 模式 | Baseline + 必改项 | V0 已验证"清晰"，正确卡在脚手架 vs 答案边界 |
| 落盘形式 | 物理工作空间（真实目录） | 用户在 Trae 里有真实目录抓手；目录由 Claude Code 建（写 baseline 时一并落盘），后端只存路径 |
| baseline 生成者 | Claude Code | 后端 LLM（mock）写不对机器人代码 |
| workspace 归属 | Milestone 级 | 一个 milestone 一个目录 + 一组整体性必改项 |
| 幂等策略 | 后端生成前查已有任务 | 根因修复，非前端临时禁用 |
| 验收判定 | Claude Code 手工（跑命令 + 看 diff + 问为什么） | 判断"真重写"需要领域智能，规则做不了 |
