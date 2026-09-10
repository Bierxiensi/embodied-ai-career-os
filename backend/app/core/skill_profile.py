"""真实技能画像（单一数据源）。

求职看板的匹配度、技能缺口、Dashboard 雷达图全部读这张表的数据。
一旦这里失真，整块看板的结论都是错的，所以：

    **改技能等级只改这个文件**，不要改 db/base.py 的种子副本。

评级口径（0-5）：
    0 未接触   1 概念层   2 能跑通 demo   3 独立做过项目
    4 能讲清取舍与踩坑   5 能带人 / 能定方案

evidence 必须是可对外陈述的事实（项目名 / 论文 / 可量化结果），
不要写"熟悉""了解"这类无法验证的形容词。

================================================================================
2026-09-10 战略调整（增量，非重写）
================================================================================
依据《求职 Agent 开发与运行规范 v2.0》：主线切为 LLM + VLM。

处理原则：**旧技能降权保留，不删除**。
- 新增 A/B/C 级技能（LLM Core / Training / Inference / VLM）
- 具身相关技能（ROS2 / VLA / Robot Learning / Isaac / Sim2Real / MoveIt2 /
  Mujoco）**保留记录与 evidence**，但把 target_level 设为等于 level
  → gap 恒为 0，看板不会再把它们排进"今天该学什么"，但历史积累仍在，
    简历叙事里可作为工程能力旁证

最后校准：2026-09-10
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SkillProfile:
    """一项技能的真实自评。"""

    name: str                            # 技能名（与 target_roles.required_skills 对齐）
    category: str                        # Strong / Medium / Weak
    level: int                           # 当前等级 0-5
    target_level: int                    # 目标等级 0-5（等于 level = 冻结，不再投入）
    evidence: list[str] = field(default_factory=list)   # 可验证证据


SKILL_PROFILE: list[SkillProfile] = [
    # ══════════════════════════════════════════════════════════════════════
    # A 级 —— 30 天必须打穿（v2.0 §18）
    # ══════════════════════════════════════════════════════════════════════
    SkillProfile(
        name="Transformer", category="Medium", level=3, target_level=5,
        evidence=["能讲清 Encoder/Decoder 与 Causal LM 差异", "EI 论文 STM-SHAP 基于时序 Transformer"],
    ),
    SkillProfile(
        name="Attention", category="Medium", level=3, target_level=5,
        evidence=["理解 QKV / scaled dot-product / causal mask", "尚未手写 MHA 并单测（Day2 目标）"],
    ),
    SkillProfile(
        name="RoPE", category="Weak", level=1, target_level=5, evidence=["仅概念层，未推导旋转矩阵"],
    ),
    SkillProfile(
        name="RMSNorm", category="Weak", level=2, target_level=5, evidence=["知道与 LayerNorm 的差异，未手写实现"],
    ),
    SkillProfile(
        name="SwiGLU", category="Weak", level=2, target_level=5, evidence=["知道 FFN 变体，未实现对比"],
    ),
    SkillProfile(
        name="Pretraining", category="Weak", level=2, target_level=4,
        evidence=["理解数据/算力/显存/稳定性要素", "未独立跑过预训练"],
    ),
    SkillProfile(
        name="SFT", category="Medium", level=3, target_level=5,
        evidence=["科研知识库：800 条高质量指令数据构造", "理解 loss mask 与 chat template"],
    ),
    SkillProfile(
        name="LoRA/QLoRA", category="Medium", level=3, target_level=5,
        evidence=["科研知识库 LoRA 微调落地", "能解释 ΔW=BA / rank / alpha（需补显存对比实验）"],
    ),
    SkillProfile(
        name="KV Cache", category="Weak", level=2, target_level=5,
        evidence=["知道推理阶段缓存 K/V", "未做 prefill/decode 时延拆解"],
    ),
    SkillProfile(
        name="Prefill/Decode", category="Weak", level=2, target_level=5,
        evidence=["概念层，未实测 TTFT / TPS"],
    ),
    SkillProfile(
        name="Quantization", category="Weak", level=2, target_level=4,
        evidence=["技术栈含 ONNX / TensorRT", "未系统做 INT8/INT4 精度-时延对比"],
    ),
    SkillProfile(
        name="FSDP/ZeRO", category="Weak", level=1, target_level=3, evidence=["仅概念层"],
    ),
    SkillProfile(
        name="vLLM", category="Weak", level=2, target_level=4,
        evidence=["技术栈含 vLLM / Ollama", "未做完整 serving benchmark"],
    ),

    # ══════════════════════════════════════════════════════════════════════
    # B 级 —— 必须理解（v2.0 §18）
    # ══════════════════════════════════════════════════════════════════════
    SkillProfile(
        name="MoE", category="Weak", level=2, target_level=3,
        evidence=["关注 Qwen3 MoE（30B-A3B / 35B-A3B）本地推理方案"],
    ),
    SkillProfile(
        name="Distributed Training", category="Weak", level=1, target_level=3, evidence=["仅概念层"],
    ),
    SkillProfile(
        name="FlashAttention", category="Weak", level=1, target_level=3, evidence=["仅概念层"],
    ),
    SkillProfile(
        name="Gradient Checkpointing", category="Weak", level=1, target_level=3, evidence=["仅概念层"],
    ),
    SkillProfile(
        name="DPO", category="Weak", level=1, target_level=3, evidence=["仅概念层"],
    ),
    SkillProfile(
        name="RLHF", category="Weak", level=1, target_level=3, evidence=["仅概念层"],
    ),

    # ══════════════════════════════════════════════════════════════════════
    # C 级 —— 一个月理解即可（VLM / 多模态）
    # ══════════════════════════════════════════════════════════════════════
    SkillProfile(
        name="ViT", category="Weak", level=2, target_level=4,
        evidence=["理解 Patch Embedding / Visual Tokens", "未手算 token 数与分辨率关系"],
    ),
    SkillProfile(
        name="Multimodal Alignment", category="Weak", level=1, target_level=4,
        evidence=["知道 Projector 的作用", "未讲清 vision/language 空间差异"],
    ),
    SkillProfile(
        name="VLM", category="Weak", level=1, target_level=4,
        evidence=["对 LLaVA / Q-Former 有概念", "未完成一次 VLM 微调"],
    ),
    SkillProfile(
        name="CLIP", category="Weak", level=2, target_level=3, evidence=["理解对比学习目标"],
    ),
    SkillProfile(
        name="BLIP", category="Weak", level=1, target_level=3, evidence=["仅概念层"],
    ),
    SkillProfile(
        name="LLaVA", category="Weak", level=1, target_level=3, evidence=["仅概念层"],
    ),
    SkillProfile(
        name="Q-Former", category="Weak", level=0, target_level=2, evidence=[],
    ),
    SkillProfile(
        name="Flamingo", category="Weak", level=0, target_level=2, evidence=[],
    ),

    # ══════════════════════════════════════════════════════════════════════
    # 现有强项 —— 求职基本盘
    # ══════════════════════════════════════════════════════════════════════
    SkillProfile(
        name="Agent Application", category="Strong", level=4, target_level=5,
        evidence=[
            "标书智能审核 Agent：ReAct 多轮推理，抽取覆盖率 56%→90%，单份 30min→10min，累计 3000+ 份",
            "一体化研发协同平台：集成 OpenHands + Claude Code CLI + MCP Server，接入 30+ 人，交付周期缩短 200%",
            "Embodied AI Career OS：Multi-Agent Runtime（supervisor → planner/reviewer/career/research）",
        ],
    ),
    SkillProfile(
        name="RAG", category="Strong", level=4, target_level=5,
        evidence=[
            "领域科研知识库：查询改写 Schema Prompt，Top-5 命中率 56%→78%，结构化文档召回 85%，扫描件 72%",
        ],
    ),
    SkillProfile(
        name="Python", category="Strong", level=4, target_level=5,
        evidence=["FastAPI 后端全栈开发", "flood-forecast-simple 洪水预报系统", "PyTorch 建模与训练脚本"],
    ),
    SkillProfile(
        name="PyTorch", category="Medium", level=3, target_level=4,
        evidence=["STM-SHAP 洪水预报模型（一作 IEEE ISCTIS 2026）", "RL-RA-QR 概率预报学位论文"],
    ),
    SkillProfile(
        name="Deep Learning", category="Medium", level=3, target_level=4,
        evidence=["时序预测 / 时空信息融合 / 文本分类 / 实体关系抽取落地", "分位数回归与不确定性建模"],
    ),
    SkillProfile(
        name="Inference Optimization", category="Weak", level=2, target_level=4,
        evidence=["技术栈含 ONNX / TensorRT / vLLM / Ollama", "未形成系统性 benchmark 结论"],
    ),
    SkillProfile(
        name="Linux", category="Medium", level=3, target_level=4,
        evidence=["日常开发环境与部署（ROS2 环境、本地推理机）"],
    ),
    SkillProfile(
        name="Docker", category="Medium", level=3, target_level=3, evidence=["本地推理与服务编排"],
    ),
    SkillProfile(
        name="FastAPI", category="Strong", level=4, target_level=4, evidence=["Career OS 后端全栈实现"],
    ),

    # ---------- 科研底座（博士叙事起点，不是"与未来无关的旧方向"）----------
    SkillProfile(
        name="Small-data Forecasting", category="Strong", level=4, target_level=4,
        evidence=["小样本洪水预报研究", "EI 论文 STM-SHAP（一作，已见刊索引）"],
    ),
    SkillProfile(
        name="Explainability", category="Strong", level=4, target_level=4,
        evidence=["SHAP 可解释性分析", "互信息过滤冗余与滞后特征"],
    ),

    # ---------- 历史主线（工程能力背书，非当前方向）----------
    SkillProfile(
        name="Frontend", category="Strong", level=4, target_level=4,
        evidence=["React / Vue 企业级项目", "Cesium / WebGIS 三维可视化（中科院地理所）"],
    ),
    SkillProfile(
        name="Web Engineering", category="Strong", level=4, target_level=4,
        evidence=["Next.js 16 全栈工程化", "qiankun 微前端、Docker / CI 部署"],
    ),
    SkillProfile(
        name="C++", category="Weak", level=2, target_level=2, evidence=["C# 桌面应用与 MicroPython 经验迁移"],
    ),

    # ══════════════════════════════════════════════════════════════════════
    # D 级 —— 冻结区（v2.0 §19：30 天主动不深挖）
    # target_level == level → gap 恒为 0，看板不再推动，但资产与证据完整保留
    # ══════════════════════════════════════════════════════════════════════
    SkillProfile(
        name="ROS2", category="Weak", level=2, target_level=2,
        evidence=["so101/v1_ros2：publisher / subscriber / launch demo 已跑通"],
    ),
    SkillProfile(
        name="Robot Learning", category="Weak", level=2, target_level=2,
        evidence=["SO101 遥操作采集 20 episodes", "ACT 训练完成、推理可用，泛化成功率待提升"],
    ),
    SkillProfile(
        name="Mujoco Simulation", category="Weak", level=2, target_level=2,
        evidence=["so101/v0_mujoco：关节控制 + FK 验证 + 轨迹记录"],
    ),
    SkillProfile(
        name="Isaac", category="Weak", level=1, target_level=1,
        evidence=["Isaac Sim / Isaac Lab 安装并跑通官方示例"],
    ),
    SkillProfile(
        name="VLA", category="Weak", level=1, target_level=1,
        evidence=["对 SmolVLA / Pi0 / Diffusion Policy 有概念，未实操部署"],
    ),
    SkillProfile(
        name="Sim2Real", category="Weak", level=0, target_level=0,
        evidence=[],   # 长期保留的卡点，当前不投入
    ),
    SkillProfile(
        name="MoveIt2", category="Weak", level=0, target_level=0, evidence=[],
    ),
]


def profile_map() -> dict[str, SkillProfile]:
    """按技能名小写索引，便于对齐现有库数据。"""
    return {p.name.lower(): p for p in SKILL_PROFILE}


def frozen_skills() -> list[str]:
    """返回被冻结的技能名（target == level），供 Planner 与看板过滤。"""
    return [p.name for p in SKILL_PROFILE if p.target_level <= p.level]
