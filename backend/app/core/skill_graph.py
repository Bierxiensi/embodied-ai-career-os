"""技能依赖图的**种子真源**（Phase 3）。

本模块只定义"谁是谁的先修"这一件事，不读写库、不依赖 FastAPI，
可被种子脚本、服务层与测试同时引用（与 core/skill_profile.py 同款约定）。

================================================================================
这一层解决什么问题
================================================================================
在此之前，技能画像是一张平表：平台能算出"哪项技能缺口最大"，
但回答不了"我该先学哪一个"。缺口 4 分的 RoPE 与缺口 4 分的 Quantization
在排序上完全等价，而实际上前者的先修是 Attention（已到 3 分）、
后者没有硬先修 —— 学习成本差一个量级。

依赖图把"缺口排序"变成"**可执行的缺口排序**"：
    先修未满足的技能先别推，先补先修（否则学了也是空中楼阁）。

================================================================================
边的语义与纪律
================================================================================
- 有向边 ``prerequisite -> dependent``：必须先掌握前者，后者才学得动。
- 只允许引用 **SKILL_PROFILE 里的规范技能名**（大小写敏感，与 skills.name 一致）。
  拼错不会被库拦住（端点是名字不是外键），因此由 tests/test_skill_graph.py
  断言每条边的两端都真的存在、且全图无环。
- 依赖是**知识结构**，不是任务顺序：它不承诺"学完 A 就必然能学 B"，
  只声明"A 完全不会时，先别碰 B"。

⚠️ 改这个文件后必须重跑 ``python scripts/seed_skill_graph.py`` 才会进库，
   两者是"种子源 → 数据库"的单向关系，库里的边不会被反向写回这里。
"""

from __future__ import annotations

from app.core.skill_profile import profile_map

# 先修被视为"已具备"的最低等级。
#
# 取 3（= 独立做过项目）而不是拿到 target_level：
#   先修的作用是"判断现在能不能学得动"，不是"是否已精通"。
#   等级 3 意味着"独立实现过"，足以支撑后续技能；要求先修也达到 target
#   会让整条链永远卡在第一步（例如 Transformer target=5，而 Attention 的先修
#   是 Transformer —— 若要求 5 则 Attention 永远解锁不了）。
PREREQ_SATISFIED_LEVEL = 3

# (prerequisite, dependent, note)
# note 写"为什么必须先学它"，仅用于展示与评审，不参与任何计算，可为 None。
SKILL_EDGES: tuple[tuple[str, str, str | None], ...] = (
    # ---------- 地基：语言 / 框架 ----------
    ("Python", "PyTorch", "PyTorch 的建模脚本、DataLoader、分布式启动都是 Python 语法层的事"),
    ("Python", "FastAPI", "服务化交付的前提"),
    ("Deep Learning", "PyTorch", "先有反向传播 / 优化器 / 正则化的概念，框架的 API 才有意义"),
    ("PyTorch", "Transformer", "手搓 MHA 需要 nn.Module / 自动求导 / 张量广播"),
    # ---------- LLM 基础：结构 ----------
    ("Transformer", "Attention", "QKV / scaled dot-product 是 Transformer 的内核"),
    ("Attention", "RoPE", "旋转位置编码作用在 Q/K 上，不理解注意力就推不动旋转矩阵"),
    ("Attention", "FlashAttention", "IO-aware 优化改的正是注意力分块的访存"),
    ("Attention", "KV Cache", "缓存的就是每层注意力算出的 K/V"),
    ("Transformer", "RMSNorm", "归一化的位置与作用要在完整结构里才讲得通"),
    ("Transformer", "SwiGLU", "FFN 变体，替换的是 Transformer 块里的前馈层"),
    ("Transformer", "ViT", "ViT 就是 patch 化的 Transformer Encoder"),
    # ---------- LLM 基础：训练 ----------
    ("Transformer", "Pretraining", "预训练目标（causal LM）建立在结构之上"),
    ("Pretraining", "SFT", "先知道基座怎么来的，才知道后训练在改什么"),
    ("Pretraining", "Distributed Training", "并行策略是为了把预训练放得下、跑得动"),
    ("Pretraining", "Gradient Checkpointing", "显存优化的动机来自预训练的真实显存预算"),
    ("Pretraining", "MoE", "稀疏专家是预训练阶段的架构选择"),
    ("Distributed Training", "FSDP/ZeRO", "ZeRO 是数据并行的显存切分方案，属同一层问题"),
    ("Distributed Training", "Gradient Checkpointing", "两条显存优化路线配合使用"),
    # ---------- 微调对齐 ----------
    ("SFT", "LoRA/QLoRA", "参数高效微调是对全参微调的成本替代，先有全参概念"),
    ("SFT", "DPO", "DPO 用偏好数据替换了 SFT 之后的 RL 阶段"),
    ("DPO", "RLHF", "理解 DPO 用偏好数据省掉了 reward model，才知道 RLHF 原本在做什么"),
    ("RLHF", "GRPO", "GRPO 是 RL 对齐里去掉 critic 的变体"),
    # ---------- 推理工程 ----------
    ("KV Cache", "Prefill/Decode", "两阶段时延拆解的核心变量就是 KV Cache 的读写"),
    ("KV Cache", "vLLM", "PagedAttention 管的正是 KV Cache 的显存碎片"),
    ("FlashAttention", "vLLM", "serving 性能前提之一是注意力内核足够快"),
    ("Quantization", "vLLM", "量化权重是 serving 显存预算的另一半"),
    ("vLLM", "Inference Optimization", "有真实 serving 数据，才谈得上优化结论"),
    ("Quantization", "Inference Optimization", "精度-时延权衡是推理优化的一条主线"),
    ("Prefill/Decode", "Inference Optimization", "优化的靶子是 TTFT 还是 TPS 取决于这个拆分"),
    # ---------- 多模态 ----------
    ("ViT", "CLIP", "CLIP 的视觉塔通常是 ViT"),
    ("CLIP", "BLIP", "BLIP 建立在对比学习到的视觉-语言对齐之上"),
    ("CLIP", "LLaVA", "LLaVA 的视觉编码器直接复用 CLIP"),
    ("ViT", "Multimodal Alignment", "对齐的目标空间由视觉编码器给出"),
    ("Multimodal Alignment", "VLM", "对齐是手段，VLM 是把它装进语言模型的结果"),
    ("Multimodal Alignment", "Q-Former", "Q-Former 是用固定数量 query 压缩视觉的一种对齐方案"),
    ("Multimodal Alignment", "Flamingo", "Flamingo 的 cross-attention 是对齐的另一条路线"),
    ("Q-Former", "BLIP", "BLIP-2 的桥接模块就是 Q-Former"),
    ("LLaVA", "VLM", "完整跑通一次 VLM 微调的具体载体"),
    # ---------- 工程交付 ----------
    ("Linux", "Docker", "容器是 Linux 命名空间与 cgroup 的封装"),
    ("Docker", "Web Engineering", "部署与编排属于工程交付的最后一公里"),
    ("Frontend", "Web Engineering", "全栈工程化 = 前端 + 构建 + 部署"),
    ("RAG", "Agent Application", "Agent 的知识底座先要能检索准"),
    ("FastAPI", "Agent Application", "Agent 服务化的接口层"),
    # ---------- 科研底座 ----------
    ("PyTorch", "Time Series Forecasting", "论文里的模型与实验都跑在框架上"),
    ("Deep Learning", "Time Series Forecasting", "时序建模属于深度学习的一个应用分支"),
    ("Time Series Forecasting", "Small-data Forecasting", "小样本是时序建模里最难的一档，先有常规方法"),
    ("Time Series Forecasting", "Explainability", "可解释性分析的对象是已跑通的时序模型"),
    # ---------- 冻结区（具身）：保留知识结构，不在六域雷达里推 ----------
    ("ROS2", "Robot Learning", "机器人学习实验跑在 ROS2 通信之上"),
    ("ROS2", "MoveIt2", "MoveIt2 是 ROS2 生态里的运动规划栈"),
    ("Robot Learning", "VLA", "VLA 是机器人学习的前沿分支"),
    ("VLA", "Sim2Real", "策略迁移的前提是先有一个能跑的 VLA 策略"),
    ("Mujoco Simulation", "Sim2Real", "仿真环境是 sim2real 的起点"),
)


