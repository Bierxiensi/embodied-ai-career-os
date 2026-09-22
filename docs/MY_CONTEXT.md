# User Context

> 最后更新：2026-09-20（v3.1 在职转型校准）
> **技能等级的唯一权威来源是 `backend/app/core/skill_profile.py`**，本文件只做背景与策略说明。
> 改等级改那边，改完跑 `python backend/scripts/seed_job_hunt.py` 校准进库。

## Background

- 职业：算法工程师（Agent 应用方向），2026.01–09 在北京东鉴科技做文档智能 / 招投标方向
- 学历：郑州航空航天大学 计算机科学与技术（本科）｜北航 软件工程 非全在读（延至 2026-12 答辩）
- 主线能力：LLM 应用栈 —— Prompt / Function Calling / RAG / 多 Agent 编排
- 算法建模：PyTorch；时序预测、时空信息融合、文本分类、实体关系抽取
- 工程：React / Vue 企业级项目；FastAPI 后端；Electron / C# 桌面应用；Taro 小程序

### 学术成果（可作为算法能力背书）

- 论文（一作，IEEE 会议 / EI）：STM-SHAP: Exploring the Impact of Redundant and Lagged
  Features on Flood Forecasting，ISCTIS 2026，DOI 10.1109/ISCTIS70043.2026.11572181
- 学位论文：RL-RA-QR 洪水概率预报（在研）
- **口径红线**：EI 会议不得虚标为 SCI

## Goal（v3.1 在职转型校准）

- 战略基线：留在现公司，走 **long_term_transition（在职转型）** 模式；v2.0 的 job_hunt
  （2026-10-31 签约 / 2026-09-24 离职）假设已作废，不再以急签防社保中断为硬目标
- 在职转型窗口：2026.09–2027.03（约 6 个月）。主线从 Agent 应用收敛到
  **Post-Training / 大模型后训练（llm 主攻）+ 多模态（vlm 卡位）**
- 长期方向：具身智能 / VLA（embodied 赛道保持 frozen，作为在职期的研究积累，不主动冲刺）
- 博士申请：作为长期研究目标并行推进（Phase 1 博士模块建模），方向偏 AI / 机器人，
  依托北航非全在读 + 一作 EI 论文（STM-SHAP）基础
- 期望薪资：转型后目标 36–42K × 13+（在职涨薪或跳槽均可，不再为签约 deadline 让步）
- 关键节点：北航答辩 2026-12；在职转型里程碑 2027-03；PhD 申请季 2026 秋–2027 春

## Current Skills

见 `backend/app/core/skill_profile.py`。摘要：

| 档位 | 技能 |
|---|---|
| 强（4） | Agent Application、Python、Frontend、Web Engineering |
| 中（3） | PyTorch、Deep Learning、Linux |
| 弱（0–2） | ROS2(2)、Robot Learning(2)、Mujoco(2)、C++(2)、Isaac(1)、VLA(1)、Sim2Real(0)、MoveIt2(0) |

**最大卡点**：Sim2Real —— 仿真训练到真机部署的闭环未打通，这是主攻赛道的核心证据缺口。

## Hardware

- 主机：i5-14600KF + 技嘉 B760M + 96GB DDR5 + RTX 4060Ti 16GB + 致态 1T + 机械师 4T
- 评估中的本地推理方案：Qwen3 MoE（30B-A3B / 35B-A3B）；DGX Spark / V100 NVLink / 7900 XTX 选型对比

## Robot: SO101

- 状态：已组装、舵机可用、遥操作可用、采集 20 episodes、ACT 训练完成、推理可用
- 问题：**泛化差**，sim2real 未通
- 代码沉淀：`so101/v0_mujoco`（控制 + FK 验证 + 轨迹）、`so101/v1_ros2`（topic 通信 demo）

## Constraints

- 在职转型期可支配时间较充裕（此前约 1 小时/天），偏好项目驱动学习
- 偏好项目驱动学习，拒绝纯理论路线

## Learning Preference

- 先做能跑的东西，再补原理
- 每个产出要能写进简历：可量化指标 + 可展示结果（视频 / demo / 数据）
