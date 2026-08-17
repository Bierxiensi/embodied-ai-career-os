# V1: ROS2 基础控制: 用 ROS2 实现 SO101 机械臂的关节控制

> **目标**：用 ROS2 实现 SO101 机械臂的关节控制
> **状态**：🔒 Baseline（当前代码是 AI 写的参考实现，**等待你动手修改**）
> **关联技能**：ROS2 (Lv1→Lv2)
>
> **工作流**：AI 规划 + 提供 baseline → **你动手改代码** → AI Reviewer 验收 → 技能升级
>
> **⚠️ 先自己写，实在卡死再看 reference/**：必改项的答案在 `reference/` 文件夹里，卡死 20 分钟才允许瞄一眼，然后回来接着写。

## 架构

```
control_node.py ──→ ROS2 Topic (/joint_cmds) ←── joystick 或定时发布
       │
       ├──→ /joint_states 发布 (编码器读数)
       ├──→ rqt_graph / RViz 可视化
       └──→ 对比：Mujoco 仿真 vs 真实舵机
```

## 必改项（你必须完成的修改，证明你理解了代码）

> **AI 不是 Doer**：以下代码的答案是 AI 写的，但已回退成 stub。你需要**亲自写核心逻辑**，提交 git，由 AI Reviewer 验收。

### 必改 1：{待定 - 生成 baseline 时按 spec 设计}
**目标**：{待定}
**要求**：
- [ ] {子任务 a}
- [ ] {子任务 b}
**验收标准**：
```bash
{可运行的验收命令}
```
**涉及文件**：{文件列表}

> 必改项由 Claude 生成 baseline 时设计（触及核心 + 带验收命令）。

---

## 验收流程

```
你 git commit → 告诉 AI「V1 必改项完成」→ AI Reviewer 检查：
  1. 回退是否彻底（stub 是否被真实现替代）
  2. git diff 是否符合必改项要求、是否真重写（vs 抄 reference/）
  3. 错题集 MISTAKES.md 是否记录真实踩坑
  4. 运行验收命令是否通过
→ PASS → V1 解锁 → 技能升级
→ FAIL → 给出具体反馈 → 你修改 → 重新提交
```

## 下一步 → V2: MoveIt2 运动规划
