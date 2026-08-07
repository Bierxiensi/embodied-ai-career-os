"""任务模板库。

按技能 + 难度预设学习任务模板，供 Rule Generator 选用。
模板源自 docs/MY_CONTEXT.md 的真实学习场景（SO101/ROS2/Isaac/VLA）。
每项含：标题、目标、验收标准、推荐资源、基准时长。

LLM Generator 不使用此库（由模型生成），但可读取作为 few-shot 示例。
"""

from __future__ import annotations

from typing import TypedDict


class TaskTemplate(TypedDict):
    """任务模板。"""

    title: str
    objective: str
    difficulty: str          # beginner / intermediate / advanced
    acceptance: list[str]
    resources: list[str]
    base_minutes: int        # 基准时长（实际按 available_minutes 截断）


# 技能 → 该技能下按难度分级的模板列表
TEMPLATES: dict[str, list[TaskTemplate]] = {
    # ===== Isaac（缺口最大，从零开始）=====
    "Isaac": [
        TaskTemplate(
            title="Isaac Sim 基础环境搭建",
            objective="成功安装并启动 Isaac Sim，跑通官方示例",
            difficulty="beginner",
            acceptance=[
                "成功启动 Isaac 环境",
                "运行官方 Example",
                "记录配置过程",
            ],
            resources=[
                "Isaac Sim 官方文档",
                "NVIDIA Omniverse Launcher",
            ],
            base_minutes=60,
        ),
        TaskTemplate(
            title="Isaac Sim Python API 入门",
            objective="用 Python 脚本控制场景中的机器人",
            difficulty="intermediate",
            acceptance=[
                "用 omni.isaac.core 创建场景",
                "加载 URDF/USD 机器人模型",
                "脚本控制关节运动",
            ],
            resources=["Isaac Python API 文档", "omni.isaac.examples"],
            base_minutes=90,
        ),
    ],
    # ===== VLA（缺口最大，从零开始）=====
    "VLA": [
        TaskTemplate(
            title="VLA 模型概念梳理与论文精读",
            objective="理解 Vision-Language-Action 模型架构与 RT-2/OpenVLA",
            difficulty="beginner",
            acceptance=[
                "阅读 OpenVLA 论文",
                "梳理 VLA 架构图",
                "记录与 ACT 的差异",
            ],
            resources=["OpenVLA 论文", "RT-2 论文", "HuggingFace LeRobot"],
            base_minutes=45,
        ),
        TaskTemplate(
            title="OpenVLA 推理 demo 复现",
            objective="本地或 Colab 跑通 OpenVLA 推理",
            difficulty="intermediate",
            acceptance=[
                "下载 OpenVLA 权重",
                "运行推理脚本",
                "记录显存与延迟",
            ],
            resources=["OpenVLA GitHub", "HuggingFace 模型页"],
            base_minutes=90,
        ),
    ],
    # ===== ROS2 =====
    "ROS2": [
        TaskTemplate(
            title="ROS2 Topic 通信机制实践",
            objective="掌握 publisher/subscriber 通信，写出可运行 demo",
            difficulty="beginner",
            acceptance=[
                "创建 publisher 节点发布字符串",
                "创建 subscriber 节点接收消息",
                "Git 提交可运行的 demo",
            ],
            resources=["ROS2 官方教程", "rclpy 文档"],
            base_minutes=40,
        ),
        TaskTemplate(
            title="ROS2 + SO101 控制节点",
            objective="用 ROS2 节点下发 SO101 关节指令",
            difficulty="intermediate",
            acceptance=[
                "编写 SO101 控制节点",
                "订阅关节状态话题",
                "SO101 响应指令动作",
            ],
            resources=["SO101 文档", "ROS2 控制接口"],
            base_minutes=60,
        ),
    ],
    # ===== Robot Learning =====
    "Robot Learning": [
        TaskTemplate(
            title="SO101 ACT 模型泛化调试",
            objective="采集新数据重训 ACT，对比泛化成功率",
            difficulty="intermediate",
            acceptance=[
                "采集 20+ episodes 新数据",
                "训练新模型并对比成功率",
                "记录泛化效果到 LearningLog",
            ],
            resources=["ACT 原论文", "SO101 采集脚本", "LeRobot"],
            base_minutes=60,
        ),
    ],
    # ===== PyTorch / Deep Learning / Agent / Python（中等缺口，巩固类）=====
    "PyTorch": [
        TaskTemplate(
            title="PyTorch 自定义 Dataset 与 DataLoader 实践",
            objective="为 SO101 数据写自定义 Dataset，跑通训练循环",
            difficulty="intermediate",
            acceptance=[
                "实现 Dataset 子类",
                "DataLoader 批量加载",
                "训练一个 epoch 不报错",
            ],
            resources=["PyTorch 官方教程"],
            base_minutes=45,
        ),
    ],
    "Deep Learning": [
        TaskTemplate(
            title="Transformer 架构手写复现",
            objective="用 PyTorch 手写最小 Transformer，理解注意力机制",
            difficulty="intermediate",
            acceptance=[
                "实现 MultiHeadAttention",
                "实现 Positional Encoding",
                "前向传播 shape 正确",
            ],
            resources=["Attention is All You Need", "The Annotated Transformer"],
            base_minutes=60,
        ),
    ],
    "Agent": [
        TaskTemplate(
            title="LangGraph 多节点 Agent 实践",
            objective="用 LangGraph 搭建含条件分支的 Agent",
            difficulty="intermediate",
            acceptance=[
                "定义 StateGraph",
                "实现至少 3 个节点",
                "跑通端到端流程",
            ],
            resources=["LangGraph 文档", "本项目 Planner Agent"],
            base_minutes=50,
        ),
    ],
    "Python": [
        TaskTemplate(
            title="Python asyncio 异步编程实践",
            objective="掌握 async/await，为 FastAPI 异步接口打基础",
            difficulty="intermediate",
            acceptance=[
                "编写 async 函数",
                "用 asyncio.gather 并发",
                "理解事件循环",
            ],
            resources=["Python asyncio 文档"],
            base_minutes=40,
        ),
    ],
}


def get_template(skill: str, difficulty: str | None = None) -> TaskTemplate | None:
    """按技能名取模板。difficulty 为 None 时返回该技能第一个模板。

    Args:
        skill: 技能名称（如 "Isaac"）
        difficulty: 可选难度过滤，未指定则取首个

    Returns:
        匹配的模板；技能无模板时返回 None（调用方需兜底）。
    """

    templates = TEMPLATES.get(skill)
    if not templates:
        return None
    if difficulty:
        for t in templates:
            if t["difficulty"] == difficulty:
                return t
    return templates[0]
