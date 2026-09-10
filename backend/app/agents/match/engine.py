"""JD 匹配引擎（纯规则，可解释，不依赖 LLM）。

设计偏离说明（重要）：
    《求职 Agent 设计》把 MatchAgent 列为 BaseAgent 子类，但 BaseAgent 抽象强制
    build_graph() 返回 LangGraph CompiledGraph。对一个纯同步的、需要可单测 / 可解释 /
    不烧 token 的评分函数套 LangGraph 是过度设计，也违背用户"利用现有基建、不过度搭建"
    的反馈与规范 §0.2「匹配先用纯规则」。因此这里实现为独立可测模块，API 直接调用。
    它仍属于"Agent 能力"范畴，只是不强制 LangGraph 契约。

评分口径严格对齐《求职 Agent 开发与运行规范 v2.0 §22》：
    score = 技术栈 40% + 项目 25% + 学历/年限 15% + 科研 10% + 行业 10%
    A≥80 | B≥65 | C≥50 | D<50

所有维度的计算都是确定性规则，前端抽屉可逐维展示"为什么是这个分"。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.skill_profile import SKILL_PROFILE
from app.models.job_match import (
    DIM_EDU_EXP,
    DIM_INDUSTRY,
    DIM_PROJECT,
    DIM_RESEARCH,
    DIM_TECH,
    WEIGHT_EDU_EXP,
    WEIGHT_INDUSTRY,
    WEIGHT_PROJECT,
    WEIGHT_RESEARCH,
    WEIGHT_TECH,
    grade_of,
)

# ───────────────────────────── 候选人硬事实（镜像 docs/MY_CONTEXT.md） ─────────────────────────────
# 这些常量即"用户简历事实"，必须和 docs/MY_CONTEXT.md 保持一致；改这里也要改那里。
USER_EDUCATION = "硕士"      # 北航软件工程非全日制研究生（在读）→ 按硕士计
USER_YEARS = 6               # 2019 本科毕业至今约 6 年相关经验
USER_HAS_PAPER = True        # EI 一作（STM-SHAP，IEEE ISCTIS 2026）

# 行业分：主攻/卡位/保底赛道均属 AI 大模型，给满分；具身方向属转型，降权
_INDUSTRY_FULL = {"llm", "vlm", "ai-algo"}
_INDUSTRY_TRANSITION = {"embodied", "robot-software"}

# 技能要求默认等级（与 TARGET_ROLES.required_level 对齐）
DEFAULT_REQUIRED_LEVEL = 4


@dataclass
class MatchResult:
    """一次匹配结果。"""

    match_score: int
    grade: str
    dimension_scores: dict[str, int]
    gaps: list[dict] = field(default_factory=list)
    matched_track: str | None = None


def _coverage(level: int) -> float:
    """技能等级 → 覆盖度 0-1（5 级封顶）。"""
    return min(max(level, 0) / 5.0, 1.0)


def _norm(name: str) -> str:
    return name.strip().lower()


# 规范技能词表（用于解析 JD 时归一化输出）
_PROFILE_NAMES = {_norm(p.name): p.name for p in SKILL_PROFILE}


# JD 关键词 → 规范技能名 的别名表（小写子串匹配）
_JD_ALIASES: dict[str, str] = {
    "transformer": "Transformer",
    "attention": "Attention",
    "self-attention": "Attention",
    "rope": "RoPE",
    "rmsnorm": "RMSNorm",
    "swiglu": "SwiGLU",
    "预训练": "Pretraining",
    "pretrain": "Pretraining",
    "sft": "SFT",
    "指令微调": "SFT",
    "lora": "LoRA/QLoRA",
    "qlora": "LoRA/QLoRA",
    "低秩适配": "LoRA/QLoRA",
    "vllm": "vLLM",
    "kv cache": "KV Cache",
    "kv-cache": "KV Cache",
    "kv 缓存": "KV Cache",
    "prefill": "Prefill/Decode",
    "decode": "Prefill/Decode",
    "量化": "Quantization",
    "quantization": "Quantization",
    "deepspeed": "FSDP/ZeRO",
    "fsdp": "FSDP/ZeRO",
    "zero": "FSDP/ZeRO",
    "moe": "MoE",
    "混合专家": "MoE",
    "flashattention": "FlashAttention",
    "dpo": "DPO",
    "rlhf": "RLHF",
    "人类反馈": "RLHF",
    "vit": "ViT",
    "vision transformer": "ViT",
    "clip": "CLIP",
    "blip": "BLIP",
    "llava": "LLaVA",
    "q-former": "Q-Former",
    "qformer": "Q-Former",
    "flamingo": "Flamingo",
    "多模态": "Multimodal Alignment",
    "对齐": "Multimodal Alignment",
    "vision-language": "Multimodal Alignment",
    "vlm": "VLM",
    "视觉语言": "VLM",
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "python": "Python",
    "深度学习": "Deep Learning",
    "deep learning": "Deep Learning",
    "神经网络": "Deep Learning",
    "rag": "RAG",
    "检索增强": "RAG",
    "agent": "Agent Application",
    "智能体": "Agent Application",
    "推理优化": "Inference Optimization",
    "推理加速": "Inference Optimization",
    "inference": "Inference Optimization",
    "linux": "Linux",
    "docker": "Docker",
    "fastapi": "FastAPI",
    "ros2": "ROS2",
    "ros 2": "ROS2",
    "vla": "VLA",
    "robot learning": "Robot Learning",
    "机械臂": "Robot Learning",
}


class JDParser:
    """从 JD 全文抽取结构化技能关键词（规则关键词匹配，可解释）。"""

    @staticmethod
    def parse_required_skills(jd_text: str | None) -> list[str]:
        """JD 文本 → 规范技能名列表（去重、保序）。

        仅做子串命中，不做语义理解；命中别名表即归一化到规范技能名。
        未命中任何别名的 JD 文本返回空列表（由匹配引擎回落到 track 的 required_skills）。
        """
        if not jd_text:
            return []

        text = jd_text.lower()
        found: list[str] = []
        seen_norm: set[str] = set()
        for alias, canonical in _JD_ALIASES.items():
            if alias in text and canonical not in seen_norm:
                found.append(canonical)
                seen_norm.add(canonical)
        return found


class MatchEngine:
    """JD × 能力画像 匹配评分（纯规则）。

    compute 接收已归一化的入参，便于单测（不依赖 DB / LLM）。
    API 层负责：从 JobPosting 取字段、从 Skill 表构建 skill_levels 映射后调用。
    """

    @staticmethod
    def compute(
        required_skills: list[str] | None,
        track: str,
        education: str | None = None,
        min_years: int | None = None,
        paper_required: bool = False,
        skill_levels: dict[str, int] | None = None,
    ) -> MatchResult:
        """计算匹配结果。

        Args:
            required_skills: JD 解析出的规范技能名列表（可为空）
            track: 对标赛道 key（llm/vlm/ai-algo/embodied/...）
            education: JD 学历要求（本科/硕士/博士/None）
            min_years: JD 经验年数要求
            paper_required: JD 是否要求论文
            skill_levels: 候选人的 "规范技能名(小写)" -> 等级(0-5) 映射
        """
        skill_levels = skill_levels or {}

        # 解析为空时回落：track 无 required 信息也行，技术栈维度记 0（信息缺失）
        required = list(required_skills or [])
        levels = [skill_levels.get(_norm(n), 0) for n in required]

        # ── 维度1：技术栈 40% ──
        if required:
            tech = int(round(sum(_coverage(l) for l in levels) / len(required) * 100))
        else:
            tech = 0

        # ── 维度2：项目经验 25% ──
        # 基线 15（有通用工程经验）+ 每个"能独立做"(level>=3) 的 JD 技能 +18，封顶 100
        hands_on = sum(1 for l in levels if l >= 3)
        project = min(100, 15 + 18 * hands_on)

        # ── 维度3：学历 / 工作年限 15% ──
        edu = _edu_exp_score(education, min_years)

        # ── 维度4：科研 / 论文 10% ──
        if not paper_required:
            research = 100  # 不要求论文 → 中性满分
        else:
            research = 100 if USER_HAS_PAPER else 30

        # ── 维度5：行业匹配 10% ──
        if track in _INDUSTRY_FULL:
            industry = 100
        elif track in _INDUSTRY_TRANSITION:
            industry = 70
        else:
            industry = 85  # other：通用 AI 岗，略低于主攻但高于转型

        score = int(round(
            WEIGHT_TECH * tech
            + WEIGHT_PROJECT * project
            + WEIGHT_EDU_EXP * edu
            + WEIGHT_RESEARCH * research
            + WEIGHT_INDUSTRY * industry
        ))
        score = max(0, min(100, score))

        # ── 差距清单（按 gap 降序）──
        gaps: list[dict] = []
        for name, lvl in zip(required, levels):
            gap = max(DEFAULT_REQUIRED_LEVEL - lvl, 0)
            if gap > 0:
                gaps.append({
                    "skill": name,
                    "level": lvl,
                    "required": DEFAULT_REQUIRED_LEVEL,
                    "gap": gap,
                })
        gaps.sort(key=lambda g: (-g["gap"], g["skill"]))

        return MatchResult(
            match_score=score,
            grade=grade_of(score),
            dimension_scores={
                DIM_TECH: tech,
                DIM_PROJECT: project,
                DIM_EDU_EXP: edu,
                DIM_RESEARCH: research,
                DIM_INDUSTRY: industry,
            },
            gaps=gaps,
            matched_track=track,
        )


def _edu_exp_score(education: str | None, min_years: int | None) -> int:
    """学历 / 年限规则分（0-100）。"""
    # 学历匹配
    req = (education or "").strip()
    if req in ("", "本科及以上", "本科"):
        edu_match = 1.0
    elif req in ("硕士", "硕士及以上"):
        edu_match = 1.0
    elif req == "博士":
        edu_match = 0.6  # 在读硕士，博士岗偏弱
    else:
        edu_match = 0.8

    # 年限匹配
    if min_years is None:
        exp_match = 1.0
    else:
        exp_match = min(USER_YEARS / max(min_years, 1), 1.0)

    return int(round((0.5 * edu_match + 0.5 * exp_match) * 100))
