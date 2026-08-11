# SO101 V0: Mujoco 仿真机械臂控制

> **目标**：用 Python + Mujoco 实现 3-DOF 机械臂的关节空间控制
> **状态**：🔒 Baseline（当前代码是 AI 写的参考实现，**等待你动手修改**）
> **关联技能**：Mujoco Simulation (Lv0→Lv2), Python (Lv4→Lv4+)
>
> **工作流**：AI 规划 + 提供 baseline → **你动手改代码** → AI Reviewer 验收 → 技能升级

## 架构

```
control_demo.py ──→ Mujoco Engine ←── so101_arm.xml (MJCF 模型)
       │
       ├──→ 设置 joint targets (data.ctrl[])
       ├──→ 读取 joint states  (data.qpos[])
       └──→ state_reader.py (CSV + matplotlib 图表)
```

## 机械臂结构

```
Base (world)
  │
  └── joint0: base_rotation  (Z-axis hinge, ±90°)
       │
       └── joint1: shoulder_pitch (Y-axis hinge, -90°~45°)
            │
            └── joint2: elbow_pitch (Y-axis hinge, 0°~135°)
                 │
                 └── end_effector (红色标记点)
```

## 学到的概念

| 概念 | 对应内容 | 迁移到 |
|------|---------|--------|
| 关节空间控制 | `data.ctrl[i] = target_rad` | SO101 舵机 / ROS2 JointTrajectory |
| 机器人模型格式 | MJCF（joint/link/actuator） | ROS2 URDF / Xacro |
| 铰链关节 (hinge) | 旋转轴 axis + 角度范围 range | 所有旋转关节 |
| Position Actuator | kp (刚度) + kv (阻尼) → PD 控制 | 真实舵机 PID |
| 正向运动学 (FK) | 给定 joint angles → 末端位置变化 | MoveIt2 / TF2 |
| 稳态误差 | PD 控制器在重力下的跟随误差 | 控制理论 |
| 轨迹记录 | CSV 导出 + matplotlib 可视化 | rosbag2 / 数据分析 |

## 运行

```bash
# 安装（只需一次）
pip install mujoco numpy matplotlib

# 关节控制 Demo —— 4 组姿态
python control_demo.py

# 轨迹记录 + 绘图
python state_reader.py record
# → output/trajectory.csv + output/trajectory.png

# 实时状态监测
python state_reader.py continuous
```

## 产出物

> ⚠️ 以下为 AI 写的 **baseline 参考代码**。你需要通过必改项证明理解。

- [x] `so101_arm.xml` — 3-DOF 机械臂 MJCF 模型（关节范围、执行器增益） `[AI baseline]`
- [x] `control_demo.py` — 4 组目标姿态控制 Demo（Home/Reach out/Reach up/Retract） `[AI baseline]`
- [x] `state_reader.py` — 双模式：实时监测 / 轨迹录制 + CSV + 绘图 `[AI baseline]`
- [x] `verify_model.py` — 模型加载 + 渲染验证 `[AI baseline]`
- [x] `output/trajectory.csv` — 150 行时间序列（20Hz 采样） `[AI baseline]`
- [x] `output/trajectory.png` — 3 关节角度变化曲线 `[AI baseline]`
- [ ] `so101_arm.xml` — **你加了 wrist_roll（第 4 关节）** `[等你完成]`
- [ ] `control_trajectory.py` — **你实现了 waypoint 插值控制** `[等你完成]`
- [ ] `verify_fk.py` — **你手写了 FK 并与 Mujoco 对比** `[等你完成]`

## 技术要点

### PD 位置控制

```
actuator force = kp * (target - current) - kv * velocity
```

- kp=40 提供适中的跟随刚度
- kv=3 提供阻尼，防止振荡
- 重力负载下 shoulder 关节约 2-3° 稳态误差 → 这是真实物理现象

### 坐标系

- Z-up（Mujoco 默认）
- Joint 0 绕 Z 轴（yaw）
- Joint 1/2 绕 Y 轴（pitch）
- 末端位置 = FK(joint0, joint1, joint2)

