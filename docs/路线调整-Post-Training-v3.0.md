# 路线调整 v3.0：主轴收敛为 Post-Training

日期：2026-09-18。用户确认此为**最终框架**（不再第四次 reframe），已落地并重跑种子校验通过。

## 决策

主轴由「LLM + VLM」收敛为 **Post-Training / 大模型后训练**：

- 首选：**Post-Training / Model Training**（SFT → DPO → RL）
- 次选（模型方向）：**VLM / Multimodal**（Post-Training 的多模态分支，非独立 hedge）
- 第三：**AI Infra / Inference**（由 `ai-algo` 保底赛道承载）
- 长期（on-job）：**VLA / Robot Learning / Embodied AI**

贯穿式项目由 Mini-VLM 升级为 **Mini Post-Training Lab**（01_sft / 02_lora / 03_dpo / 04_evaluation / 05_badcase / 06_vlm_sft / 07_inference）。

## 改了什么（4 个文件）

1. `backend/app/core/skill_profile.py`：B 级 Weak 区新增 **GRPO**（level=1, target=3，与 DPO/RLHF 同口径）。
2. `backend/app/core/target_roles.py`：`llm` 改名「大模型后训练 / Post-Training 算法工程师」，required_skills 加 `DPO`/`RLHF`/`GRPO`；`vlm` 改「模型方向」并加 `DPO`；`embodied` 维持 `frozen=True`。
3. `backend/app/core/plan_30d.py`：标题/PHASES 改 Post-Training 主轴；`RESOURCE_LOCK` 加 DPO/GRPO/Qwen2.5-VL（5→8 类）；`D_LEVEL_FORBIDDEN` **移除 RLHF**（解禁后训练）；Day22 扩为 Mini Post-Training Lab；Day23 由 Inference Benchmark 改为 DPO/GRPO 学完即资产；`SKILL_TO_DAY_SEQ` 加 `DPO:23`。**30 天契约不变**。
4. `backend/scripts/seed_job_hunt.py`：`Career.target_role` 与 notes 改 v3.0 口径；项目 goal/description 同步。

## 验证（重跑种子 + 只读探针）

- `plan_days` = 30，`RLHF` 已不在 `D_LEVEL_FORBIDDEN`。
- Day22 = Mini Post-Training Lab / Day23 = DPO / 偏好优化 + GRPO。
- `Career.target_role` = "大模型后训练 / Post-Training 算法工程师（主攻）"。
- Skill 表 DPO/RLHF/GRPO 均 level=1（`calibrate_skills` 已对齐入库）。

## 关键提醒（防虚构）

RAG / 文档解析 / 合规 / badcase 经验是**应用层**能力，可「重新解释」为后训练的
数据质量 / 评测 / failure-analysis 视角，但**不能写成做过后训练**。
Mini Post-Training Lab 是补真实后训练证据的唯一路径——先把 `03_dpo` 真训一轮，再写进简历。

## 权重变化（对比 v2.0）

- Post-Training 显性成为最大投入块（SFT / LoRA / QLoRA / DPO / GRPO 全进主线）。
- VLM 从「卡位 hedge」降级为「Post-Training 的模型分支」，不再独立成线。
- AI Infra 不单开赛道（`ai-algo` 已含 Inference Optimization；Megatron/DeepSpeed 对 4060Ti 不现实，留 on-job）。
- 具身（VLA / ROS2 / Robot Learning）维持 frozen：30 天不投，on-job 后转。

## 既有分析文档状态

`docs/候选人背景分析-2026-09-17.md`、`docs/具身智能切入点分析-2026-09-17.md`、
`docs/具身智能在职转型路线图-2026-09-17.md` 仍为 v2.0（LLM+VLM）口径，
需按 v3.0 重写「主线 = Post-Training」一节；本文档为 v3.0 权威记录。
