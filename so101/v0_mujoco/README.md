# SO101 V0: Mujoco 仿真机械臂控制

> **目标**：用 Python + Mujoco 实现 3-DOF 机械臂的关节空间控制
> **状态**：✅ 完成
> **关联技能**：Mujoco Simulation (Lv0→Lv2), Python (Lv4→Lv4+)

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

- [x] `so101_arm.xml` — 3-DOF 机械臂 MJCF 模型（关节范围、执行器增益）
- [x] `control_demo.py` — 4 组目标姿态控制 Demo（Home/Reach out/Reach up/Retract）
- [x] `state_reader.py` — 双模式：实时监测 / 轨迹录制 + CSV + 绘图
- [x] `verify_model.py` — 模型加载 + 渲染验证
- [x] `output/trajectory.csv` — 150 行时间序列（20Hz 采样）
- [x] `output/trajectory.png` — 3 关节角度变化曲线

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

## 下一步 → V1: ROS2 基础控制

见项目 Dashboard → SO101 → V1 里程碑