## ⚠️ 必改项（你必须做的修改，证明你理解了代码）

> **AI 不是 Doer**：以下代码是 AI 写的 baseline。你需要**亲自修改代码**，
> 提交到 git，然后由 AI Reviewer 验收。只有 Reviewer 通过，V0 才算完成。

### 必改 1：加第 4 个关节 — 腕部旋转 (wrist_roll)

**目标**：证明你理解了 MJCF 模型结构（joint / body / actuator 的关系）

**要求**：
- [ ] 在 forearm 末端、end_effector 之前插入第 4 个关节 `wrist_roll`
- [ ] 类型为 hinge，绕 X 轴旋转，范围 ±90°
- [ ] 配对应的 `<position>` actuator（kp=40, kv=3）
- [ ] 更新 `control_demo.py` 的 poses 为 4 元素数组（加腕关节角度）
- [ ] 更新 `state_reader.py` 支持 4 关节（轴标签、颜色等自适应）

**验收标准**：
```bash
python verify_model.py  # 输出 4 bodies, 4 joints, 4 actuators
python control_demo.py  # 每组姿态包含 4 个关节角度
python state_reader.py record  # CSV 有 4 列 joint_X_deg，图表 4 行
```

**涉及文件**：`so101_arm.xml`, `control_demo.py`, `state_reader.py`

---

### 必改 2：改控制策略 — 从跳变到轨迹插值（waypoint interpolation）

**目标**：证明你理解了关节空间控制的本质（不是瞬间跳变，而是平滑运动）

**要求**：
- [ ] 写一个新函数 `interpolate_waypoints(waypoints, duration_per_segment)` 
- [ ] 输入是一系列目标姿态（waypoints），比如 Home → Reach out → Reach up → Retract
- [ ] 在相邻 waypoint 之间做**线性插值**（每 50 步更新一次 ctrl）
- [ ] 用 `state_reader.py record` 模式录制完整轨迹，验证曲线是平滑的（无跳变）
- [ ] 将新脚本命名为 `control_trajectory.py`

**验收标准**：
```bash
python control_trajectory.py
# 机械臂应该平滑经过所有 waypoint，而非瞬间跳变
python state_reader.py record
# trajectory.png 曲线应无阶跃跳变（对比 control_demo.py 的 step 响应）
```

**涉及文件**：新建 `control_trajectory.py`

---

### 必改 3：FK 验证 — 用三角函数手算末端位置

**目标**：证明你理解了正向运动学（给定各关节角度 → 末端在哪？）

**要求**：
- [ ] 写一个函数 `compute_fk(joint_angles_deg)` → `(x, y, z)` 
- [ ] 使用三角函数（sin/cos）和机械臂的几何参数（link length = 0.3m upper_arm + 0.24m forearm）
- [ ] 考虑 base_rotation（绕 Z 轴）和 shoulder_pitch/elbow_pitch（绕 Y 轴在竖直平面内）
- [ ] 用 Mujoco 的 `data.site_xpos[0]` 作为 ground truth，比较你的 FK 计算结果
- [ ] 对至少 5 组随机关节角度，打印比较结果，误差应 < 0.01m
- [ ] 将脚本命名为 `verify_fk.py`

**验收标准**：
```bash
python verify_fk.py
# 输出 5 组对比，每组格式：
#   FK: (x, y, z) = (0.123, 0.045, 0.567)
#   Mujoco: (x, y, z) = (0.125, 0.043, 0.565)
#   Error: 0.003m ✅
```

**涉及文件**：新建 `verify_fk.py`

---

## 验收流程

```
你 git commit → 告诉 AI "V0 必改项完成" → AI Reviewer 检查：
  1. git diff 是否符合必改项要求
  2. 代码逻辑正确性
  3. 运行验收命令是否通过
→ Reviewer PASS → V0 解锁 → Dashboard 标记 complete → 技能升级
→ Reviewer FAIL → 给出具体反馈 → 你修改 → 重新提交
```

## 下一步 → V1: ROS2 基础控制

见项目 Dashboard → SO101 → V1 里程碑
