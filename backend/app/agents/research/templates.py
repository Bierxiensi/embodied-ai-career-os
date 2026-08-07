"""Research Agent 模板库。

按技术主题预设研究计划模板，供 Research Agent 选用。
Phase 2 不做 RAG，先用模板覆盖核心主题。
模板源自 docs/MY_CONTEXT.md 真实研究场景（ACT/SO101/Isaac Lab）。

每项模板含 4 类研究任务：
    paper        论文精读
    code         代码实践
    experiment   实验验证
    verification 结果验证

Week 4-6 接入 RAG 后，模板可作为 fallback 或 few-shot 示例。
"""

from __future__ import annotations

from typing import TypedDict


class ResearchTemplate(TypedDict):
    """研究计划模板。"""

    topic: str                       # 规范化主题名
    aliases: list[str]               # 主题别名（大小写/缩写变体）
    paper: dict                      # 论文研究项
    code: dict                       # 代码实践项
    experiment: dict                 # 实验验证项
    verification: dict               # 结果验证项


# 主题 → 研究模板
# aliases 用于模糊匹配：用户输入 "act" / "ACT" / "Action Chunking" 都命中 ACT 模板
TEMPLATES: dict[str, ResearchTemplate] = {
    # ===== ACT（SO101 模仿学习核心算法）=====
    "ACT": ResearchTemplate(
        topic="ACT",
        aliases=["act", "ACT", "Action Chunking", "Action Chunking Transformer"],
        paper={
            "title": "ACT paper 精读",
            "description": "阅读 Learning Fine-Grained Bimanual Manipulation with Deep RL and Coarse Demonstration",
            "resources": ["ACT 原论文 arXiv", "First Author Blog"],
        },
        code={
            "title": "LeRobot ACT 实现阅读",
            "description": "阅读 HuggingFace LeRobot 仓库的 ACT 实现",
            "resources": ["LeRobot GitHub", "LeRobot 文档"],
        },
        experiment={
            "title": "SO101 imitation learning 实验",
            "description": "在 SO101 上跑 ACT 模仿学习，记录泛化效果",
            "resources": ["SO101 采集脚本", "ACT 训练配置"],
        },
        verification={
            "title": "ACT 泛化能力评估",
            "description": "对比不同场景下的成功率，记录到 LearningLog",
            "resources": ["评估脚本", "实验记录模板"],
        },
    ),
    # ===== VLA =====
    "VLA": ResearchTemplate(
        topic="VLA",
        aliases=["vla", "VLA", "Vision Language Action", "OpenVLA", "RT-2"],
        paper={
            "title": "OpenVLA / RT-2 论文精读",
            "description": "理解 Vision-Language-Action 模型架构",
            "resources": ["OpenVLA 论文", "RT-2 论文"],
        },
        code={
            "title": "OpenVLA 推理 demo",
            "description": "本地或 Colab 跑通 OpenVLA 推理",
            "resources": ["OpenVLA GitHub", "HuggingFace 模型页"],
        },
        experiment={
            "title": "VLA 在真实机器人上的推理",
            "description": "尝试将 VLA 接入 SO101，记录延迟与效果",
            "resources": ["SO101 控制接口", "VLA 推理脚本"],
        },
        verification={
            "title": "VLA vs ACT 对比",
            "description": "对比 VLA 与 ACT 在相同任务上的表现",
            "resources": ["对比实验设计", "评估指标"],
        },
    ),
    # ===== Isaac Lab / Isaac Sim =====
    "Isaac Lab": ResearchTemplate(
        topic="Isaac Lab",
        aliases=["isaac lab", "Isaac Lab", "isaac-lab", "IsaacLab"],
        paper={
            "title": "Isaac Lab / Isaac Sim 架构文档",
            "description": "阅读官方文档理解 Isaac Lab 与 Isaac Sim 的关系",
            "resources": ["Isaac Lab 官方文档", "Isaac Sim 文档"],
        },
        code={
            "title": "Isaac Lab 入门示例",
            "description": "跑通官方 RL 训练示例",
            "resources": ["Isaac Lab GitHub", "rsl_rl"],
        },
        experiment={
            "title": "SO101 URDF 在 Isaac 中仿真",
            "description": "导入 SO101 模型到 Isaac，做简单仿真",
            "resources": ["SO101 URDF", "Isaac Lab 机器人导入教程"],
        },
        verification={
            "title": "Sim-to-Real 可行性评估",
            "description": "评估 Isaac 仿真训练迁移到 SO101 真机的可行性",
            "resources": ["Sim-to-Real 综述", "domain randomization 文档"],
        },
    ),
    # ===== ROS2 =====
    "ROS2": ResearchTemplate(
        topic="ROS2",
        aliases=["ros2", "ROS2", "ros 2", "ROS 2"],
        paper={
            "title": "ROS2 架构与通信机制",
            "description": "理解 DDS / Topic / Service / Action 通信模型",
            "resources": ["ROS2 官方文档", "DDS 协议简介"],
        },
        code={
            "title": "rclpy publisher/subscriber 实践",
            "description": "用 rclpy 写 pub/sub demo",
            "resources": ["rclpy 文档", "ROS2 官方教程"],
        },
        experiment={
            "title": "ROS2 控制 SO101",
            "description": "用 ROS2 节点下发 SO101 关节指令",
            "resources": ["SO101 ROS2 驱动", "ROS2 控制接口"],
        },
        verification={
            "title": "ROS2 节点稳定性验证",
            "description": "长时间运行测试节点稳定性与延迟",
            "resources": ["ros2 bag 录制", "性能分析工具"],
        },
    ),
}


def match_template(topic: str) -> ResearchTemplate | None:
    """按主题名模糊匹配模板。

    匹配策略：
    1. 精确匹配规范化主题名（key）
    2. 别名匹配（aliases，大小写不敏感）

    Args:
        topic: 用户输入的原始主题

    Returns:
        匹配的模板；未命中返回 None（调用方需 fallback）
    """
    if not topic:
        return None

    normalized = topic.strip()

    # 1. 精确匹配 key
    if normalized in TEMPLATES:
        return TEMPLATES[normalized]

    # 2. 别名匹配（大小写不敏感）
    lowered = normalized.lower()
    for tmpl in TEMPLATES.values():
        for alias in tmpl["aliases"]:
            if alias.lower() == lowered:
                return tmpl

    return None


def fallback_template(topic: str) -> ResearchTemplate:
    """生成通用研究模板（未命中预设模板时使用）。

    保证 Research Agent 对任意主题都有输出，不阻塞下游 Planner。

    Args:
        topic: 用户输入的原始主题

    Returns:
        通用模板，4 类任务均基于该主题生成
    """
    safe_topic = (topic or "Unknown").strip()
    return ResearchTemplate(
        topic=safe_topic,
        aliases=[safe_topic],
        paper={
            "title": f"{safe_topic} 相关论文精读",
            "description": f"检索并阅读 {safe_topic} 领域的核心论文",
            "resources": ["arXiv", "Google Scholar"],
        },
        code={
            "title": f"{safe_topic} 开源实现阅读",
            "description": f"查找 {safe_topic} 的开源实现并阅读核心代码",
            "resources": ["GitHub", "Papers with Code"],
        },
        experiment={
            "title": f"{safe_topic} 实践实验",
            "description": f"基于 {safe_topic} 跑一个最小可运行实验",
            "resources": ["官方示例", "社区教程"],
        },
        verification={
            "title": f"{safe_topic} 学习成果验证",
            "description": f"记录 {safe_topic} 学习产出，验证理解深度",
            "resources": ["LearningLog", "评估清单"],
        },
    )