def edge_pairs() -> list[tuple[str, str]]:
    """全部边的 (prerequisite, dependent) 二元组，供种子脚本与去重断言使用。"""
    return [(p, d) for p, d, _ in SKILL_EDGES]


def edges_by_dependent() -> dict[str, list[str]]:
    """dependent -> [prerequisite...]；空列表表示该技能无先修。"""
    out: dict[str, list[str]] = {}
    for prereq, dep, _ in SKILL_EDGES:
        out.setdefault(dep, []).append(prereq)
    return out


def prerequisites_of(skill_name: str) -> list[str]:
    """某技能的全部先修名（大小写敏感，按 SKILL_EDGES 顺序）。"""
    return [p for p, d, _ in SKILL_EDGES if d == skill_name]


def dependents_of(skill_name: str) -> list[str]:
    """学了该技能之后解锁的技能。"""
    return [d for p, d, _ in SKILL_EDGES if p == skill_name]


def unknown_skills() -> list[str]:
    """两端里引用了 SKILL_PROFILE 之外技能名的全部名字（去重，保持顺序）。

    这是**校验**而非运行时过滤：返回非空即说明 SKILL_EDGES 写错了技能名，
    由测试断言必须为空。生产路径不静默丢弃未知边 —— 静默丢弃会让
    "依赖图看起来是好的，其实少了几条"，正是本项目反复踩过的坑。
    """
    known = profile_map()
    bad: list[str] = []
    for prereq, dep, _ in SKILL_EDGES:
        for name in (prereq, dep):
            if name.lower() not in known and name not in bad:
                bad.append(name)
    return bad


def find_cycle() -> list[str] | None:
    """返回一条环（技能名列表）；无环返回 None。

    依赖图一旦有环，"先补先修"的排序会陷入互相等待且不报错 ——
    学习顺序表会静默给出错误答案。因此环是硬错误，由测试拦下。
    """
    graph = {dep: prereqs for dep, prereqs in edges_by_dependent().items()}
    state: dict[str, int] = {}   # 0 未访问 / 1 在栈上 / 2 已完成
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = 1
        stack.append(node)
        for nxt in graph.get(node, []):
            if state.get(nxt) == 1:
                return stack[stack.index(nxt):] + [nxt]
            if state.get(nxt, 0) == 0:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        state[node] = 2
        return None

    for node in list(graph):
        if state.get(node, 0) == 0:
            found = visit(node)
            if found:
                return found
    return None
