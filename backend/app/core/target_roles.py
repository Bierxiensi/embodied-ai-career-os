"""目标岗位画像配置。

求职看板的核心输入：把"我要找工作"拆成几条可执行的赛道。
每条赛道声明硬性要求技能，系统据此计算匹配度与缺口。

按自己的投递策略直接改这个文件即可，无需改代码逻辑。

================================================================================
2026-09-10 战略调整（增量，非重写）
================================================================================
依据《求职 Agent 开发与运行规范 v2.0》：主线从「具身智能」切换为
「LLM 深度为主 + Multimodal/VLM 轻量卡位」，具身转为长期观察。

处理原则：**旧内容降权保留，不删除**。
- 新增 llm（主攻）/ vlm（卡位）/ ai-algo（保底）三条赛道
- embodied 赛道保留，标记 frozen=True —— 仍然计算匹配度、仍然展示，
  只是不再进入"技能缺口"的推动列表（其技能 target=level，gap 恒为 0），
  不再占用学习时间
- 历史投递记录的 track=embodied 数据不受影响

这样具身方向的已有积累（SO101、ROS2 demo、Mujoco 控制）仍是简历里的
工程能力旁证，但不会被系统当成"今天的待办"推给你。

================================================================================
2026-09-18 战略再调整 v3.0（主线收敛为 Post-Training）
================================================================================
依据岗位面现状与本人底牌（RAG/文档解析/合规 badcase = 后训练的数据与评测能力），
主轴由「LLM+VLM」收敛为 **Post-Training / 大模型后训练**：
- llm 赛道改名「大模型后训练 / Post-Training 算法工程师」（主攻），
  要求技能补 DPO / RLHF / GRPO（偏好优化与强化学习后训练）
- vlm 降级为「模型方向」：Post-Training 内的多模态分支，不再独立成 hedge
- ai-algo（保底）不变，承载 AI Infra / Inference 增强
- embodied 维持 frozen（VLA / Robot Learning 是 on-job 长期目标，不是 30 天内容）
- 贯穿式项目由 Mini-VLM 升级为 **Mini Post-Training Lab**（SFT→LoRA→DPO→Eval→Badcase→VLM SFT→Inference）
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TargetRole:
    """一个目标岗位画像。"""

    key: str                      # 标识：llm / vlm / ai-algo / embodied
    name: str                     # 岗位名称
    priority: str                 # 主攻 / 卡位 / 保底 / 暂缓
    salary_range: str             # 期望薪资区间
    note: str                     # 策略说明
    required_skills: list[str] = field(default_factory=list)   # 硬性要求技能
    required_level: int = 4       # 每项技能的要求等级（0-5）
    frozen: bool = False          # 冻结：不投入新时间，看板不再推动其技能缺口


# 四条赛道（按优先级排列）：
# 1. llm      —— 主攻，30 天冲刺的核心盘
# 2. vlm      —— 卡位，差异化 + 长期方向（Multimodal Foundation Model）
# 3. ai-algo  —— 保底，进入模型团队的入口岗
# 4. embodied —— 暂缓（frozen），长期观察，保留已有资产但不投入时间
#
# ================================================================================
# 2026-09-20 战略校准 v3.1（在职转型，非重写）
# ================================================================================
# 用户确认留在现公司（北航非全在读 + 在职转型窗口 2026.09–2027.03），战略基线由
# job_hunt 切到 long_term_transition（激活机制见 services/career_mode/{presets,service}.py）。
#
# 关于 phd 赛道：long_term_transition 的 active_track_keys 已声明 phd，但本文件
# **暂不**新增 phd 为 TargetRole。理由：
#   1. 博士就绪度是"研究匹配"（导师 / 方向 / 论文 / 院校），不是技能匹配；提前进
#      TARGET_ROLES 会让 /api/job-hunt 用 required_skills 算一张误导性的
#      "博士申请 技能匹配度"卡片。
#   2. 博士模块的六维匹配（Phase 1）会自带模型与 API，那时再正式建模 phd 赛道。
# 因此 phd 在 Phase 0 只是 long_term 的一个"占位生效赛道"，不参与技能匹配计算；
# 它也不出现在 job_hunt 的派生赛道里（job_hunt 仍严格由本文件的 frozen 标记派生）。
#
# ================================================================================
# 2026-09-21 口径校准 v3.2（双轨匹配分 + 内核突击收口，docs/项目梳理与迭代指导-2026-09-21.md）
# ================================================================================
# 用户三项裁决：
# 1. 确认留任 → long_term_transition 激活（presets.py v3.1 已定义，本文件无需新增 phd 赛道）。
# 2. 匹配分双轨制：match_pct（推进度）继续展示，新增 strict 达标率
#    （level >= required_level 的技能占比，见 api/job_hunt.py roles_out.strict_pct）。
#    llm 赛道补 RAG / Agent Application —— 本人 level 4 的两项最强技能此前被排除在
#    匹配计算外，导致分数系统性虚高（看板 82-89 分 vs 严格达标 13-20%）。
# 3. 内核层 24 项不全铺：只突击 6 个最高频考点到 level 3（够答"是什么/为什么"）：
#    KV Cache / FlashAttention / PagedAttention / FSDP-ZeRO / Quantization / MoE，
#    与 Mini Post-Training Lab 实验绑定；其余维持 level 1-2，本窗口不投入。
TARGET_ROLES: list[TargetRole] = [
    TargetRole(
        key="llm",
        name="大模型后训练 / Post-Training 算法工程师",
        priority="主攻",
        salary_range="36-45K",
        note="v3.2：Post-Training 横向能力（SFT→DPO→RL），VLM 是其模型分支；"
             "Transformer→SFT→LoRA/QLoRA→DPO/GRPO→Eval 必须能讲透并做过实验；"
             "补 RAG/Agent Application（真实 JD 要求且是本人强项，见 v3.2 注记）",
        required_skills=[
            "Transformer", "Attention", "Pretraining", "SFT",
            "LoRA/QLoRA", "DPO", "RLHF", "GRPO",
            "PyTorch", "Python", "Deep Learning",
            "RAG", "Agent Application",
        ],
        required_level=4,
    ),
    TargetRole(
        key="vlm",
        name="多模态 / VLM（Post-Training 模型方向）",
        priority="卡位",
        salary_range="36-45K",
        note="v3.0 改为模型方向：VLM 是 Post-Training 的多模态分支，不是独立 hedge；"
             "ViT / CLIP / 对齐 / Projector 讲清楚，配 Mini Post-Training Lab 的 VLM SFT 子实验",
        required_skills=[
            "ViT", "Multimodal Alignment", "VLM",
            "LoRA/QLoRA", "DPO", "PyTorch", "Python",
        ],
        required_level=4,
    ),
    TargetRole(
        key="ai-algo",
        name="AI 算法 / 推理工程师",
        priority="保底",
        salary_range="30-40K",
        note="进入模型团队的入口岗：推理优化与工程交付是现有强项，可快速拿面试",
        required_skills=[
            "Python", "Deep Learning", "PyTorch",
            "Inference Optimization", "Linux",
        ],
        required_level=4,
    ),
    TargetRole(
        key="embodied",
        name="具身智能 / VLA 算法工程师",
        priority="暂缓",
        salary_range="36-45K",
        note="长期观察（v2.0 D 级：30 天内主动不深挖）。已有 SO101 / ROS2 资产转为工程能力旁证，不投入新时间",
        required_skills=["ROS2", "VLA", "Robot Learning", "PyTorch", "Isaac", "Sim2Real"],
        required_level=4,
        frozen=True,
    ),
]

# 求职项目标识（seed 脚本与 API 共用，保证幂等匹配）
JOB_HUNT_PROJECT_NAME = "求职冲刺 · 2026 Q4"

# offer 目标日期兜底值（Career.timeframe 无法解析时使用）
DEFAULT_OFFER_DEADLINE = "2026-10-31"

# 30 天冲刺窗口（v2.0 §核心时间节点）
SPRINT_START = "2026-09-10"
SPRINT_END = "2026-10-09"

# D 级技术黑名单：v2.0 §19 明令 30 天内不投入。
# Planner 生成学习任务时命中这里应直接拒绝并提示，防止路线发散。
TECH_BLACKLIST: list[str] = [
    "ROS2", "VLA", "Robot Learning", "Isaac", "Sim2Real",
    "MoveIt2", "Mujoco Simulation", "SO101",
    "World Model", "3D VLM", "Video LLM", "Multimodal RL",
]
