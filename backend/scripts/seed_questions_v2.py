"""题库补充脚本 v2：110 → 150 题。

填补 Multimodal / Project / Coding 缺口，覆盖 MoE / DPO / RAG / Agent 等热门技能。
幂等：按 question 文本去重，已存在的跳过。

用法：
    cd backend
    python scripts/seed_questions_v2.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.base import SessionLocal, init_db
from app.models.interview_question import InterviewQuestion

QUESTIONS: list[dict] = [
    # ═══════════════════════ Multimodal（10 题）═══════════════════════
    {
        "category": "Multimodal",
        "question": "CLIP 的核心思路是什么？对比学习的 loss 怎么设计？",
        "difficulty": "intermediate",
        "skill_name": "CLIP",
        "answer_outline": "1) 双塔架构：图像编码器（ViT/ResNet）+ 文本编码器（Transformer），各自映射到共享嵌入空间。2) 对比损失：batch 内图文对为正样本，其余为负样本，InfoNCE loss 最大化正样本相似度。3) 对称 loss：image-to-text + text-to-image 两个方向求和。4) zero-shot 能力：无需微调，通过文本 prompt 分类。",
        "source": "seed_v2",
    },
    {
        "category": "Multimodal",
        "question": "BLIP-2 相比 BLIP 做了哪些改进？Q-Former 的作用是什么？",
        "difficulty": "advanced",
        "skill_name": "BLIP",
        "answer_outline": "1) 两阶段预训练：先冻结视觉/文本编码器训练 Q-Former，再解冻做端到端微调。2) Q-Former：轻量级 Transformer，用可学习的 query token 从冻结的图像特征中提取与语言相关的表示。3) 三个预训练任务：图文对比（ITC）、图文匹配（ITM）、图文生成（ITG）。4) 效率提升：避免大规模视觉-语言联合预训练，计算成本降低 10x+。",
        "source": "seed_v2",
    },
    {
        "category": "Multimodal",
        "question": "LLaVA 如何实现视觉指令微调？两阶段训练分别做什么？",
        "difficulty": "intermediate",
        "skill_name": "LLaVA",
        "answer_outline": "1) 第一阶段（特征对齐）：冻结视觉编码器和 LLM，只训练线性投影层，用 CC3M 图文对对齐视觉-语言空间。2) 第二阶段（指令微调）：解冻 LLM，用 GPT-4 生成的视觉指令数据微调，提升指令遵循能力。3) 视觉 token：CLIP 编码图像 → 线性层投影到 LLM embedding 空间，与文本 token 拼接输入。4) 简单高效：仅 1 个线性层做对齐，无需复杂交叉注意力。",
        "source": "seed_v2",
    },
    {
        "category": "Multimodal",
        "question": "视觉编码器 ViT 和 SigLIP 有什么区别？各自优势是什么？",
        "difficulty": "intermediate",
        "skill_name": "视觉编码器",
        "answer_outline": "1) ViT：图像切 patch → 线性嵌入 + 位置编码 → Transformer Encoder，CLS token 做分类。2) SigLIP：用 sigmoid loss 替代 softmax loss，不需要全局 batch 归一化，支持更大 batch size。3) SigLIP 优势：训练更稳定，zero-shot 性能更好，已被 PaLI-3、Idefics2 等采用。4) 选择依据：小模型用 ViT 足够，大模型或需要 zero-shot 用 SigLIP。",
        "source": "seed_v2",
    },
    {
        "category": "Multimodal",
        "question": "多模态模型中视觉 token 和文本 token 如何对齐？有哪些主流方案？",
        "difficulty": "advanced",
        "skill_name": "多模态对齐",
        "answer_outline": "1) 线性投影：LLaVA 方案，简单但信息损失大。2) Q-Former：BLIP-2 方案，可学习 query 提取相关特征。3) 交叉注意力：Flamingo 方案，视觉特征注入 LLM 每一层。4) Perceiver Resampler：将可变数量的视觉 token 压缩为固定数量。5) 对比学习预训练：CLIP 风格先对齐空间，再做生成微调。",
        "source": "seed_v2",
    },
    {
        "category": "Multimodal",
        "question": "图文检索任务中，双塔模型和交叉注意力模型各有什么优劣？",
        "difficulty": "intermediate",
        "skill_name": "图文检索",
        "answer_outline": "1) 双塔：图文各自编码，余弦相似度匹配。优势：检索速度快（可预计算图像嵌入），适合大规模检索。劣势：交互信息少，精度较低。2) 交叉注意力：图文 token 交叉注意力，精细交互。优势：精度高，适合 rerank。劣势：每对都要计算，速度慢。3) 实践：双塔粗筛 + 交叉注意力精排。",
        "source": "seed_v2",
    },
    {
        "category": "Multimodal",
        "question": "视频理解模型如何处理时序信息？与图像理解有什么本质区别？",
        "difficulty": "advanced",
        "skill_name": "视频理解",
        "answer_outline": "1) 时序建模：均匀采帧 → 每帧独立编码 → 时序聚合（平均池化/Transformer/因果注意力）。2) 与图像区别：视频有时序因果关系、运动信息、长程依赖。3) 代表模型：VideoCLIP（对比学习）、VideoChat（指令微调）、Video-LLaVA（多帧输入 LLM）。4) 挑战：帧数多 → token 爆炸，需要 token 压缩或稀疏采样。",
        "source": "seed_v2",
    },
    {
        "category": "Multimodal",
        "question": "OCR 和文档理解有哪些主流方案？LayoutLM 系列的核心思路是什么？",
        "difficulty": "intermediate",
        "skill_name": "OCR",
        "answer_outline": "1) 传统 OCR：检测（CRAFT/DBNet）+ 识别（CRNN/SVTR）两阶段。2) 端到端：PaddleOCR、GOT-OCR 等直接输出文本。3) LayoutLM：将文档布局（bounding box）编码为位置嵌入，与文本 embedding 拼接输入 Transformer。4) LayoutLMv3：加入图像特征，多模态文档理解。5) 应用：发票、合同、表格结构化提取。",
        "source": "seed_v2",
    },
    {
        "category": "Multimodal",
        "question": "多模态 Agent 的架构设计？如何让 LLM 调用视觉工具？",
        "difficulty": "advanced",
        "skill_name": "多模态 Agent",
        "answer_outline": "1) 架构：LLM 为大脑，视觉模型为眼睛，工具为手。LLM 理解指令 → 规划步骤 → 调用视觉工具 → 整合结果。2) 视觉工具：目标检测、OCR、图像分割、视觉问答等。3) 代表：CogAgent（GUI Agent）、KOSMOS-2（grounding）、GPT-4V（通用多模态）。4) 关键挑战：视觉 grounding（把语言描述映射到图像区域）、工具选择、错误恢复。",
        "source": "seed_v2",
    },
    {
        "category": "Multimodal",
        "question": "Flamingo 的少样本多模态能力是怎么实现的？",
        "difficulty": "advanced",
        "skill_name": "Flamingo",
        "answer_outline": "1) Perceiver Resampler：将可变数量的视觉 token 压缩为固定 64 个 token。2) Gated Cross-Attention：在 LLM 每隔几层插入交叉注意力层，视觉特征注入语言模型。3) 门控机制：可学习的 alpha 参数，初始为 0，训练稳定。4) 少样本能力：in-context learning，给几个图文示例即可处理新任务，无需微调。",
        "source": "seed_v2",
    },
    # ═══════════════════════ Project（21 题）═══════════════════════
    {
        "category": "Project",
        "question": "RAG 系统的整体架构设计？检索、增强、生成三阶段各做什么？",
        "difficulty": "intermediate",
        "skill_name": "RAG",
        "answer_outline": "1) 检索：用户 query → 向量化 → 在文档库中检索 top-k 相关片段。2) 增强：将检索结果与 query 拼接，构造增强 prompt。3) 生成：LLM 基于增强 prompt 生成回答，引用来源。4) 关键组件：文档加载 → 分块 → 嵌入 → 向量数据库 → 检索 → 重排 → 生成。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "RAG 中有哪些检索策略？向量检索、混合检索、重排各自解决什么问题？",
        "difficulty": "advanced",
        "skill_name": "RAG",
        "answer_outline": "1) 向量检索：embedding 余弦相似度，语义匹配好但关键词匹配差。2) BM25/关键词检索：精确匹配好但语义理解差。3) 混合检索：向量 + BM25 分数融合（RRF/加权），兼顾语义和精确匹配。4) 重排（Rerank）：用交叉注意力模型（如 Cohere Rerank、BGE Reranker）对粗筛结果精排，提升 top-k 精度。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "RAG 系统有哪些评估指标？如何衡量检索质量和生成质量？",
        "difficulty": "intermediate",
        "skill_name": "RAG",
        "answer_outline": "1) 检索指标：Recall@K（top-k 是否包含正确文档）、MRR（正确文档排名）、NDCG（排序质量）。2) 生成指标：faithfulness（回答是否忠于检索内容）、relevance（回答是否切题）、answer correctness。3) 端到端指标：RAGAS 框架（Context Recall/Precision + Faithfulness + Answer Relevance）。4) 人工评估：标注 golden answer 对比。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "Agent 架构中 ReAct 和 Plan-and-Execute 有什么区别？各自适用场景？",
        "difficulty": "intermediate",
        "skill_name": "Agent",
        "answer_outline": "1) ReAct：交替执行 Thought → Action → Observation，逐步推理和行动。优势：灵活、可纠错。劣势：可能循环、长任务效率低。2) Plan-and-Execute：先生成完整计划，再逐步执行。优势：全局规划、长任务高效。劣势：计划可能不准、纠错成本高。3) 适用：简单任务用 ReAct，复杂多步骤任务用 Plan-and-Execute。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "Agent 的工具调用（Function Calling）机制是怎么实现的？",
        "difficulty": "intermediate",
        "skill_name": "Agent",
        "answer_outline": "1) 工具定义：JSON Schema 描述函数名、参数、返回值，注入 system prompt。2) LLM 决策：根据用户意图选择工具和参数，输出结构化 JSON。3) 执行层：解析 LLM 输出 → 调用实际函数 → 返回结果。4) 错误处理：参数校验、超时、异常捕获，结果回传 LLM 重试。5) 多工具：parallel function calling、tool routing。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "Prompt Engineering 有哪些核心技巧？如何设计高质量 prompt？",
        "difficulty": "beginner",
        "skill_name": "Prompt Engineering",
        "answer_outline": "1) 角色设定：明确 LLM 扮演的角色和能力边界。2) Few-shot 示例：给 2-3 个输入输出示例，对齐格式和风格。3) 链式思考（CoT）：引导 LLM 逐步推理。4) 结构化输出：指定 JSON/XML 格式。5) 约束条件：明确不要做什么（negative prompting）。6) 迭代优化：A/B 测试不同 prompt 版本。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "Prompt 注入有哪些类型？如何防御？",
        "difficulty": "intermediate",
        "skill_name": "Prompt Engineering",
        "answer_outline": "1) 直接注入：用户输入中嵌入指令覆盖 system prompt。2) 间接注入：通过外部数据源（网页/文档）注入恶意指令。3) 防御：输入过滤（检测注入模式）、prompt 隔离（system/user 分层）、输出校验（检测越权行为）、sandwich defense（前后夹击 user 内容）。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "LLM 评估体系怎么设计？自动评估、人工评估、LLM-as-Judge 各自优劣？",
        "difficulty": "advanced",
        "skill_name": "评估体系",
        "answer_outline": "1) 自动评估：BLEU/ROUGE（文本相似度）、准确率/F1（分类）、pass@k（代码）。优势：快、可复现。劣势：与人类判断相关性有限。2) 人工评估：众包标注、专家评审。优势：最准确。劣势：慢、贵、主观。3) LLM-as-Judge：GPT-4 打分。优势：快且相对准确。劣势：position bias、自我偏好。4) 实践：自动评估为主 + LLM-as-Judge 辅助 + 关键任务人工抽检。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "模型部署用 vLLM 还是 TGI？各自的优劣和适用场景？",
        "difficulty": "advanced",
        "skill_name": "部署优化",
        "answer_outline": "1) vLLM：PagedAttention 技术，显存利用率高，吞吐量大。支持 OpenAI 兼容 API。社区活跃。2) TGI：HuggingFace 出品，与 Transformers 生态集成好，支持多种量化格式（GPTQ/AWQ/GGUF）。3) 选择：高吞吐在线服务用 vLLM，HuggingFace 生态用 TGI，边缘部署用 llama.cpp。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "数据清洗和标注流程怎么设计？如何保证数据质量？",
        "difficulty": "intermediate",
        "skill_name": "数据工程",
        "answer_outline": "1) 清洗管道：去重（MinHash/SimHash）→ 过滤（质量/毒性/语言）→ 规范化（格式/编码）。2) 标注流程：标注指南 → 试标 → 正式标注 → 质检（交叉验证/一致性检查）。3) 质量保证：标注者间一致率（Cohen's Kappa ≥ 0.7）、golden set 校验、自动异常检测。4) 工具：Label Studio、Prodigy、Argilla。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "数据飞轮是什么？主动学习如何减少标注成本？",
        "difficulty": "advanced",
        "skill_name": "数据工程",
        "answer_outline": "1) 数据飞轮：模型上线 → 用户反馈 → 有价值数据回流 → 模型迭代提升 → 更多用户。正循环。2) 主动学习：模型对未标注数据预测置信度，选择最不确定的样本优先标注。3) 策略：不确定性采样（entropy/least confidence）、多样性采样（coreset）、混合策略。4) 效果：通常只需标注 20-30% 数据即可达到全量标注 90%+ 的效果。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "RLHF、DPO、Constitutional AI 三种对齐方法有什么区别？",
        "difficulty": "advanced",
        "skill_name": "安全对齐",
        "answer_outline": "1) RLHF：SFT → 训练奖励模型（人类偏好对）→ PPO 优化。经典但训练不稳定。2) DPO：直接从偏好对学习策略，跳过奖励模型。训练更稳定，但表达能力可能弱于 RLHF。3) Constitutional AI：用一组原则（宪法）让 LLM 自我批评和修订，减少人工标注。4) 趋势：DPO 及其变体（IPO/KTO）逐步替代 RLHF。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "MoE（Mixture of Experts）架构的核心思路？路由策略有哪些？",
        "difficulty": "advanced",
        "skill_name": "MoE",
        "answer_outline": "1) 核心：FFN 层替换为多个专家网络（Expert），每个 token 只激活 Top-K 个专家。稀疏计算，参数量大但计算量小。2) 路由策略：Token Choice（每个 token 选 top-k 专家）、Expert Choice（每个专家选 top-k token）。3) 负载均衡：辅助 loss 防止专家坍缩（少数专家被过度使用）。4) 代表：Switch Transformer、Mixtral 8x7B、DeepSeek-MoE。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "DPO（Direct Preference Optimization）的原理是什么？相比 RLHF 有什么优势？",
        "difficulty": "advanced",
        "skill_name": "DPO",
        "answer_outline": "1) 原理：将 RLHF 的奖励建模 + PPO 优化合并为一个分类问题。直接从偏好对（chosen/rejected）学习策略。2) 推导：Bradley-Terry 模型下，最优策略有闭式解，loss 是 chosen/rejected 的 log-ratio。3) 优势：无需训练奖励模型、无需 PPO 的采样和 clipping、训练稳定、超参少。4) 局限：依赖离线数据、可能有 distribution shift。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "分布式训练中 FSDP 和 DeepSpeed ZeRO 各有什么特点？",
        "difficulty": "advanced",
        "skill_name": "分布式训练",
        "answer_outline": "1) FSDP（PyTorch 原生）：全分片数据并行，将参数/梯度/优化器状态分片到多卡。前向时按需 all-gather，反向后 reduce-scatter。2) DeepSpeed ZeRO：Stage 1（分片优化器状态）、Stage 2（+分片梯度）、Stage 3（+分片参数）。3) 对比：FSDP 与 PyTorch 生态集成好，DeepSpeed 功能更多（offload、NVMe）。4) 选择：新项目优先 FSDP，已有 DeepSpeed 代码继续用。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "模型推理优化有哪些手段？量化、剪枝、蒸馏各自怎么做？",
        "difficulty": "intermediate",
        "skill_name": "推理优化",
        "answer_outline": "1) 量化：FP16→INT8/INT4（GPTQ/AWQ/SmoothQuant），显存减半到四分之一，精度损失小。2) 剪枝：移除不重要的权重/注意力头/层（SparseGPT、Wanda）。结构化剪枝更友好于硬件加速。3) 蒸馏：大模型（teacher）指导小模型（student）学习，保留能力压缩体积。4) 实践：先量化（最简单有效）→ 再考虑蒸馏（需要训练资源）→ 剪枝（精度敏感慎用）。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "LLM 幻觉有哪些类型？如何检测和缓解？",
        "difficulty": "intermediate",
        "skill_name": "幻觉检测",
        "answer_outline": "1) 类型：事实性幻觉（编造事实）、忠实性幻觉（偏离上下文）、指令幻觉（不遵循指令）。2) 检测：基于外部知识验证（fact-checking）、NLI 模型判断蕴含关系、self-consistency（多次采样看一致性）。3) 缓解：RAG 接入知识库、Chain-of-Verification（自我验证）、self-critique（自我批评）、constrained decoding（限制输出空间）。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "长上下文处理有哪些技术方案？如何让 LLM 处理超长文本？",
        "difficulty": "advanced",
        "skill_name": "长上下文",
        "answer_outline": "1) 位置编码扩展：RoPE 外推（NTK-aware scaling、YaRN）、ALiBi（线性偏置）。2) 注意力优化：FlashAttention（IO 感知分块）、Ring Attention（分布式长序列）。3) 上下文压缩：Landmark Attention、StreamingLLM（attention sink）。4) RAG 替代：检索相关片段而非塞入全文。5) 实践：128K 以内用 RoPE scaling + FlashAttention，更长用 RAG。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "多轮对话管理有哪些挑战？如何维护对话状态？",
        "difficulty": "intermediate",
        "skill_name": "多轮对话",
        "answer_outline": "1) 挑战：指代消解（"它"指什么）、话题切换、上下文窗口限制、一致性维护。2) 状态管理：全量历史（短对话）、摘要压缩（长对话）、槽位填充（任务型对话）。3) 架构：对话管理器维护状态机，context window 管理历史长度。4) 实践：system prompt 放长期记忆，对话历史滑动窗口 + 摘要。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "LLM 服务的监控和可观测性怎么做？需要关注哪些指标？",
        "difficulty": "intermediate",
        "skill_name": "模型监控",
        "answer_outline": "1) 性能指标：TTFT（首 token 延迟）、TPS（每秒 token 数）、P99 延迟、吞吐量。2) 质量指标：用户满意度（thumbs up/down）、hallucination rate、task completion rate。3) 成本指标：token 消耗、GPU 利用率、cost per request。4) 工具：LangSmith、Weights & Biases、自建 Prometheus + Grafana。5) 告警：延迟飙升、错误率突增、GPU 利用率异常。",
        "source": "seed_v2",
    },
    {
        "category": "Project",
        "question": "LLM 应用怎么做 A/B 测试和灰度发布？",
        "difficulty": "intermediate",
        "skill_name": "A/B 测试",
        "answer_outline": "1) A/B 测试：随机分流用户到不同模型/prompt 版本，对比核心指标（转化率/满意度）。2) 灰度发布：1% → 10% → 50% → 100% 逐步放量，每步观察指标。3) LLM 特殊性：输出非确定性（temperature > 0），需要更大样本量。4) 指标：业务指标（转化/留存）+ 模型指标（质量/延迟）+ 成本指标。5) 工具：LaunchDarkly、自建 feature flag。",
        "source": "seed_v2",
    },
    # ═══════════════════════ Coding（7 题）═══════════════════════
    {
        "category": "Coding",
        "question": "手写 Transformer Encoder 的核心代码（Multi-Head Attention + FFN + LayerNorm）。",
        "difficulty": "advanced",
        "skill_name": "Transformer",
        "answer_outline": "1) MultiHeadAttention：Q/K/V 线性投影 → split heads → scaled dot-product → concat → 输出投影。2) FFN：两个线性层 + GELU 激活，中间维度 4x。3) Pre-Norm vs Post-Norm：Pre-Norm（LayerNorm 在前）训练更稳定。4) 残差连接：每个子层输出 + 输入。5) 位置编码：sinusoidal 或 RoPE。",
        "source": "seed_v2",
    },
    {
        "category": "Coding",
        "question": "手写 LoRA 层的实现代码。低秩分解怎么做？如何注入到预训练模型？",
        "difficulty": "advanced",
        "skill_name": "LoRA/QLoRA",
        "answer_outline": "1) LoRA 层：冻结原始权重 W，新增 A（d×r）和 B（r×d）两个矩阵，r << d。输出 = Wx + BAx。2) 初始化：A 用高斯初始化，B 初始化为 0（保证训练开始时 BA=0）。3) 注入：替换 Linear 层的 forward，原始 W 不更新梯度。4) scaling：BA 乘以 alpha/r 缩放因子。5) 合并：推理时 W' = W + BA，无额外推理开销。",
        "source": "seed_v2",
    },
    {
        "category": "Coding",
        "question": "手写 Scaled Dot-Product Attention 的实现。为什么要除以 sqrt(d_k)？",
        "difficulty": "intermediate",
        "skill_name": "Attention",
        "answer_outline": "1) 公式：Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) V。2) 步骤：QK^T 计算相似度 → 缩放 → softmax 归一化 → 加权求和 V。3) 为什么缩放：d_k 大时 QK^T 方差大，softmax 进入饱和区，梯度消失。除以 sqrt(d_k) 使方差稳定在 1。4) 实现细节：causal mask（上三角 -inf）、padding mask。",
        "source": "seed_v2",
    },
    {
        "category": "Coding",
        "question": "手写一个自定义 PyTorch Dataset + DataLoader，支持多进程加载和动态 batching。",
        "difficulty": "intermediate",
        "skill_name": "PyTorch",
        "answer_outline": "1) Dataset：继承 torch.utils.data.Dataset，实现 __len__ 和 __getitem__。2) DataLoader：num_workers 多进程加载、pin_memory 加速 GPU 传输、prefetch_factor 预取。3) 动态 batching：自定义 collate_fn，按长度 padding 到 batch 内最大长度（减少计算浪费）。4) 注意：多进程下避免共享状态、内存泄漏检测（worker_init_fn）。",
        "source": "seed_v2",
    },
    {
        "category": "Coding",
        "question": "手写 BLEU 和 ROUGE-L 评估指标的实现。",
        "difficulty": "intermediate",
        "skill_name": "评估指标",
        "answer_outline": "1) BLEU：n-gram 精度（1-gram 到 4-gram）的几何平均 × brevity penalty。BP = 1 if len_pred > len_ref else exp(1 - len_ref/len_pred)。2) ROUGE-L：最长公共子序列（LCS）长度，recall = LCS/ref_len, precision = LCS/pred_len, F1 = 2*P*R/(P+R)。3) 实现：collections.Counter 统计 n-gram、动态规划求 LCS。4) 平滑：0 counts 用 epsilon 替代避免 log(0)。",
        "source": "seed_v2",
    },
    {
        "category": "Coding",
        "question": "分布式训练中梯度同步怎么做？AllReduce 和 AllGather 有什么区别？",
        "difficulty": "advanced",
        "skill_name": "分布式训练",
        "answer_outline": "1) AllReduce：所有 GPU 的梯度求和/求平均，每个 GPU 得到相同结果。用于标准数据并行。2) AllGather：每个 GPU 持有部分数据，AllGather 后每个 GPU 拥有完整数据。用于 FSDP 前向时收集完整参数。3) ReduceScatter：先 reduce 再 scatter，每个 GPU 只保留一部分结果。用于 FSDP 反向时分片梯度。4) 通信优化：梯度压缩、异步通信、通信计算重叠。",
        "source": "seed_v2",
    },
    {
        "category": "Coding",
        "question": "KV Cache 的原理是什么？如何实现自回归推理的加速？",
        "difficulty": "advanced",
        "skill_name": "KV Cache",
        "answer_outline": "1) 原理：自回归生成时，每个新 token 只需计算自己的 Q，K/V 可以复用之前 token 的结果。2) 实现：维护 cache tensor，每生成一个 token 追加 K/V 到 cache，attention 时用完整 cache 的 K/V。3) 显存占用：cache 大小 = 2 × num_layers × num_heads × seq_len × head_dim × dtype。4) 优化：GQA/MQA 减少 KV 头数、PagedAttention 动态分配显存、量化 KV cache。",
        "source": "seed_v2",
    },
]


def main() -> None:
    init_db()
    db = SessionLocal()
    added = 0
    skipped = 0
    try:
        existing = {
            q.question
            for q in db.query(InterviewQuestion.question).all()
        }
        for item in QUESTIONS:
            if item["question"] in existing:
                skipped += 1
                continue
            db.add(InterviewQuestion(
                category=item["category"],
                question=item["question"],
                difficulty=item.get("difficulty", "intermediate"),
                answer_outline=item.get("answer_outline"),
                skill_name=item.get("skill_name"),
                source=item.get("source", "seed_v2"),
                question_type="open",
                hit_count=0,
                is_verified=False,
            ))
            added += 1
        db.commit()
        print(f"完成：新增 {added} 题，跳过 {skipped} 题（已存在）")

        # 统计
        from sqlalchemy import func
        total = db.query(func.count(InterviewQuestion.id)).scalar()
        cats = db.query(
            InterviewQuestion.category, func.count()
        ).group_by(InterviewQuestion.category).all()
        print(f"\n当前总计: {total} 题")
        for cat, cnt in cats:
            print(f"  {cat}: {cnt}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
