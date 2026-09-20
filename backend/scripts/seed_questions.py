"""题库种子脚本。

按4分类（LLM / Multimodal / Project / Coding）填充面试题，
对齐主攻赛道技能（Transformer / Attention / SFT / LoRA / PyTorch 等）。

运行：cd backend && python scripts/seed_questions.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import SessionLocal, init_db
from app.models.interview_question import InterviewQuestion

# ───────────────────────── 题目数据 ─────────────────────────

QUESTIONS: list[dict] = [
    # ═══════ LLM（目标 50 题，核心必达） ═══════
    # Transformer 基础
    {"category": "LLM", "question": "Transformer 的 self-attention 计算复杂度是多少？如何降低？", "difficulty": "intermediate", "skill_name": "Transformer", "answer_outline": "O(n²d)，n为序列长度，d为维度。降低方法：Sparse Attention、Linear Attention、FlashAttention（IO感知分块计算）"},
    {"category": "LLM", "question": "Multi-Head Attention 为什么要用多个头？和单头的区别？", "difficulty": "beginner", "skill_name": "Attention", "answer_outline": "多头让模型在不同子空间捕获不同模式（语法、语义、位置等）。单头只能学一种注意力分布。多头拼接后线性投影融合。"},
    {"category": "LLM", "question": "RoPE 位置编码的原理？相比 Sinusoidal 和 ALiBi 的优势？", "difficulty": "advanced", "skill_name": "Transformer", "answer_outline": "RoPE 把位置信息编码为旋转矩阵，作用于 Q/K 向量。优势：相对位置信息自然涌现、外推性好。ALiBi 无需训练位置参数，直接加偏置。"},
    {"category": "LLM", "question": "KV Cache 在推理中起什么作用？如何优化其内存占用？", "difficulty": "intermediate", "skill_name": "Transformer", "answer_outline": "缓存已计算的 K/V 避免重复计算。优化：GQA（分组查询注意力，减少KV头数）、MQA、PagedAttention（vLLM，按块分配显存）、量化KV Cache。"},
    {"category": "LLM", "question": "Layer Normalization 和 Batch Normalization 在 LLM 中的区别？为什么用 Pre-Norm？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "BN 按 batch 维度归一化，LN 按 feature 维度。LLM 用 LN 因为序列长度不一。Pre-Norm（先归一化再做子层）训练更稳定，梯度流更顺畅。"},
    # 预训练
    {"category": "LLM", "question": "大模型预训练的三个阶段分别是什么？", "difficulty": "beginner", "skill_name": "Pretraining", "answer_outline": "1) Pretraining（无监督/自监督，在大规模语料上学语言建模）2) SFT（监督微调，学指令遵循）3) RLHF/DPO（对齐人类偏好）"},
    {"category": "LLM", "question": "Causal Language Modeling 和 Masked Language Modeling 的区别？各自用在什么模型？", "difficulty": "beginner", "skill_name": "Pretraining", "answer_outline": "CLM：预测下一个 token（GPT 系列），从左到右。MLM：随机 mask 预测被遮住的 token（BERT 系列），双向。生成式用 CLM，理解式用 MLM。"},
    {"category": "LLM", "question": "Scaling Law 的核心发现是什么？对训练决策有什么指导意义？", "difficulty": "intermediate", "skill_name": "Pretraining", "answer_outline": "Chinchilla 定律：给定计算预算，模型参数和数据量应按比例增长。最优比约 1:20（参数:token）。数据不够时增大模型收益递减。"},
    {"category": "LLM", "question": "FlashAttention 的核心思想是什么？为什么能加速？", "difficulty": "advanced", "skill_name": "Attention", "answer_outline": "IO 感知的分块计算：把 Q/K/V 分块加载到 SRAM，在 SRAM 内完成 softmax 和乘法，避免反复读写 HBM。减少内存访问次数，训练速度提升2-4倍。"},
    {"category": "LLM", "question": "混合专家模型（MoE）的工作原理？负载均衡怎么解决？", "difficulty": "advanced", "skill_name": "Transformer", "answer_outline": "Router 选 top-k 专家处理 token，只有被选中的专家参与计算（稀疏激活）。负载均衡：辅助损失（auxiliary loss）鼓励均匀路由，或用 capacity factor 限制每专家处理量。"},
    # SFT & LoRA
    {"category": "LLM", "question": "SFT（监督微调）的数据格式是什么？质量 vs 数量哪个更重要？", "difficulty": "beginner", "skill_name": "SFT", "answer_outline": "指令-输入-输出三元组（instruction/input/output）。质量远比数量重要：LIMA 论文用1000条高质量数据就能达到不错效果。数据多样性是关键。"},
    {"category": "LLM", "question": "LoRA 的原理是什么？秩 r 怎么选？", "difficulty": "intermediate", "skill_name": "LoRA/QLoRA", "answer_outline": "冻结原始权重，用两个低秩矩阵 A(r×d) 和 B(d×r) 近似增量更新。r 通常8-64，越大学习能力越强但参数越多。一般先试r=16，效果不够再加大。"},
    {"category": "LLM", "question": "QLoRA 相比 LoRA 做了哪些改进？", "difficulty": "intermediate", "skill_name": "LoRA/QLoRA", "answer_outline": "4-bit NormalFloat 量化基座 + 双重量化（量化参数本身也量化）+ 分页优化器。用48GB显存微调65B模型。精度损失极小，是 LoRA 的显存优化版。"},
    {"category": "LLM", "question": "如何判断 SFT 是否过拟合？有哪些正则化手段？", "difficulty": "intermediate", "skill_name": "SFT", "answer_outline": "监控 eval loss 不再下降甚至上升。正则化：dropout、weight decay、early stopping、数据增强（改写指令）、减少训练轮数（1-3 epoch 通常够）。"},
    {"category": "LLM", "question": "全参数微调 vs LoRA 微调，各自适用什么场景？", "difficulty": "intermediate", "skill_name": "LoRA/QLoRA", "answer_outline": "全参数：数据充足、计算预算大、需要最大化性能。LoRA：资源有限、快速迭代、多任务共享基座。LoRA 效果通常达全参数的90-95%，但显存只需1/10。"},
    # 推理优化
    {"category": "LLM", "question": "模型量化的常见方案有哪些？INT8 和 INT4 的精度差异？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "PTQ（训练后量化）、QAT（量化感知训练）。INT8 精度损失极小（<1%），几乎无损。INT4 需要更精细的量化方案（GPTQ/AWQ），有少量精度损失但显存减半。"},
    {"category": "LLM", "question": "vLLM 的 PagedAttention 解决了什么问题？", "difficulty": "advanced", "skill_name": "Transformer", "answer_outline": "解决 KV Cache 显存碎片化。传统方式预分配连续显存，浪费严重。PagedAttention 按页管理 KV Cache，类似操作系统虚拟内存，显存利用率提升至接近100%。"},
    {"category": "LLM", "question": "Speculative Decoding 的原理是什么？", "difficulty": "advanced", "skill_name": "Transformer", "answer_outline": "用小模型（draft model）快速生成多个候选 token，再用大模型一次性验证。验证通过的 token 直接采纳，不通过的从分布中重采样。吞吐量提升2-3倍，输出质量不变。"},
    {"category": "LLM", "question": "连续批处理（Continuous Batching）和静态批处理的区别？", "difficulty": "intermediate", "skill_name": "Transformer", "answer_outline": "静态：一批请求必须全部完成才能处理下一批（短请求等长请求）。连续：请求完成后立即插入新请求，GPU 利用率高。vLLM/TGI 都用连续批处理。"},
    {"category": "LLM", "question": "长上下文（128K+）的技术挑战有哪些？如何解决？", "difficulty": "advanced", "skill_name": "Attention", "answer_outline": "挑战：注意力O(n²)、位置编码外推、Lost-in-the-middle。方案：RoPE外推/NTK-aware scaling、Ring Attention（分布式序列并行）、YaRN、StreamingLLM。"},
    # RAG & Agent
    {"category": "LLM", "question": "RAG 系统的完整链路是什么？有哪些优化点？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "索引（分块→向量化→存入向量库）→ 检索（query向量化→top-k）→ 生成（拼接context→LLM回答）。优化：分块策略、HyDE、Reranker、混合检索（向量+BM25）、查询改写。"},
    {"category": "LLM", "question": "ReAct 框架的推理-行动循环是什么？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "Thought（推理当前状态）→ Action（选择工具执行）→ Observation（获取结果）→ 循环直到得出答案。让LLM能与外部环境交互，解决需要多步推理的任务。"},
    {"category": "LLM", "question": "Function Calling 的实现原理？和传统 API 调用的区别？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "把函数 schema 注入 system prompt，LLM 输出结构化的函数调用 JSON。区别：LLM 自主决定何时调用、传什么参数，不需要硬编码规则。"},
    {"category": "LLM", "question": "如何评估 RAG 系统的效果？有哪些指标？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "检索指标：Recall@K、MRR、NDCG。生成指标：Faithfulness（答案忠于检索文档）、Answer Relevance、Context Relevance。框架：RAGAS、TruLens。"},
    {"category": "LLM", "question": "CoT（Chain-of-Thought）提示为什么有效？Zero-shot CoT 怎么用？", "difficulty": "beginner", "skill_name": "Deep Learning", "answer_outline": "让模型展示推理过程，激活隐含的推理能力。Zero-shot CoT：只需加一句\"Let's think step by step\"就能触发。对数学、逻辑推理任务提升明显。"},
    # 更多 LLM 题
    {"category": "LLM", "question": "Temperature 和 Top-P 在解码中的作用？怎么调？", "difficulty": "beginner", "skill_name": "Deep Learning", "answer_outline": "Temperature 控制概率分布平滑度（低=确定性，高=随机）。Top-P (nucleus sampling) 只从累积概率达P的最小集合中采样。创意任务高temp+高topP，精确任务低temp。"},
    {"category": "LLM", "question": "RLHF 的三个阶段分别是什么？DPO 相比 RLHF 的优势？", "difficulty": "intermediate", "skill_name": "SFT", "answer_outline": "1) SFT 2) 训练 Reward Model（人类偏好数据）3) PPO 优化。DPO 优势：不需要单独的 RM，直接从偏好数据优化策略，训练更稳定、更简单。"},
    {"category": "LLM", "question": "Tokenizer 的 BPE 算法原理？中文和英文的分词差异？", "difficulty": "beginner", "skill_name": "Transformer", "answer_outline": "BPE：从字符开始，反复合并最高频的相邻对。英文按子词切分（unhappiness → un+happi+ness），中文通常按字或词切分。中文 token 效率低（一个汉字可能2-3个token）。"},
    {"category": "LLM", "question": "模型并行（Tensor/Pipeline/Sequence Parallelism）的区别？", "difficulty": "advanced", "skill_name": "Deep Learning", "answer_outline": "Tensor：把单层权重切分到多卡（Megatron-LM）。Pipeline：不同层放不同卡（GPipe）。Sequence：把序列维度切分（Ring Attention）。通常组合使用。"},
    {"category": "LLM", "question": "幻觉（Hallucination）的成因和缓解方法？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "成因：训练数据噪声、解码随机性、知识过时。缓解：RAG引入外部知识、Self-Consistency（多次采样投票）、事实性检验链、Constrained Decoding。"},
    {"category": "LLM", "question": "Adapter 微调和 LoRA 的区别？各有什么优缺点？", "difficulty": "intermediate", "skill_name": "LoRA/QLoRA", "answer_outline": "Adapter：在层间插入小型前馈网络，增加推理延迟。LoRA：低秩分解权重更新，不增加推理延迟（可合并）。LoRA 更主流。"},
    {"category": "LLM", "question": "如何做 LLM 的安全对齐？Red Teaming 怎么实施？", "difficulty": "advanced", "skill_name": "SFT", "answer_outline": "安全对齐：SFT 加安全数据 + RLHF 奖励模型偏好安全回答 + Constitutional AI。Red Teaming：组建攻击团队用对抗 prompt 测试，发现漏洞后补充训练数据修复。"},
    {"category": "LLM", "question": "Prefix Decoding 和 Prefill-then-Decode 的区别？", "difficulty": "advanced", "skill_name": "Transformer", "answer_outline": "Prefill：一次性计算 prompt 所有 token 的 KV Cache（compute-bound）。Decode：逐个生成 token（memory-bound）。Prefix Decoding 复用相同前缀的 KV Cache，适合多轮对话。"},
    {"category": "LLM", "question": "MoE 模型（如 Mixtral）的推理和 Dense 模型有什么不同？", "difficulty": "advanced", "skill_name": "Transformer", "answer_outline": "MoE 每层只有 top-k 专家被激活（如8选2），计算量远小于同参数量 Dense 模型。但需要 All-to-All 通信交换专家分配，通信开销是瓶颈。显存需要容纳所有专家。"},
    {"category": "LLM", "question": "LoRA 的权重如何合并回原模型？合并后有什么好处？", "difficulty": "beginner", "skill_name": "LoRA/QLoRA", "answer_outline": "W' = W + BA，直接矩阵加法合并。好处：推理时零额外延迟，和原模型架构完全一致，可正常量化部署。"},
    {"category": "LLM", "question": "什么是 Instruction Following 评估？常见的 benchmark 有哪些？", "difficulty": "intermediate", "skill_name": "SFT", "answer_outline": "评估模型遵循指令的能力。MMLU（多任务）、HumanEval（代码）、GSM8K（数学）、MT-Bench（多轮对话）、IFEval（严格指令遵循）、AlpacaEval。"},
    {"category": "LLM", "question": "模型蒸馏（Knowledge Distillation）在 LLM 中怎么用？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "用大模型（teacher）的输出概率分布训练小模型（student）。LLM 场景：用 GPT-4 生成高质量回答训练小模型（如 Alpaca、Vicuna）。也可蒸馏中间层特征。"},
    {"category": "LLM", "question": "为什么 Pre-Norm 比 Post-Norm 训练更稳定？", "difficulty": "advanced", "skill_name": "Transformer", "answer_outline": "Post-Norm 梯度在深层会指数放大（梯度爆炸）。Pre-Norm 残差连接直接传递梯度，不经过 Norm 层，梯度流更顺畅。代价是 Pre-Norm 最终性能可能略低于收敛良好的 Post-Norm。"},
    {"category": "LLM", "question": "FlashAttention v2 相比 v1 的改进是什么？", "difficulty": "advanced", "skill_name": "Attention", "answer_outline": "v2 改进了线程块的工作分配（减少非矩阵乘法操作）、更好的并行化（跨序列长度维度并行）、支持头维度不等的 GQA。速度比 v1 再快约2倍。"},
    {"category": "LLM", "question": "SFT 数据中的 system prompt 有什么作用？应该怎么写？", "difficulty": "beginner", "skill_name": "SFT", "answer_outline": "设定模型角色、行为边界和输出格式。好的 system prompt：明确角色（\"你是一个...\"）、给出约束（\"不要...\"）、规定格式（\"用JSON输出\"）。保持简洁，不要太长。"},

    # ═══════ Multimodal（目标 30 题，核心必达） ═══════
    {"category": "Multimodal", "question": "Vision Transformer (ViT) 的工作原理？和 CNN 的区别？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "把图片切 patch → 线性投影 → Transformer 编码。CNN 有归纳偏置（局部性、平移不变性），ViT 需要更多数据但扩展性更好。ViT + 大规模预训练 > CNN。"},
    {"category": "Multimodal", "question": "CLIP 的对比学习目标是什么？为什么能做 zero-shot？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "图文对的相似度最大化，非配对的最小化（InfoNCE loss）。Zero-shot：把类别名变成文本 embedding，和图片 embedding 算相似度，无需任何标注数据。"},
    {"category": "Multimodal", "question": "LLaVA 的架构设计？视觉编码器和语言模型怎么连接？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "CLIP 视觉编码器 → 投影层（MLP）→ 拼接到 LLM 的 token 序列。两阶段训练：1) 预训练投影层（冻结ViT和LLM）2) 端到端微调。"},
    {"category": "Multimodal", "question": "多模态模型如何处理不同分辨率的图片？", "difficulty": "advanced", "skill_name": "Deep Learning", "answer_outline": "方案：动态分辨率（切多个子图分别编码）、Position Embedding 插值（支持任意分辨率）、Native Resolution（如 Qwen-VL2 直接处理原始分辨率）。"},
    {"category": "Multimodal", "question": "Grounding 能力是什么？多模态模型如何实现定位？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "模型输出中包含物体的边界框坐标（如 <box>x1,y1,x2,y2</box>）。通过在训练数据中加入坐标标注实现。用于指代理解（\"红色的那个\"→输出位置）。"},
    {"category": "Multimodal", "question": "多模态大模型的训练数据有哪些类型？", "difficulty": "beginner", "skill_name": "Deep Learning", "answer_outline": "图文对（CLIP预训练）、图文交错文档（网页）、VQA（视觉问答）、OCR数据、图表理解、视频描述。数据质量和多样性是关键。"},
    {"category": "Multimodal", "question": "OCR 在多模态模型中怎么处理？和传统 OCR 的区别？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "端到端：直接从图片理解文字内容，不需要先检测再识别。优势：能理解版面布局、表格、公式。传统 OCR 只输出文本，多模态 OCR 能理解语义。"},
    {"category": "Multimodal", "question": "视频理解模型和图片理解模型的主要区别？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "视频需要处理时序信息。方案：均匀采样帧 → 分别编码 → 时序聚合（Temporal Attention / Pooling）。挑战：token 数量爆炸（帧数×每帧 patch 数）。"},
    {"category": "Multimodal", "question": "Diffusion Model 的前向和反向过程是什么？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "前向：逐步加高斯噪声直到纯噪声。反向：学习去噪过程，从噪声逐步恢复图像。U-Net 预测噪声，采样时迭代去噪。Stable Diffusion 在 latent space 做扩散。"},
    {"category": "Multimodal", "question": "ControlNet 的原理？如何控制生成图像的结构？", "difficulty": "advanced", "skill_name": "Deep Learning", "answer_outline": "在 U-Net 旁加一个可训练的副本，接收控制条件（边缘图/深度图/姿态）。Zero Convolution 连接（初始权重为0的1×1卷积），训练初期不影响原模型。"},
    {"category": "Multimodal", "question": "多模态模型的幻觉问题有什么特点？", "difficulty": "advanced", "skill_name": "Deep Learning", "answer_outline": "视觉幻觉：描述图中不存在的物体。成因：训练数据中的语言先验过强（\"桌子上通常有杯子\"）。缓解：Grounding 数据、RLHF with visual reward、对比解码。"},
    {"category": "Multimodal", "question": "图文检索（Image-Text Retrieval）的评估指标？", "difficulty": "beginner", "skill_name": "Deep Learning", "answer_outline": "Recall@K（前K个结果中包含正确配对的比例）、Median Rank、MRR。分两个方向：Image→Text 和 Text→Image。Flickr30K、COCO 是常用 benchmark。"},
    {"category": "Multimodal", "question": "SigLIP 和 CLIP 的损失函数区别？", "difficulty": "advanced", "skill_name": "Deep Learning", "answer_outline": "CLIP 用 InfoNCE（softmax cross-entropy），需要全局归一化。SigLIP 用 sigmoid loss（逐对二分类），不需要全局归一化，可扩展到更大 batch。"},
    {"category": "Multimodal", "question": "多模态 Agent 能做什么？举例说明。", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "GUI Agent：理解屏幕截图→操作UI元素（点击、输入）。具身Agent：理解场景→规划动作→操控机器人。工具Agent：看图表→调用计算器→生成报告。"},
    {"category": "Multimodal", "question": "Flamingo 模型的交叉注意力机制？", "difficulty": "advanced", "skill_name": "Deep Learning", "answer_outline": "在冻结的 LLM 层间插入交叉注意力层（Gated X-Attention），视觉 token 作为 K/V，文本 token 作为 Q。门控机制（初始化为0）控制视觉信息注入量。"},

    # ═══════ Project（目标 40 题） ═══════
    {"category": "Project", "question": "你在项目中如何做模型选型？考虑哪些因素？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "因素：任务类型、数据量、推理延迟要求、部署成本、团队能力。流程：定义评估指标→基线模型→小规模实验→对比分析→选定。不要只看 benchmark，要看实际场景。"},
    {"category": "Project", "question": "RAG 系统上线后发现检索质量差，你怎么排查和优化？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "排查：1) 看检索结果是否相关（检索问题）2) 看 LLM 是否正确利用了 context（生成问题）。优化：调整分块大小、试不同 embedding 模型、加 Reranker、HyDE、混合检索。"},
    {"category": "Project", "question": "如何设计一个可扩展的 Prompt 管理系统？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "版本控制（git-like）、A/B 测试框架、评估 pipeline（自动打分）、模板变量注入、环境隔离（dev/staging/prod）。避免硬编码 prompt 在代码里。"},
    {"category": "Project", "question": "大模型推理服务的监控应该关注哪些指标？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "延迟（TTFT、TPS、E2E）、吞吐（QPS）、GPU 利用率、显存占用、队列深度、错误率、Token 成本。业务指标：回答质量分、用户满意度。"},
    {"category": "Project", "question": "如何做 LLM 的 A/B 测试？和传统 A/B 有什么不同？", "difficulty": "advanced", "skill_name": "Deep Learning", "answer_outline": "不同：LLM 输出非确定性、评估维度多（质量/安全/延迟）、需要人工评估。方案：流量分桶、多维度评分、自动评估+人工抽检、统计显著性检验。"},
    {"category": "Project", "question": "多轮对话系统的上下文管理怎么做？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "策略：滑动窗口（保留最近N轮）、摘要压缩（LLM 总结历史）、分层存储（近期全文+远期摘要）。挑战：token 预算、关键信息可能被截断。"},
    {"category": "Project", "question": "如何评估一个 SFT 数据集的质量？", "difficulty": "intermediate", "skill_name": "SFT", "answer_outline": "维度：准确性（答案正确）、多样性（覆盖不同场景）、一致性（格式统一）、难度梯度。方法：随机抽样人工审查、用强模型自动评分、训练小规模验证效果。"},
    {"category": "Project", "question": "模型上线后用户反馈回答质量下降，你怎么排查？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "1) 收集 bad case 分类（幻觉/格式/安全/延迟）2) 对比线上 prompt 和离线 3) 检查是否有数据漂移 4) 检查模型版本/配置变更 5) A/B 对比确认。"},
    {"category": "Project", "question": "如何设计一个 Agent 系统的错误处理和重试机制？", "difficulty": "advanced", "skill_name": "Deep Learning", "answer_outline": "分层处理：工具调用失败→重试+fallback、LLM 输出格式错误→重试+约束解码、循环检测→限制步数+兜底回答。日志完整记录每步决策。"},
    {"category": "Project", "question": "向量数据库选型考虑哪些因素？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "维度支持、索引类型（HNSW/IVF）、过滤能力（向量+标量混合查询）、扩展性、运维复杂度。Milvus（分布式）、Qdrant（Rust高性能）、Chroma（轻量级）、Pinecone（托管）。"},
    {"category": "Project", "question": "如何用最少的人工标注构建高质量 SFT 数据？", "difficulty": "advanced", "skill_name": "SFT", "answer_outline": "Self-Instruct（用 LLM 自己生成指令数据）、Evol-Instruct（逐步增加复杂度）、人工审核过滤（而非全人工编写）、主动学习（选最有价值的样本标注）。"},
    {"category": "Project", "question": "RAG 系统的分块策略怎么选？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "固定大小（简单但可能切断语义）、语义分块（按段落/章节）、递归分块（LangChain RecursiveCharacterTextSplitter）。大小 256-1024 token，重叠 10-20%。不同类型文档用不同策略。"},
    {"category": "Project", "question": "如何处理多语言 RAG 场景？", "difficulty": "advanced", "skill_name": "Deep Learning", "answer_outline": "Embedding 选多语言模型（BGE-M3、E5-Multilingual）、查询翻译（先翻再检索）、跨语言检索、混合索引。评估需覆盖各语言的 Recall。"},
    {"category": "Project", "question": "大模型应用的成本优化有哪些策略？", "difficulty": "intermediate", "skill_name": "Deep Learning", "answer_outline": "模型路由（简单用小模型、复杂用大模型）、缓存（语义缓存相似查询）、Prompt 压缩、批量推理、量化部署、按需扩缩容。监控每请求 token 成本。"},
    {"category": "Project", "question": "如何设计 LLM 应用的自动化评估 pipeline？", "difficulty": "advanced", "skill_name": "Deep Learning", "answer_outline": "评估维度：正确性、相关性、安全性、格式。方法：GPT-4 做 judge、规则匹配、embedding 相似度、人工抽检校准。流水线：golden set → 自动评分 → 回归检测 → 告警。"},

    # ═══════ Coding（目标 30 题） ═══════
    {"category": "Coding", "question": "实现一个简单的 BPE Tokenizer（核心算法部分）。", "difficulty": "intermediate", "skill_name": "Python", "answer_outline": "1) 统计相邻 pair 频率 2) 合并最高频 pair 为新 token 3) 重复直到达到词表大小。关键：用 defaultdict 统计，合并时更新词表和分割结果。"},
    {"category": "Coding", "question": "用 PyTorch 实现 Multi-Head Attention。", "difficulty": "intermediate", "skill_name": "PyTorch", "answer_outline": "Q/K/V 线性投影 → split heads → scaled dot-product attention → concat → output projection。关键：view/transpose 做 head 维度变换，mask 用 triu。"},
    {"category": "Coding", "question": "实现一个简单的 RAG 检索函数（给定 embedding 和 query）。", "difficulty": "beginner", "skill_name": "Python", "answer_outline": "1) 对 query 做 embedding 2) 计算和所有文档的 cosine similarity 3) 取 top-k 返回。用 numpy 或 torch 实现，注意归一化。"},
    {"category": "Coding", "question": "实现 LoRA 层（forward 方法）。", "difficulty": "advanced", "skill_name": "PyTorch", "answer_outline": "forward(x): return x @ W + (x @ A @ B) * alpha/r。A 初始化为 normal，B 初始化为 zero（保证初始输出为零）。dropout 可选。"},
    {"category": "Coding", "question": "写一个函数计算 BLEU-4 分数。", "difficulty": "advanced", "skill_name": "Python", "answer_outline": "1) 计算 1-4 gram 的精确率 2) 几何平均 3) 乘以 brevity penalty。关键：n-gram 计数要 clip（不超过参考中最大次数），BP = min(1, ref_len/gen_len)。"},
    {"category": "Coding", "question": "用 Python 实现一个简单的向量数据库（支持插入和 top-k 查询）。", "difficulty": "intermediate", "skill_name": "Python", "answer_outline": "存向量列表，查询时算 cosine similarity 全量扫描取 top-k。优化：用 numpy 矩阵运算批量计算。生产环境需要建索引（HNSW/IVF）。"},
    {"category": "Coding", "question": "实现 Cross-Entropy Loss（带 temperature）。", "difficulty": "intermediate", "skill_name": "PyTorch", "answer_outline": "logits/temperature → log_softmax → 取目标类别的 log_prob → 求负平均。注意数值稳定性：减去 max(logits)防溢出。"},
    {"category": "Coding", "question": "实现一个简单的 Agent 循环（ReAct 模式）。", "difficulty": "intermediate", "skill_name": "Python", "answer_outline": "while not done: prompt LLM → parse action → execute tool → append observation → check stop condition。关键：限制最大步数，处理工具调用失败，解析 LLM 输出。"},
    {"category": "Coding", "question": "用 PyTorch 实现 Layer Normalization。", "difficulty": "intermediate", "skill_name": "PyTorch", "answer_outline": "沿最后一维计算 mean 和 var → 归一化 → 可学习的 gamma 和 beta 做仿射变换。和 BatchNorm 的区别：不跨 batch 统计。"},
    {"category": "Coding", "question": "实现 cosine learning rate scheduler。", "difficulty": "beginner", "skill_name": "PyTorch", "answer_outline": "lr = min_lr + 0.5*(max_lr-min_lr)*(1+cos(π*step/total_steps))。实现：继承 _LRScheduler，override get_lr()。"},
    {"category": "Coding", "question": "写一个函数解析 LLM 输出中的 JSON（容错处理）。", "difficulty": "intermediate", "skill_name": "Python", "answer_outline": "1) 尝试直接 json.loads 2) 失败则正则提取 ```json...``` 块 3) 再失败则找 { 和 } 匹配 4) 用 json-repair 库修复。多层 fallback。"},
    {"category": "Coding", "question": "实现 Top-K 和 Top-P 采样。", "difficulty": "intermediate", "skill_name": "Python", "answer_outline": "Top-K：排序取前K，重新归一化，采样。Top-P：排序后累积概率达P的最小集合，重新归一化，采样。两者可组合：先 Top-K 再 Top-P。"},
    {"category": "Coding", "question": "实现一个简单的 Embedding 模型训练（对比学习）。", "difficulty": "advanced", "skill_name": "PyTorch", "answer_outline": "InfoNCE loss：正对相似度最大化，负对最小化。batch 内负采样。编码器共享权重。关键：大 batch size 对比学习效果好，用梯度累积模拟大 batch。"},
    {"category": "Coding", "question": "用 Python 实现 trie 树（用于 constrained decoding）。", "difficulty": "intermediate", "skill_name": "Python", "answer_outline": "节点存 children dict 和 is_end 标记。insert(word)、search(word)、starts_with(prefix)。Constrained decoding：根据 trie 只允许输出合法 token。"},
    {"category": "Coding", "question": "实现 beam search 解码。", "difficulty": "advanced", "skill_name": "Python", "answer_outline": "维护 top-k 个候选序列。每步扩展所有候选，取总概率最高的 k 个。结束条件：生成 EOS 或达到 max_length。length normalization 防止偏好短序列。"},
    {"category": "Coding", "question": "写一个简单的 Prompt 模板引擎（支持变量替换和条件逻辑）。", "difficulty": "beginner", "skill_name": "Python", "answer_outline": "用 Jinja2 或手写：{variable} 替换、{% if %} 条件、{% for %} 循环。支持默认值、格式化。核心是 string.Template 或正则替换。"},
    {"category": "Coding", "question": "实现一个简单的文本分块器（Chunker）。", "difficulty": "beginner", "skill_name": "Python", "answer_outline": "按固定 token 数切分，支持重叠。用 tiktoken 计数。进阶：按段落/句子边界切分，保证语义完整性。"},
    {"category": "Coding", "question": "用 PyTorch 实现 Group Query Attention (GQA)。", "difficulty": "advanced", "skill_name": "PyTorch", "answer_outline": "Q 有 n_heads 个头，K/V 只有 n_kv_heads 个头（n_heads % n_kv_heads == 0）。每个 KV 头被多个 Q 头共享。比 MHA 省显存，比 MQA 效果好。"},
    {"category": "Coding", "question": "实现一个简单的评估函数（计算 ROUGE-L 分数）。", "difficulty": "intermediate", "skill_name": "Python", "answer_outline": "ROUGE-L = LCS长度 / 参考长度。LCS（最长公共子序列）用动态规划。分别算 precision 和 recall，取 F1。"},
    {"category": "Coding", "question": "实现 gradient accumulation 的训练循环。", "difficulty": "intermediate", "skill_name": "PyTorch", "answer_outline": "loss /= accumulation_steps → loss.backward() → 每 accumulation_steps 步 optimizer.step() + zero_grad()。模拟大 batch，显存只需 1/accumulation_steps。"},

    # ═══════ 补充题（覆盖更多技能） ═══════
    {"category": "LLM", "question": "DeepSpeed ZeRO 的三个阶段分别优化了什么？", "difficulty": "advanced", "skill_name": "Deep Learning", "answer_outline": "ZeRO-1：切分优化器状态。ZeRO-2：切分梯度。ZeRO-3：切分参数。每级都减少显存但增加通信。ZeRO-3 + NVMe offload 可训超大模型。"},
    {"category": "LLM", "question": "什么是 Catastrophic Forgetting？LoRA 能缓解吗？", "difficulty": "intermediate", "skill_name": "LoRA/QLoRA", "answer_outline": "微调时模型忘记预训练知识。LoRA 能缓解（冻结原始权重，只改低秩增量），但不能完全避免。进一步缓解：正则化（EWC）、回放旧数据、多任务训练。"},
    {"category": "Multimodal", "question": "图像分割模型（SAM）的 prompt 机制是什么？", "difficulty": "advanced", "skill_name": "Deep Learning", "answer_outline": "SAM 支持点、框、文本作为 prompt。Prompt Encoder 编码输入 → Mask Decoder 与图像 embedding 交叉注意力 → 输出分割 mask。Zero-shot 泛化能力强。"},
    {"category": "Coding", "question": "实现一个简单的 Rate Limiter（令牌桶算法）。", "difficulty": "intermediate", "skill_name": "Python", "answer_outline": "桶以固定速率填充令牌，请求消耗令牌，桶空则拒绝。实现：记录上次时间和当前令牌数，每次请求按时间差补充。线程安全需加锁。"},
    {"category": "Project", "question": "如何做 LLM 的持续预训练（Continual Pretraining）？", "difficulty": "advanced", "skill_name": "Pretraining", "answer_outline": "在通用模型基础上用领域数据继续预训练。关键：数据配比（领域+通用混合防遗忘）、学习率衰减、数据清洗。比从头训练省算力，保留通用能力。"},
]


def seed():
    """写入种子题目（幂等：按 question 文本去重）。"""
    db = SessionLocal()
    try:
        existing = {q.question for q in db.query(InterviewQuestion.question).all()}
        added = 0
        for q in QUESTIONS:
            if q["question"] in existing:
                continue
            db.add(InterviewQuestion(
                category=q["category"],
                question=q["question"],
                difficulty=q["difficulty"],
                answer_outline=q.get("answer_outline"),
                skill_name=q.get("skill_name"),
                source="seed",
                hit_count=0,
                is_verified=False,
            ))
            added += 1
        db.commit()
        print(f"题库种子：新增 {added} 题（跳过 {len(QUESTIONS) - added} 已有）")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    seed()
