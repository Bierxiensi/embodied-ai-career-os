# V1: ROS2 基础控制: 用 ROS2 实现 SO101 机械臂的关节控制

> **目标**：掌握 ROS2 Topic 通信机制，用 Publisher/Subscriber 控制 SO101 关节
> **状态**：🔒 Baseline（当前代码是 AI 写的参考实现，**等待你动手修改**）
> **关联技能**：ROS2 (Lv1→Lv2)
>
> **工作流**：AI 规划 + 提供 baseline → **你动手改代码** → AI Reviewer 验收 → 技能升级
>
> **⚠️ 先自己写，实在卡死再看 reference/**：必改项的答案在 `reference/` 文件夹里，卡死 20 分钟才允许瞄一眼，然后回来接着写。

## 前置条件

- Ubuntu 22.04 或 WSL2 + ROS2 Humble
- 已安装 ROS2：`sudo apt install ros-humble-desktop`
- Source 环境：`source /opt/ros/humble/setup.bash`

## 架构

```
joint_publisher.py ──→ /joint_commands (Float64MultiArray) ←── joint_subscriber.py
       │                                                          │
       ├──→ 发布 4 关节角度 (弧度)                                ├──→ 打印关节角度 (度)
       └──→ 定时器 1Hz                                            └──→ 订阅回调处理

demo_launch.py ──→ 同时启动 Publisher + Subscriber
```

## 学到的概念

| 概念 | 对应内容 | 迁移到 |
|------|---------|--------|
| ROS2 Node | `class Node` 基类 | 所有 ROS2 程序 |
| Topic | 命名总线，异步通信 | 传感器数据、控制指令 |
| Publisher | `create_publisher()` 发布消息 | 关节控制、状态广播 |
| Subscriber | `create_subscription()` 订阅消息 | 传感器读取、反馈接收 |
| 消息类型 | `Float64MultiArray` | 任意数组数据 |
| Launch 文件 | 编排多节点启动 | 复杂系统集成 |

## 运行

```bash
# 终端 1：启动 Publisher
source /opt/ros/humble/setup.bash
python3 joint_publisher.py

# 终端 2：启动 Subscriber
source /opt/ros/humble/setup.bash
python3 joint_subscriber.py

# 或者用 Launch 文件同时启动
python3 demo_launch.py
```

## 必改项（你必须完成的修改，证明你理解了代码）

> **AI 不是 Doer**：以下代码的答案是 AI 写的，但已回退成 stub。你需要**亲自写核心逻辑**，提交 git，由 AI Reviewer 验收。

### 必改 1：实现 SimplePublisher（字符串 Publisher）
**目标**：证明理解 ROS2 节点、Publisher、定时器的基本用法
**要求**：
- [ ] 完成 `SimplePublisher.__init__`：创建节点、Publisher、定时器
- [ ] 完成 `timer_callback`：创建 String 消息、发布、打印日志
- [ ] 完成 `main`：初始化 ROS2、spin 节点、清理资源
- [ ] 运行验证：`python3 simple_publisher.py` 每 0.5 秒输出 "Hello ROS2: N"
**验收标准**：
```bash
python3 simple_publisher.py
# 预期输出：
# [INFO] [talker]: Publishing: 'Hello ROS2: 0'
# [INFO] [talker]: Publishing: 'Hello ROS2: 1'
# ... (Ctrl+C 停止)
```
**涉及文件**：`simple_publisher.py`

---

### 必改 2：实现 JointSubscriber（关节 Subscriber）
**目标**：证明理解 Subscriber 回调、消息解析、弧度→度转换
**要求**：
- [ ] 完成 `JointSubscriber.__init__`：创建 Subscriber，订阅 `/joint_commands`
- [ ] 完成 `joint_callback`：解析 Float64MultiArray、转换度数、逐关节打印
- [ ] 完成 `main`：初始化 ROS2、spin 节点、清理资源
- [ ] 运行验证：配合 `joint_publisher.py` 能正确接收并打印关节角度
**验收标准**：
```bash
# 终端 1：python3 joint_publisher.py
# 终端 2：python3 joint_subscriber.py
# 预期输出：
# [INFO] [joint_subscriber]: 收到关节命令: [0.524, -0.524, 0.524, 1.047] rad
#   关节 0: 30.0° | 关节 1: -30.0° | 关节 2: 30.0° | 关节 3: 60.0°
```
**涉及文件**：`joint_subscriber.py`

---

### 必改 3：实现 Launch 文件
**目标**：证明理解 ROS2 Launch 文件的作用和 Node 配置
**要求**：
- [ ] 完成 `generate_launch_description`：返回 LaunchDescription 包含两个 Node
- [ ] 配置 package、executable、name、output 参数
- [ ] 运行验证：`ros2 launch so101_v1 demo_launch.py` 同时启动两个节点
**验收标准**：
```bash
python3 demo_launch.py
# 预期输出：提示使用 ros2 launch 命令
# 同时启动 Publisher 和 Subscriber，输出交替显示
```
**涉及文件**：`demo_launch.py`

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

## 产出物

> ⚠️ 以下为 AI 写的 **baseline 参考代码**（已回退成 stub）。你需要通过必改项证明理解。

- [x] `simple_publisher.py` — 字符串 Publisher stub `[AI baseline → 等你实现]`
- [x] `simple_subscriber.py` — 字符串 Subscriber stub `[AI baseline → 等你实现]`
- [x] `joint_publisher.py` — 关节控制 Publisher stub `[AI baseline → 等你实现]`
- [x] `joint_subscriber.py` — 关节控制 Subscriber stub `[AI baseline → 等你实现]`
- [x] `demo_launch.py` — Launch 文件 stub `[AI baseline → 等你实现]`
- [x] `reference/` — 完整参考答案 `[卡死 20 分钟才看]`
- [ ] `MISTAKES.md` — 错题集 `[你来记录]`

## 下一步 → V2: MoveIt2 运动规划
