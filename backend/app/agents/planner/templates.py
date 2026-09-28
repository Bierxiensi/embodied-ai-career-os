"""任务模板库。

按技能 + 难度预设学习任务模板，供 Rule Generator 选用。
模板源自 Post-Training（SFT/LoRA/DPO/GRPO/vLLM）真实学习场景。
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


# 技能 → 该技能下按难度分级的模板列表（2026-09-24 对齐 Post-Training v3.0）
TEMPLATES: dict[str, list[TaskTemplate]] = {
    "SFT": [
        TaskTemplate(
            title="SFT 指令数据集构建与清洗",
            objective="产出一份可训练的指令数据集并完成格式校验",
            difficulty="beginner",
            acceptance=[
                "收集/构造 ≥100 条指令样本",
                "完成去重与格式校验脚本",
                "数据卡（来源/许可/规模）随库提交",
            ],
            resources=["Hugging Face LLM Course（数据集章节）", "InstructGPT 论文（数据构成）"],
            base_minutes=60,
        ),
        TaskTemplate(
            title="跑通一次 SFT 微调并记录 loss 曲线",
            objective="用 transformers Trainer 完成一次小规模 SFT 并留存训练记录",
            difficulty="intermediate",
            acceptance=[
                "训练脚本可复跑（依赖锁定）",
                "loss 曲线与最终指标记录进 LearningLog",
                "badcase 至少 3 条入册",
            ],
            resources=["Hugging Face LLM Course（微调章节）", "Mini Post-Training Lab 01_sft"],
            base_minutes=90,
        ),
    ],
    "LoRA/QLoRA": [
        TaskTemplate(
            title="LoRA 低秩适配原理精读 + 复述",
            objective="能向他人讲清 LoRA 为什么省显存、秩 r 怎么选",
            difficulty="beginner",
            acceptance=[
                "精读 LoRA 论文 method 节",
                "Teach-Back 复述通过（3 个要点）",
                "概念卡入复习队列",
            ],
            resources=["LoRA (arXiv 2106.09685)", "Hugging Face PEFT 文档"],
            base_minutes=45,
        ),
        TaskTemplate(
            title="QLoRA 4-bit 微调对比实验",
            objective="同基座 LoRA vs QLoRA 对比显存与效果，产出实验记录",
            difficulty="advanced",
            acceptance=[
                "两组配置可复现（bitsandbytes 配置入册）",
                "显存/时长/指标三列对比表",
                "实验记录进 experiments（kind=finetune）",
            ],
            resources=["QLoRA 论文", "Mini Post-Training Lab 02_lora"],
            base_minutes=120,
        ),
    ],
    "DPO": [
        TaskTemplate(
            title="DPO 偏好优化原理精读 + 复述",
            objective="弄清 DPO 如何绕过奖励模型、与 RLHF 的关系",
            difficulty="beginner",
            acceptance=[
                "精读 DPO 论文 method 节",
                "能回答“DPO 相比 RLHF 的优势”3 点以上",
                "概念卡入复习队列",
            ],
            resources=["DPO (arXiv 2305.18290)", "RLHF (arXiv 2203.02155)"],
            base_minutes=45,
        ),
        TaskTemplate(
            title="跑通一次 DPO 对齐训练",
            objective="用 trl 完成一次 DPO 训练并评估偏好胜率",
            difficulty="advanced",
            acceptance=[
                "偏好数据对 ≥200 组",
                "训练可复跑，超参入册",
                "胜率/评测结果进 experiments（kind=finetune）",
            ],
            resources=["Mini Post-Training Lab 03_dpo", "trl DPOTrainer 文档"],
            base_minutes=120,
        ),
    ],
    "GRPO": [
        TaskTemplate(
            title="GRPO 与 PPO 的区别梳理",
            objective="能讲清 GRPO 去掉价值网络的做法与适用场景",
            difficulty="intermediate",
            acceptance=[
                "精读 DeepSeekMath GRPO 小节",
                "对照表：PPO vs GRPO（至少 4 行）",
                "对照行入复习卡",
            ],
            resources=["DeepSeekMath (arXiv 2402.03300)", "PPO (arXiv 1707.06347)"],
            base_minutes=60,
        ),
    ],
    "RLHF": [
        TaskTemplate(
            title="RLHF 三阶段管线复盘",
            objective="SFT→RM→PPO 三阶段各自解决什么，能完整讲一遍",
            difficulty="beginner",
            acceptance=[
                "三阶段流程图（手绘/文本）",
                "Teach-Back 复述通过",
                "薄弱点写进 LearningLog 反思",
            ],
            resources=["InstructGPT (arXiv 2203.02155)", "PPO 论文"],
            base_minutes=45,
        ),
    ],
    "vLLM": [
        TaskTemplate(
            title="vLLM 部署模型并压测吞吐",
            objective="本地部署一个模型并拿到吞吐/延迟基线数据",
            difficulty="intermediate",
            acceptance=[
                "vLLM serve 成功并 curl 通",
                "吞吐与首 token 延迟记录成表",
                "压测脚本入册（可复跑）",
            ],
            resources=["vLLM Documentation", "Mini Post-Training Lab 07_inference"],
            base_minutes=90,
        ),
    ],
    "VLM": [
        TaskTemplate(
            title="多模态 SFT 数据格式调研",
            objective="弄清图文指令数据的主流格式与一条完整样本长什么样",
            difficulty="beginner",
            acceptance=[
                "对比 ≥2 种数据格式（如 LLaVA 与 Qwen-VL）",
                "手工构造 ≥10 条样本",
                "记录进 LearningLog",
            ],
            resources=["Hugging Face Multimodal / LLaVA", "Qwen2.5-VL 技术报告"],
            base_minutes=60,
        ),
    ],
}


def get_template(skill: str, difficulty: str | None = None) -> TaskTemplate | None:
    """按技能名取模板。difficulty 为 None 时返回该技能第一个模板。

    Args:
        skill: 技能名称（如 "SFT"）
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
