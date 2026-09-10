"""30 天施工计划的课程脊梁（唯一事实来源）。

来源：《30-Day LLM → VLM 求职施工计划 v2.0》§四 ~ §八。
本文件是 **计划内容的唯一出处** —— 改计划 = 改这个文件 + 重跑
`scripts/seed_plan_30d.py`，不做 CRUD 管理界面（见 docs/platform-direction-30day.md §八）。

为什么不做数据库 CRUD：
    计划会变（比如 Day 9 显存计算要花两天），但变更频率远低于查看频率。
    给 30 条固定记录做一套管理界面，是典型的"建设平台吞掉学习时间"。
    幂等种子脚本 + 版本控制，改计划可追溯、可回滚。

设计要点：
1. seq（1..30）是**不可变的课程序号**，绝不与日历日期绑定。
   日期由 DayProgress 记录（P1），落后只提示、不自动顺延 ——
   否则滑一天后面全错位，30 天会变成 45 天。
2. track_key 复用 tasks 的赛道口径（llm / vlm / ai-algo / embodied），
   周 1-2 是 LLM 主攻，周 3 切换 VLM 卡位，周 4 回到包装与投递。
3. 每天固定产出「四件套」：代码 / 笔记 / 面试题 ≥5 / git commit。
   本文件只声明当天的面试题主题，题目本身由用户在完成任务时录入。

⚠️ 本文件里的字符串不要出现裸分号 —— 虽然这里不是 SQL，
   但保持与 migrations/ 同一套"避免分号"习惯，方便复制粘贴。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class PlanDaySeed:
    """课程中的一天。frozen 防止种子脚本误改。"""

    seq: int                      # 1..30，不可变课程序号
    phase: int                    # 阶段（周）：1..4
    phase_name: str               # 阶段名，用于总览分带
    title: str                    # 当天主题（一句话）
    theme: str                    # 归属技术域，用于分组展示
    objectives: tuple[str, ...]   # 学习目标（要搞懂什么）
    acceptance: tuple[str, ...]   # 验收标准（做到什么算过）
    interview_topics: tuple[str, ...]   # 当天必须能回答的面试题
    resources: tuple[str, ...]    # 指定资源（严格来自计划的 5 类资源，防发散）
    est_minutes: int              # 预计投入分钟数（计划 §九：约 6 小时/天）
    track_key: str                # 归属赛道：llm / vlm


PHASES: Final[dict[int, str]] = {
    1: "第一周 · 打穿 Transformer",
    2: "第二周 · Training / Fine-tuning / Inference",
    3: "第三周 · 只学 VLM 结构",
    4: "第四周 · 变成求职资产",
}

# 计划 §二指定的 5 类资源（唯一允许的来源，替代"课程收藏"）
RESOURCE_LOCK: Final[tuple[str, ...]] = (
    "Hugging Face LLM Course",
    "Attention Is All You Need (arXiv 1706.03762)",
    "LoRA (arXiv 2106.09685) + Hugging Face PEFT",
    "vLLM Documentation",
    "Hugging Face Multimodal / LLaVA",
)

# 计划 §十二的 D 级技术黑名单（30 天内不投入）
# 与 app/core/target_roles.py 的 TECH_BLACKLIST 同源，此处保留轻量副本用于种子校验。
D_LEVEL_FORBIDDEN: Final[tuple[str, ...]] = (
    "MoE", "RLHF", "CUDA Kernel", "Megatron", "FlashAttention",
    "VLA", "World Model", "Isaac", "ROS2", "Robot Learning", "Agent Framework",
)


PLAN_30D: list[PlanDaySeed] = [
    # ══════════════════ 第一周：把 Transformer 真正打穿 ══════════════════
    PlanDaySeed(
        seq=1,
        phase=1,
        phase_name=PHASES[1],
        title="Transformer 总体结构",
        theme="Transformer",
        objectives=(
            "走通数据流：Token → Embedding → Position → Attention → FFN → Residual → Norm → LM Head → Cross Entropy",
            "阅读 HF LLM Course 对应章节 + Attention Is All You Need 原文",
        ),
        acceptance=(
            "产出 docs/01_transformer.md",
            "自己手画一张 Transformer 架构图（不许截图）",
            "能讲清 Encoder-only / Decoder-only / Enc-Dec 的取舍",
        ),
        interview_topics=(
            "Transformer 为什么会出现？",
            "Self-Attention 是什么？",
            "为什么 Transformer 可以并行计算？",
            "Decoder-only 为什么适合 LLM？",
        ),
        resources=(
            "Hugging Face LLM Course",
            "Attention Is All You Need (arXiv 1706.03762)",
        ),
        est_minutes=360,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=2,
        phase=1,
        phase_name=PHASES[1],
        title="Attention 手写实现",
        theme="Transformer",
        objectives=(
            "自己推导 Q = XWq / K = XWk / V = XWv",
            "推导 Attention(Q,K,V) = softmax(QKᵀ / √d) V",
            "搞懂 Shape 变换：[B,T,D] → [B,H,T,Dh]",
        ),
        acceptance=(
            "产出 01_transformer/attention.py",
            "自己实现 MultiHeadAttention(nn.Module)",
            "闭卷解释：为什么需要除以 √d",
        ),
        interview_topics=(
            "为什么要除以 √d？",
            "Multi-head 相比单头强在哪里？",
            "Causal Mask 怎么实现？",
            "Attention 的时间复杂度是多少？",
        ),
        resources=("Attention Is All You Need (arXiv 1706.03762)",),
        est_minutes=360,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=3,
        phase=1,
        phase_name=PHASES[1],
        title="RoPE 旋转位置编码",
        theme="Transformer",
        objectives=(
            "不停留在「RoPE 是位置编码」，理解 Q/K 经旋转后携带相对位置信息",
            "区分 absolute position / relative position / RoPE",
            "理解 RoPE 与 context length 的关系",
        ),
        acceptance=(
            "产出 01_transformer/rope.py",
            "能推导旋转矩阵形式",
            "闭卷解释 RoPE 为什么能外推",
        ),
        interview_topics=(
            "RoPE 和绝对位置编码的区别？",
            "RoPE 为什么能表达相对位置？",
            "长上下文扩展（NTK / YaRN）在改什么？",
            "位置编码可以不加吗？",
        ),
        resources=("Hugging Face LLM Course",),
        est_minutes=330,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=4,
        phase=1,
        phase_name=PHASES[1],
        title="RMSNorm + SwiGLU",
        theme="Transformer",
        objectives=(
            "实现 RMSNorm 与 SwiGLU",
            "对比 LayerNorm / RMSNorm 的计算差异",
            "理解为什么现代 LLM 常用 RMSNorm + SwiGLU",
        ),
        acceptance=(
            "产出 01_transformer/rmsnorm.py 与 swiglu.py",
            "说明 Pre-Norm 与 Post-Norm 的训练稳定性差异",
        ),
        interview_topics=(
            "RMSNorm 比 LayerNorm 省了什么？",
            "SwiGLU 相比 ReLU FFN 为什么效果更好？",
            "Pre-Norm 和 Post-Norm 的区别？",
            "残差连接解决什么问题？",
        ),
        resources=("Hugging Face LLM Course",),
        est_minutes=300,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=5,
        phase=1,
        phase_name=PHASES[1],
        title="Loss 与反向传播全链路",
        theme="Transformer",
        objectives=(
            "跑通 Token → Logits → Cross Entropy → Backward → Gradient → AdamW → Weight Update",
            "理解 Cross Entropy 在 language modeling 里的位置",
        ),
        acceptance=(
            "自己写一个最小训练 loop（不调 Trainer）",
            "能讲清 AdamW 相对 Adam 的改动",
            "loss 能稳定下降",
        ),
        interview_topics=(
            "Cross Entropy 的公式和在 LM 里的含义？",
            "AdamW 和 Adam 的区别？",
            "学习率 warmup 为什么有用？",
            "梯度裁剪解决什么问题？",
        ),
        resources=("Hugging Face LLM Course",),
        est_minutes=360,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=6,
        phase=1,
        phase_name=PHASES[1],
        title="拼装 Mini Transformer",
        theme="Transformer",
        objectives=(
            "把 Embedding + RoPE + Attention + RMSNorm + SwiGLU + LM Head 合并成一个可训练模型",
            "参数小没关系，重点是跑得起来",
        ),
        acceptance=(
            "产出 01_transformer/model.py",
            "自己写的模型 loss 真的下降",
            "能讲清每一层的 tensor shape",
        ),
        interview_topics=(
            "一个 Decoder block 里有哪些子层？",
            "参数量怎么估算？",
            "为什么需要 weight tying？",
            "dropout 一般加在哪里？",
        ),
        resources=("Hugging Face LLM Course",),
        est_minutes=390,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=7,
        phase=1,
        phase_name=PHASES[1],
        title="第一次面试验收（闭卷 20 题）",
        theme="验收",
        objectives=(
            "闭卷回答 20 题，覆盖 Attention / Multi-head / Causal Mask / RoPE / RMSNorm / SwiGLU / Cross Entropy / AdamW / Residual / Pre-Norm",
        ),
        acceptance=(
            "20 题中答不出的立即补课，不继续往后学",
            "把答不出的题录入题库并标记待验证",
            "本周 7 天四件套全部齐全",
        ),
        interview_topics=(
            "上述 10 个主题各 2 题",
        ),
        resources=("Hugging Face LLM Course",),
        est_minutes=300,
        track_key="llm",
    ),

    # ══════════ 第二周：Training + Fine-tuning + Inference（核心周）══════════
    PlanDaySeed(
        seq=8,
        phase=2,
        phase_name=PHASES[2],
        title="LLM Pretraining 全景",
        theme="Training",
        objectives=(
            "理解 数据 → Tokenizer → Next Token Prediction → CE → Backprop → 参数更新",
            "搞清四大约束：Data / Compute / Memory / Communication",
        ),
        acceptance=(
            "产出 docs/02_pretraining.md",
            "能讲清 pretraining 与 SFT 的目标差异",
        ),
        interview_topics=(
            "预训练目标是什么？",
            "数据配比为什么重要？",
            "数据去重怎么做？",
            "训练不收敛怎么排查？",
        ),
        resources=("Hugging Face LLM Course",),
        est_minutes=300,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=9,
        phase=2,
        phase_name=PHASES[2],
        title="显存计算（重要）",
        theme="Training",
        objectives=(
            "拆解显存构成：Model Parameters + Gradients + Optimizer States + Activations + KV Cache",
            "回答：7B 模型 BF16 为什么不是简单的 14GB",
        ),
        acceptance=(
            "产出 docs/memory_calculation.md",
            "能手算 7B / 13B 模型在各精度下的训练显存",
            "面试题：显存不够有哪些解法（能说 4 种以上）",
        ),
        interview_topics=(
            "全参数训练显存怎么估算？",
            "AdamW 的优化器状态占多少？",
            "梯度累积怎么省显存？",
            "ZeRO 的三个 stage 各切什么？",
            "为什么 7B BF16 不是 14GB？",
        ),
        resources=("Hugging Face LLM Course",),
        est_minutes=360,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=10,
        phase=2,
        phase_name=PHASES[2],
        title="第一次真实 SFT",
        theme="Fine-tuning",
        objectives=(
            "跑通 Base Model → Instruction Dataset → SFT → Chat Model",
            "搞清 Prompt / Response / Labels / Loss Mask / Chat Template",
        ),
        acceptance=(
            "产出 03_sft/train_sft.py 并真实跑通",
            "能解释 Loss Mask 为什么只算 response 部分",
            "记录训练前后的对话效果对比",
        ),
        interview_topics=(
            "SFT 的 loss 只算哪部分？",
            "Chat Template 是什么，为什么必须对齐？",
            "SFT 数据量一般多少？",
            "过拟合怎么判断？",
        ),
        resources=("Hugging Face LLM Course",),
        est_minutes=390,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=11,
        phase=2,
        phase_name=PHASES[2],
        title="LoRA（关键日）",
        theme="PEFT",
        objectives=(
            "读 LoRA 原论文，理解 W' = W + BA，其中 W 冻结、A/B 可训练",
            "理解低秩假设与秩 r 的选择",
        ),
        acceptance=(
            "产出 04_lora/train_lora.py 并用 HF PEFT 真实跑一次",
            "能手算 LoRA 的可训练参数量",
            "说明 target_modules 怎么选",
        ),
        interview_topics=(
            "LoRA 为什么有效？",
            "秩 r 怎么选？",
            "alpha 的作用是什么？",
            "target_modules 一般选哪些层？",
            "LoRA 和 Adapter 的区别？",
        ),
        resources=("LoRA (arXiv 2106.09685) + Hugging Face PEFT",),
        est_minutes=360,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=12,
        phase=2,
        phase_name=PHASES[2],
        title="QLoRA 与对比实验",
        theme="PEFT",
        objectives=(
            "理解 Quantization + LoRA 的组合",
            "回答：QLoRA 到底解决了什么问题",
        ),
        acceptance=(
            "真实测 LoRA vs QLoRA 两组",
            "记录 GPU Memory / Training Time / Trainable Parameters / Performance 四项",
            "产出 Experiment 记录（P2 落表，本周先存 docs）",
        ),
        interview_topics=(
            "QLoRA 的核心创新是什么？",
            "NF4 量化为什么适合正态分布的权重？",
            "Double Quantization 省了什么？",
            "Paged Optimizer 解决什么问题？",
            "QLoRA 有什么代价？",
        ),
        resources=("LoRA (arXiv 2106.09685) + Hugging Face PEFT",),
        est_minutes=390,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=13,
        phase=2,
        phase_name=PHASES[2],
        title="KV Cache",
        theme="Inference",
        objectives=(
            "理解 Prefill → KV Cache → Decode 两阶段",
            "回答：生成第 100 个 token 时为什么不需要重算前 99 个 token 的 K/V",
        ),
        acceptance=(
            "产出 05_inference/kv_cache.py",
            "手算 KV Cache 显存占用公式",
            "能讲清 MHA / MQA / GQA 的差异",
        ),
        interview_topics=(
            "KV Cache 存的是什么？",
            "KV Cache 显存怎么算？",
            "MQA / GQA 为什么能省显存？",
            "PagedAttention 解决什么问题？",
            "Prefill 和 Decode 的瓶颈各是什么？",
        ),
        resources=("vLLM Documentation",),
        est_minutes=330,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=14,
        phase=2,
        phase_name=PHASES[2],
        title="vLLM 部署与 Benchmark",
        theme="Inference",
        objectives=(
            "部署 Model → vLLM → OpenAI Compatible API",
            "设计并发实验：1 / 4 / 8 requests",
        ),
        acceptance=(
            "产出 05_inference/benchmark.py",
            "记录 TTFT / Tokens per s / Throughput / GPU Memory",
            "★ 里程碑：本周结束即可开始投 LLM Algorithm",
        ),
        interview_topics=(
            "vLLM 为什么比普通 Transformers 推理快？",
            "Continuous Batching 是什么？",
            "TTFT 和 TPOT 分别衡量什么？",
            "量化推理有哪些方案？",
            "吞吐和延迟如何权衡？",
        ),
        resources=("vLLM Documentation",),
        est_minutes=390,
        track_key="llm",
    ),

    # ══════════════ 第三周：只学 VLM 结构（占 20-25% 时间）══════════════
    PlanDaySeed(
        seq=15,
        phase=3,
        phase_name=PHASES[3],
        title="ViT",
        theme="Vision",
        objectives=(
            "理解 Image → Patch → Patch Embedding → Transformer → Visual Tokens",
            "回答：图像为什么也可以变成 token",
        ),
        acceptance=(
            "产出 docs/06_vit.md",
            "能讲清 patch size 对序列长度的影响",
        ),
        interview_topics=(
            "ViT 是什么？",
            "Patch Embedding 怎么做？",
            "position embedding 在 ViT 里怎么加？",
            "cls token 有什么用？",
        ),
        resources=("Hugging Face Multimodal / LLaVA",),
        est_minutes=270,
        track_key="vlm",
    ),
    PlanDaySeed(
        seq=16,
        phase=3,
        phase_name=PHASES[3],
        title="CLIP 与对比学习",
        theme="Vision",
        objectives=(
            "理解 Image Encoder + Text Encoder + Contrastive Learning 双塔结构",
            "只搞懂 InfoNCE / contrastive objective，不深钻 CV",
        ),
        acceptance=(
            "产出 docs/07_clip.md",
            "能解释 CLIP 为什么能做 zero-shot 分类",
        ),
        interview_topics=(
            "CLIP 是什么？",
            "InfoNCE 损失怎么构造？",
            "温度系数 τ 的作用？",
            "CLIP 的局限是什么？",
        ),
        resources=("Hugging Face Multimodal / LLaVA",),
        est_minutes=240,
        track_key="vlm",
    ),
    PlanDaySeed(
        seq=17,
        phase=3,
        phase_name=PHASES[3],
        title="VLM 架构（本周最重要）",
        theme="VLM",
        objectives=(
            "走通 Image → Vision Encoder → Projector → LLM → Text",
            "理解为什么 Frozen Vision Encoder + Frozen LLM + Train Projector",
            "理解两阶段：feature alignment → visual instruction tuning",
        ),
        acceptance=(
            "产出 docs/08_vlm_arch.md 含架构图",
            "说明 LLaVA 的 projector 为什么用两层 MLP",
            "能解释对齐阶段和指令微调阶段各自在训什么",
        ),
        interview_topics=(
            "Vision Encoder 干什么？",
            "Projector 干什么？",
            "为什么不能直接把视觉 feature 扔进 LLM？",
            "VLM 为什么需要 Alignment？",
            "LLaVA 的两阶段训练各做什么？",
        ),
        resources=("Hugging Face Multimodal / LLaVA",),
        est_minutes=300,
        track_key="vlm",
    ),
    PlanDaySeed(
        seq=18,
        phase=3,
        phase_name=PHASES[3],
        title="Multimodal Token",
        theme="VLM",
        objectives=(
            "理解 Image → Pixels → Patch → Visual Tokens → Projector → LLM Token Space",
            "回答：视觉 token 最终为什么能和 text token 一起进入 LLM",
        ),
        acceptance=(
            "产出 docs/09_multimodal_token.md",
            "能算一张图会产生多少个 visual token",
            "说明 visual token 数量对推理成本的影响",
        ),
        interview_topics=(
            "Visual Token 是什么？",
            "一张图占多少 token？",
            "怎么压缩 visual token 数量？",
            "resampler / Q-Former 是干什么的？",
        ),
        resources=("Hugging Face Multimodal / LLaVA",),
        est_minutes=240,
        track_key="vlm",
    ),
    PlanDaySeed(
        seq=19,
        phase=3,
        phase_name=PHASES[3],
        title="VLM 推理跑通",
        theme="VLM",
        objectives=(
            "直接使用一个成熟的 HF multimodal model",
            "跑通 Image + Question → VLM → Answer，不研究训练",
        ),
        acceptance=(
            "产出 06_vlm/inference.py",
            "成功对一张真实图片提问并得到答案",
            "记录显存占用与推理延迟",
        ),
        interview_topics=(
            "多模态输入怎么用 Processor 处理？",
            "chat template 在多模态里怎么用？",
            "VLM 推理显存主要花在哪？",
            "怎么评估一个 VLM 的能力？",
        ),
        resources=("Hugging Face Multimodal / LLaVA",),
        est_minutes=240,
        track_key="vlm",
    ),
    PlanDaySeed(
        seq=20,
        phase=3,
        phase_name=PHASES[3],
        title="VLM LoRA 微调",
        theme="VLM",
        objectives=(
            "做一次 VLM + LoRA + Small Dataset 的微调",
            "不追求 SOTA，目标只有一个：确实训练过一个 VLM",
        ),
        acceptance=(
            "产出 06_vlm/finetune.py 并真实跑通",
            "记录微调前后对比（before / after）",
            "说明 LoRA 加在 VLM 的哪些模块上",
        ),
        interview_topics=(
            "VLM 微调一般冻什么、训什么？",
            "LoRA 加在 VLM 哪一层更有效？",
            "VLM 微调的数据格式是什么样？",
            "微调后为什么会灾难性遗忘？",
        ),
        resources=("Hugging Face Multimodal / LLaVA",),
        est_minutes=300,
        track_key="vlm",
    ),
    PlanDaySeed(
        seq=21,
        phase=3,
        phase_name=PHASES[3],
        title="VLM 面试验收",
        theme="验收",
        objectives=(
            "把 9 个核心问题答到每个 1-2 分钟",
        ),
        acceptance=(
            "9 题全部能答，答不出的补课",
            "本周四件套齐全（VLM 部分可少于 5 题，但不得为 0）",
        ),
        interview_topics=(
            "ViT 是什么？",
            "Patch Embedding 是什么？",
            "CLIP 是什么？",
            "InfoNCE 是什么？",
            "Vision Encoder 干什么？",
            "Projector 干什么？",
            "为什么不能直接把视觉 feature 扔进 LLM？",
            "Visual Token 是什么？",
            "VLM 为什么需要 Alignment？",
        ),
        resources=("Hugging Face Multimodal / LLaVA",),
        est_minutes=210,
        track_key="vlm",
    ),

    # ══════════════ 第四周：把东西变成求职资产 ══════════════
    PlanDaySeed(
        seq=22,
        phase=4,
        phase_name=PHASES[4],
        title="建立统一实验",
        theme="实验",
        objectives=(
            "Experiment A（LLM）：Base → SFT → LoRA → QLoRA 四组对比",
            "Experiment B（VLM）：Base VLM → LoRA → Small Dataset 前后对比",
        ),
        acceptance=(
            "Experiment A 表填完：方法 / Trainable Params / GPU Memory / Time / Result",
            "Experiment B 记录 before / after",
            "★ 项目叙事升级为「研究 PEFT 对 LLM/VLM 训练成本与效果的影响」",
        ),
        interview_topics=(
            "LoRA 相比全参微调省了多少显存？",
            "QLoRA 和 LoRA 的区别？",
            "PEFT 会损失多少效果？",
            "怎么设计一个公平的微调对比实验？",
        ),
        resources=(
            "LoRA (arXiv 2106.09685) + Hugging Face PEFT",
            "Hugging Face Multimodal / LLaVA",
        ),
        est_minutes=390,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=23,
        phase=4,
        phase_name=PHASES[4],
        title="Inference Benchmark",
        theme="实验",
        objectives=(
            "形成 Transformers vs vLLM 的正式对比",
            "对比 TTFT / Throughput / Latency / Memory 四维指标",
        ),
        acceptance=(
            "产出对比表与结论",
            "说明 vLLM 的加速来自哪里（能定位到具体机制）",
        ),
        interview_topics=(
            "vLLM 的加速来源拆解？",
            "什么场景下 vLLM 优势最大？",
            "batch size 对吞吐和延迟的影响？",
            "线上部署怎么选推理框架？",
        ),
        resources=("vLLM Documentation",),
        est_minutes=360,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=24,
        phase=4,
        phase_name=PHASES[4],
        title="README 写成论文",
        theme="包装",
        objectives=(
            "README 结构：Motivation / Architecture / Environment / Dataset / Training / LoRA & QLoRA / VLM / Evaluation / Inference Benchmark / Results / Failure Cases / Lessons Learned / Future Work",
        ),
        acceptance=(
            "README 必须像论文而不是课程作业",
            "Failure Cases 与 Lessons Learned 两节不得空着",
        ),
        interview_topics=(
            "用 3 分钟讲清这个项目？",
            "项目里最难的坑是什么？",
            "如果重做会改什么？",
        ),
        resources=("Hugging Face LLM Course",),
        est_minutes=240,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=25,
        phase=4,
        phase_name=PHASES[4],
        title="简历反向校准",
        theme="包装",
        objectives=(
            "简历主线：硕士研究（小样本时序预测 → EI 论文）→ 模型能力（Transformer → LLM Fine-tuning → VLM → Inference）",
            "STM-SHAP 不弱化，突出 EI indexed publication",
        ),
        acceptance=(
            "简历技能行每一项都能点开对应证据（代码 / 实验 / 论文）",
            "身份定位写成「已有科研成果 + 正在转型 Foundation Model」，不是「零基础转行」",
            "英文作者名统一为 Xiangyu Zhang",
        ),
        interview_topics=(
            "你的硕士研究做了什么？",
            "论文的核心贡献是什么？",
            "为什么从洪水预测转向多模态？",
        ),
        resources=("Hugging Face LLM Course",),
        est_minutes=240,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=26,
        phase=4,
        phase_name=PHASES[4],
        title="LLM 题库收口（≥50 题）",
        theme="面试",
        objectives=(
            "把前 25 天累积的题目按 Transformer / Training / SFT / PEFT / Quantization / Inference / Distributed Training / Serving 八类归档",
            "查缺补漏到达 50 题",
        ),
        acceptance=(
            "题库 LLM 类 ≥50 题，八分类无空档",
            "标注仍答不出来的题，明天补",
        ),
        interview_topics=(
            "八分类各抽查 2 题",
        ),
        resources=("Hugging Face LLM Course",),
        est_minutes=300,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=27,
        phase=4,
        phase_name=PHASES[4],
        title="VLM 题库收口（25-30 题）",
        theme="面试",
        objectives=(
            "按 ViT / CLIP / Vision Encoder / Projector / Multimodal Alignment / Visual Token / VLM Fine-tuning / Multimodal Evaluation 八类归档",
        ),
        acceptance=(
            "题库 Multimodal 类 ≥25 题",
            "与 LLM 类合并累计达到核心必达 80 题",
        ),
        interview_topics=(
            "八分类各抽查 2 题",
        ),
        resources=("Hugging Face Multimodal / LLaVA",),
        est_minutes=270,
        track_key="vlm",
    ),
    PlanDaySeed(
        seq=28,
        phase=4,
        phase_name=PHASES[4],
        title="项目模拟面试",
        theme="面试",
        objectives=(
            "按真实技术面流程自问自答，覆盖 LoRA / QLoRA / 显存 / KV Cache / vLLM / 视觉 token / Projector / 转方向动机",
        ),
        acceptance=(
            "★「你为什么从洪水预测转到多模态」必须答得非常好",
            "转方向叙事四段式：小样本时序 → Transformer → Foundation Model → Multimodal Foundation Model",
            "全程录音或写逐字稿，找出卡壳处",
        ),
        interview_topics=(
            "为什么选择 LoRA？",
            "QLoRA 和 LoRA 有什么区别？",
            "为什么你的显存只有这么多？",
            "KV Cache 怎么工作？",
            "vLLM 为什么比普通 Transformers inference 快？",
            "VLM 的视觉 token 从哪里来？",
            "Projector 的作用是什么？",
            "你为什么从洪水预测转到多模态？",
        ),
        resources=("Hugging Face LLM Course",),
        est_minutes=240,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=29,
        phase=4,
        phase_name=PHASES[4],
        title="海投启动",
        theme="求职",
        objectives=(
            "第一目标：LLM Algorithm Engineer",
            "第二目标：Foundation Model / Multimodal / VLM Engineer",
            "第三目标：AI Algorithm / NLP / CV / Generative AI / Inference",
        ),
        acceptance=(
            "投递记录进入看板，至少完成首批投递",
            "每个岗位记录匹配度与缺口，便于复盘",
        ),
        interview_topics=(
            "针对目标 JD 的定制化自我介绍",
        ),
        resources=("Hugging Face LLM Course",),
        est_minutes=210,
        track_key="llm",
    ),
    PlanDaySeed(
        seq=30,
        phase=4,
        phase_name=PHASES[4],
        title="最终验收",
        theme="验收",
        objectives=(
            "从 Input → Token → Transformer → Training → SFT → LoRA → QLoRA → KV Cache → vLLM 讲到 Image → ViT → Visual Tokens → Projector → LLM → VLM",
            "再自然接到 Time Series + Vision + Language → Multimodal Foundation Model",
        ),
        acceptance=(
            "技术故事完整、连贯，能一口气讲 10 分钟",
            "30 commits / 30 技术笔记 / 150 题三项总账核对",
            "明确下一步：12 月硕士毕业，2027 年把工作与 Multimodal 科研结合",
        ),
        interview_topics=(
            "完整技术线串讲",
            "未来三年规划",
        ),
        resources=("Hugging Face LLM Course",),
        est_minutes=180,
        track_key="llm",
    ),
]


def get_day(seq: int) -> PlanDaySeed | None:
    """按序号取课程日。越界返回 None。"""

    for day in PLAN_30D:
        if day.seq == seq:
            return day
    return None


assert len(PLAN_30D) == 30, f"课程脊梁必须是 30 天，当前 {len(PLAN_30D)}"
assert [d.seq for d in PLAN_30D] == list(range(1, 31)), "seq 必须连续 1..30"
