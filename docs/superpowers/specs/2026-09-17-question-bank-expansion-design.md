# 题库补充设计（110 → 150）

> 日期：2026-09-17
> 状态：已批准

## 目标

从 110 题补到 150 题，填 3 个分类缺口 + 覆盖热门技能。

## 缺口分析

| 分类 | 当前 | 目标 | 缺口 |
|---|---|---|---|
| LLM | 48 | 50 | 2 |
| Multimodal | 20 | 30 | 10 |
| Project | 19 | 40 | 21 |
| Coding | 23 | 30 | 7 |
| 合计 | 110 | 150 | 40 |

## 补充技能清单

### Multimodal（10 题）
1. CLIP 原理与对比学习
2. BLIP/BLIP-2 架构
3. LLaVA 视觉指令微调
4. Flamingo 少样本多模态
5. 视觉编码器（ViT / SigLIP）
6. 多模态对齐策略
7. 图文检索与相似度
8. 视频理解模型
9. OCR 与文档理解
10. 多模态 Agent

### Project（21 题）
1. RAG 架构设计
2. RAG 检索策略（向量/混合/重排）
3. RAG 评估指标
4. Agent 架构（ReAct/Plan-and-Execute）
5. Agent 工具调用与函数签名
6. Prompt Engineering 技巧
7. Prompt 注入防御
8. 评估体系设计（自动/人工/LLM-as-Judge）
9. 模型部署优化（vLLM/TGI）
10. 数据清洗与标注流程
11. 数据飞轮与主动学习
12. 安全对齐（RLHF/DPO/Constitutional AI）
13. MoE 架构与路由策略
14. DPO 原理与实现
15. 分布式训练（FSDP/DeepSpeed）
16. 推理优化（量化/剪枝/蒸馏）
17. 幻觉检测与缓解
18. 长上下文处理
19. 多轮对话管理
20. 模型监控与可观测性
21. A/B 测试与灰度发布

### Coding（7 题）
1. 手撕 Transformer Encoder
2. 手撕 LoRA 层
3. 手撕 Scaled Dot-Product Attention
4. 自定义 Dataset + DataLoader
5. BLEU/ROUGE 评估指标实现
6. 分布式训练梯度同步
7. KV Cache 推理优化

## 执行方式

新建 `backend/scripts/seed_questions_v2.py`，每题包含：
- `question`：题目文本
- `answer_outline`：参考答案要点（3-5 条）
- `category`：LLM / Multimodal / Project / Coding
- `difficulty`：beginner / intermediate / advanced
- `skill_name`：关联技能（canonical name）
- `source`：`seed_v2`
- `question_type`：`open`（默认）

跑一次脚本批量录入，幂等（按 question 文本去重）。
