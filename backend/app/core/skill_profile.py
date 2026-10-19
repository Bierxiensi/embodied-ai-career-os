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

最后校准：2026-09-18（v3.0：主轴由 LLM+VLM 调整为 Post-Training，新增 GRPO，DPO/RLHF 升为主攻赛道要求）
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

    # Phase 3（2026-09-22）新增：六域归属，供 R2 域聚合雷达（long_term 模式）使用。
    #
    # 为什么放在 Python 而不加 skills.domain 列：
    #   技能等级早已是"只改这个文件"的单一真源（见模块 docstring），
    #   域归属与等级同源同命 —— 再加一列 DB 副本只会多一处可漂移的真相。
    #   读接口（/api/skills、/api/skills/domains）按技能名回查本表补 domain。
    #
    # None 的语义：**不在六域内**。当前仅 7 项冻结/历史旁证技能（ROS2 / VLA /
    #   Robot Learning / Mujoco Simulation / Isaac / Sim2Real / MoveIt2）为 None。
    #   它们不属于在职转型的六域推进范围，故不参与 R2 雷达的域聚合 ——
    #   与 task_scope 的"冻结赛道不占默认视图"是同一个取舍，方向一致。
    domain: str | None = None


SKILL_PROFILE: list[SkillProfile] = [
    # ══════════════════════════════════════════════════════════════════════
    # A 级 —— 30 天必须打穿（v2.0 §18）
    # ══════════════════════════════════════════════════════════════════════
    SkillProfile(
        name="Transformer", domain="llm_foundation", category="Medium", level=3, target_level=5,
        evidence=["能讲清 Encoder/Decoder 与 Causal LM 差异", "EI 论文 STM-SHAP 基于时序 Transformer"],
    ),
    SkillProfile(
        name="Attention", domain="llm_foundation", category="Medium", level=3, target_level=5,
        evidence=["理解 QKV / scaled dot-product / causal mask", "尚未手写 MHA 并单测（Day2 目标）"],
    ),
    SkillProfile(
        name="RoPE", domain="llm_foundation", category="Weak", level=1, target_level=5, evidence=["仅概念层，未推导旋转矩阵"],
    ),
    SkillProfile(
        name="RMSNorm", domain="llm_foundation", category="Weak", level=2, target_level=5, evidence=["知道与 LayerNorm 的差异，未手写实现"],
    ),
    SkillProfile(
        name="SwiGLU", domain="llm_foundation", category="Weak", level=2, target_level=5, evidence=["知道 FFN 变体，未实现对比"],
    ),
    SkillProfile(
        name="Pretraining", domain="llm_foundation", category="Weak", level=2, target_level=4,
        evidence=["理解数据/算力/显存/稳定性要素", "未独立跑过预训练"],
    ),
    SkillProfile(
        name="SFT", domain="finetune_alignment", category="Medium", level=3, target_level=5,
        evidence=["科研知识库：800 条高质量指令数据构造", "理解 loss mask 与 chat template"],
    ),
    SkillProfile(
        name="LoRA/QLoRA", domain="finetune_alignment", category="Medium", level=3, target_level=5,
        evidence=["科研知识库 LoRA 微调落地", "能解释 ΔW=BA / rank / alpha（需补显存对比实验）"],
    ),
    SkillProfile(
        name="KV Cache", domain="inference_engineering", category="Weak", level=2, target_level=5,
        evidence=["知道推理阶段缓存 K/V", "未做 prefill/decode 时延拆解"],
    ),
    SkillProfile(
        name="Prefill/Decode", domain="inference_engineering", category="Weak", level=2, target_level=5,
        evidence=["概念层，未实测 TTFT / TPS"],
    ),
    SkillProfile(
        name="Quantization", domain="inference_engineering", category="Weak", level=2, target_level=4,
        evidence=["技术栈含 ONNX / TensorRT", "未系统做 INT8/INT4 精度-时延对比"],
    ),
    SkillProfile(
        name="FSDP/ZeRO", domain="llm_foundation", category="Weak", level=1, target_level=3, evidence=["仅概念层"],
    ),
    SkillProfile(
        name="vLLM", domain="inference_engineering", category="Weak", level=2, target_level=4,
        evidence=["技术栈含 vLLM / Ollama", "未做完整 serving benchmark"],
    ),

    # ══════════════════════════════════════════════════════════════════════
    # B 级 —— 必须理解（v2.0 §18）
    # ══════════════════════════════════════════════════════════════════════
    SkillProfile(
        name="MoE", domain="llm_foundation", category="Weak", level=2, target_level=3,
        evidence=["关注 Qwen3 MoE（30B-A3B / 35B-A3B）本地推理方案"],
    ),
    SkillProfile(
        name="Distributed Training", domain="llm_foundation", category="Weak", level=1, target_level=3, evidence=["仅概念层"],
    ),
    SkillProfile(
        name="FlashAttention", domain="llm_foundation", category="Weak", level=1, target_level=4, evidence=["仅概念层"],
    ),
    SkillProfile(
        name="Gradient Checkpointing", domain="llm_foundation", category="Weak", level=1, target_level=3, evidence=["仅概念层"],
    ),
    SkillProfile(
        name="DPO", domain="finetune_alignment", category="Weak", level=1, target_level=3, evidence=["仅概念层"],
    ),
    SkillProfile(
        name="RLHF", domain="finetune_alignment", category="Weak", level=1, target_level=3, evidence=["仅概念层"],
    ),
    SkillProfile(
        name="GRPO", domain="finetune_alignment", category="Weak", level=1, target_level=3,
        evidence=["仅概念层，未实现 rollout / reward / advantage 闭环"],
    ),

    # ══════════════════════════════════════════════════════════════════════
    # C 级 —— 一个月理解即可（VLM / 多模态）
    # ══════════════════════════════════════════════════════════════════════
    SkillProfile(
        name="ViT", domain="multimodal", category="Weak", level=2, target_level=4,
        evidence=["理解 Patch Embedding / Visual Tokens", "未手算 token 数与分辨率关系"],
    ),
    SkillProfile(
        name="Multimodal Alignment", domain="multimodal", category="Weak", level=1, target_level=4,
        evidence=["知道 Projector 的作用", "未讲清 vision/language 空间差异"],
    ),
    SkillProfile(
        name="VLM", domain="multimodal", category="Weak", level=1, target_level=4,
        evidence=["对 LLaVA / Q-Former 有概念", "未完成一次 VLM 微调"],
    ),
    SkillProfile(
        name="CLIP", domain="multimodal", category="Weak", level=2, target_level=3, evidence=["理解对比学习目标"],
    ),
    SkillProfile(
        name="BLIP", domain="multimodal", category="Weak", level=1, target_level=3, evidence=["仅概念层"],
    ),
    SkillProfile(
        name="LLaVA", domain="multimodal", category="Weak", level=1, target_level=3, evidence=["仅概念层"],
    ),
    SkillProfile(
        name="Q-Former", domain="multimodal", category="Weak", level=0, target_level=2, evidence=[],
    ),
    SkillProfile(
        name="Flamingo", domain="multimodal", category="Weak", level=0, target_level=2, evidence=[],
    ),

    # ══════════════════════════════════════════════════════════════════════
    # 现有强项 —— 求职基本盘
    # ══════════════════════════════════════════════════════════════════════
    # v3.3：护城河维持，不因推理支加权降权（Agent Application / RAG / Python 三项 target 不动）
    SkillProfile(
        name="Agent Application", domain="engineering_delivery", category="Strong", level=4, target_level=5,
        evidence=[
            "标书智能审核 Agent：ReAct 多轮推理，抽取覆盖率 56%→90%，单份 30min→10min，累计 3000+ 份",
            "一体化研发协同平台：集成 OpenHands + Claude Code CLI + MCP Server，接入 30+ 人，交付周期缩短 200%",
            "Embodied AI Career OS：Multi-Agent Runtime（supervisor → planner/reviewer/career/research）",
        ],
    ),
    SkillProfile(
        name="RAG", domain="engineering_delivery", category="Strong", level=4, target_level=5,
        evidence=[
            "领域科研知识库：查询改写 Schema Prompt，Top-5 命中率 56%→78%，结构化文档召回 85%，扫描件 72%",
        ],
    ),
    SkillProfile(
        name="Python", domain="engineering_delivery", category="Strong", level=4, target_level=5,
        evidence=["FastAPI 后端全栈开发", "flood-forecast-simple 洪水预报系统", "PyTorch 建模与训练脚本"],
    ),
    SkillProfile(
        name="PyTorch", domain="engineering_delivery", category="Medium", level=3, target_level=4,
        evidence=["STM-SHAP 洪水预报模型（一作 IEEE ISCTIS 2026）", "RL-RA-QR 概率预报学位论文"],
    ),
    SkillProfile(
        name="Deep Learning", domain="engineering_delivery", category="Medium", level=3, target_level=4,
        evidence=["时序预测 / 时空信息融合 / 文本分类 / 实体关系抽取落地", "分位数回归与不确定性建模"],
    ),
    SkillProfile(
        name="Inference Optimization", domain="inference_engineering", category="Weak", level=2, target_level=4,
        evidence=["技术栈含 ONNX / TensorRT / vLLM / Ollama", "未形成系统性 benchmark 结论"],
    ),
    SkillProfile(
        name="Linux", domain="engineering_delivery", category="Medium", level=3, target_level=4,
        evidence=["日常开发环境与部署（ROS2 环境、本地推理机）"],
    ),
    SkillProfile(
        name="Docker", domain="engineering_delivery", category="Medium", level=3, target_level=3, evidence=["本地推理与服务编排"],
    ),
    SkillProfile(
        name="FastAPI", domain="engineering_delivery", category="Strong", level=4, target_level=4, evidence=["Career OS 后端全栈实现"],
    ),

    # ---------- 科研底座（博士叙事起点，不是"与未来无关的旧方向"）----------
    SkillProfile(
        name="Small-data Forecasting", domain="research_foundation", category="Strong", level=4, target_level=4,
        evidence=["小样本洪水预报研究", "EI 论文 STM-SHAP（一作，已见刊索引）"],
    ),
    SkillProfile(
        name="Explainability", domain="research_foundation", category="Strong", level=4, target_level=4,
        evidence=["SHAP 可解释性分析", "互信息过滤冗余与滞后特征"],
    ),
    SkillProfile(
        name="Time Series Forecasting", domain="research_foundation", category="Strong", level=4, target_level=4,
        evidence=[
            "学位论文 RL-RA-QR 洪水概率预报（强化学习 + 分位数回归，多步滚动预报）",
            "STM-SHAP 时序可解释性（一作 IEEE ISCTIS 2026，EI）",
            "多流域对比 q99 分位数预报；时空信息融合与误差归因",
        ],
    ),

    # ---------- 历史主线（工程能力背书，非当前方向）----------
    SkillProfile(
        name="Frontend", domain="engineering_delivery", category="Strong", level=4, target_level=4,
        evidence=["React / Vue 企业级项目", "Cesium / WebGIS 三维可视化（中科院地理所）"],
    ),
    SkillProfile(
        name="Web Engineering", domain="engineering_delivery", category="Strong", level=4, target_level=4,
        evidence=["Next.js 16 全栈工程化", "qiankun 微前端、Docker / CI 部署"],
    ),
    SkillProfile(
        name="C++", domain="engineering_delivery", category="Weak", level=2, target_level=2, evidence=["C# 桌面应用与 MicroPython 经验迁移"],
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


# ══════════════════════════════════════════════════════════════════════════════
# 六域（Phase 3 / R2 域聚合雷达的轴定义）
# ══════════════════════════════════════════════════════════════════════════════
#
# 为什么是"域"而不是 SkillProfile.category：
#   category 只有 Strong / Medium / Weak 三档，描述的是**自评强度**，不是知识结构。
#   拿它当雷达轴会得到一张"强/中/弱"图 —— 形状没有解释力（SkillRadarCard 的注释
#   记过同一个教训：早期用全量技能当轴同样是形状噪音）。
#   六域描述的是**能力栈里的位置**，回答"我在这一层投入够不够"。
#
# 顺序即雷达轴的绘制顺序（从上方开始顺时针）。顺序本身是产品决策，故显式固定：
#   模型底层（LLM基础）→ 训练（微调对齐）→ 推理（推理工程）→ 模型分支（多模态）
#   → 交付（工程交付）→ 学术（科研底座）。

DOMAIN_LLM_FOUNDATION = "llm_foundation"
DOMAIN_FINETUNE_ALIGNMENT = "finetune_alignment"
DOMAIN_INFERENCE_ENGINEERING = "inference_engineering"
DOMAIN_MULTIMODAL = "multimodal"
DOMAIN_ENGINEERING_DELIVERY = "engineering_delivery"
DOMAIN_RESEARCH_FOUNDATION = "research_foundation"

# (key, 显示名)：key 是稳定业务标识（前端与测试按它引用），显示名可改。
SKILL_DOMAINS: tuple[tuple[str, str], ...] = (
    (DOMAIN_LLM_FOUNDATION, "LLM基础"),
    (DOMAIN_FINETUNE_ALIGNMENT, "微调对齐"),
    (DOMAIN_INFERENCE_ENGINEERING, "推理工程"),
    (DOMAIN_MULTIMODAL, "多模态"),
    (DOMAIN_ENGINEERING_DELIVERY, "工程交付"),
    (DOMAIN_RESEARCH_FOUNDATION, "科研底座"),
)

DOMAIN_LABELS: dict[str, str] = {key: label for key, label in SKILL_DOMAINS}

# 域的划分（哪项技能属于哪个域）**唯一权威**是每项 SkillProfile.domain，
# 这里不再抄一份成员名单 —— 抄一份就是第二份真相。
DOMAIN_ORDER: dict[str, int] = {key: i for i, (key, _) in enumerate(SKILL_DOMAINS)}


def domain_of(skill_name: str) -> str | None:
    """按技能名（大小写不敏感）查六域 key；不在六域内返回 None。"""
    profile = profile_map().get((skill_name or "").strip().lower())
    return profile.domain if profile else None


def skills_in_domain(domain_key: str) -> list[SkillProfile]:
    """该域下的全部技能，按 SKILL_PROFILE 原顺序（= 由浅入深的人工排序）。"""
    return [p for p in SKILL_PROFILE if p.domain == domain_key]


def unmapped_skills() -> list[SkillProfile]:
    """不在六域内的技能（当前为冻结 / 历史旁证区，共 7 项）。"""
    return [p for p in SKILL_PROFILE if p.domain is None]


def domains_are_all_populated() -> bool:
    """护栏：SKILL_DOMAINS 声明的每个域都必须真的有技能，否则雷达会出现空轴。

    空轴在 RadarChart 里会退化成中心的一个点，均值也会变成 0/0。
    这里给出布尔，供测试与 /api/skills/domains 的自检使用。
    """
    return all(skills_in_domain(key) for key, _ in SKILL_DOMAINS)

