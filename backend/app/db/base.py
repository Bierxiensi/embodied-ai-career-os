"""数据库基础设施。

提供：
- engine：SQLAlchemy 引擎（按 DATABASE_URL 创建，SQLite/PostgreSQL 兼容）
- SessionLocal：会话工厂
- Base：所有模型的声明基类
- get_db：FastAPI 依赖，注入数据库会话
- init_db：启动时建表 + 首次启动插入种子数据
"""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def _is_sqlite(url: str) -> bool:
    """判断是否为 SQLite 连接。"""
    return url.startswith("sqlite")


def _build_engine() -> Engine:
    """构建引擎。

    SQLite：开启外键约束 + check_same_thread=False（多线程）。
    PostgreSQL：标准连接，无额外参数。
    """
    connect_args: dict = {}

    if _is_sqlite(settings.database_url):
        connect_args = {"check_same_thread": False}

    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        echo=False,
    )

    # SQLite 显式开启外键约束
    if _is_sqlite(settings.database_url):

        @event.listens_for(engine, "connect")
        def _enable_sqlite_fk(dbapi_conn, _):  # noqa: ANN001
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的声明基类。"""

    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：注入数据库会话，请求结束自动关闭。"""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """启动时建表 + 首次启动插入种子数据。

    开发态用 create_all；生产环境或需要迁移历史时改用 Alembic。
    种子数据源自 docs/MY_CONTEXT.md 真实自评，确保前端不空。
    """

    # SQLite 文件型数据库需保证 data 目录存在
    # 注意：不能用 replace("sqlite:///./", "") —— 该写法只覆盖相对路径形式，
    # 遇到 DATABASE_URL=sqlite:///D:/xxx/data/test.db（测试隔离常用）时会解析出
    # "sqlite:///D:/..." 这样的非法目录，Windows 直接 WinError 123。
    if _is_sqlite(settings.database_url):
        db_path = settings.database_url.split("sqlite:///", 1)[-1]
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    # 导入模型，确保 Base.metadata 感知所有表
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # 首次启动插入种子数据（表为空时）
    _seed_if_empty()

    # 职业阶段模式：定义以 app/services/career_mode/presets.py 为单一来源，
    # 每次启动对齐一次。与上面"仅空表播种"不同 —— 模式定义会随配置演进，
    # 需要对已存在的行做校正；is_current 不受影响，用户切换后的选择保持不变。
    _sync_career_modes()


def _sync_career_modes() -> None:
    """把职业阶段模式的预置定义物化到库（幂等）。

    仅做"连接管理 + 委托"，判定逻辑全在 services/career_mode/service.py，
    以免基础设施层成为业务规则的第二个实现点。
    """

    from app.services.career_mode.service import sync_career_modes

    db = SessionLocal()
    try:
        sync_career_modes(db)
    finally:
        db.close()


def _seed_if_empty() -> None:
    """表为空时插入种子数据。基于 docs/MY_CONTEXT.md 真实自评。"""

    from app.models.career import Career
    from app.models.interview_log import InterviewLog
    from app.models.interview_question import InterviewQuestion
    from app.models.job_match import JobMatch
    from app.models.job_posting import JobPosting
    from app.models.milestone import Milestone
    from app.models.project import Project
    from app.models.resume_fact import ResumeFact
    from app.models.resume_version import ResumeVersion
    from app.models.skill import Skill
    from app.models.task import Task

    db = SessionLocal()
    try:
        # Career 种子（求职口径：与 scripts/seed_job_hunt.py 保持一致）
        if db.query(Career).count() == 0:
            db.add(
                Career(
                    target_role="Robot AI Engineer（具身/机器人方向）",
                    salary_target=40000,
                    timeframe="2026-10-31",
                    notes="主攻具身/VLA，折中机器人软件 ROS2+AI，保底 Agent 应用",
                )
            )

        # Skill 种子：单一数据源 app/core/skill_profile.py
        # 改等级只改 skill_profile.py，不要在这里改副本
        if db.query(Skill).count() == 0:
            from app.core.skill_profile import SKILL_PROFILE

            for p in SKILL_PROFILE:
                db.add(
                    Skill(
                        name=p.name,
                        category=p.category,
                        level=p.level,
                        target_level=p.target_level,
                        evidence=list(p.evidence),
                    )
                )

        # Task 种子：3 项（source="seed" 便于与用户/测试数据区分，见 migrations/0007）
        if db.query(Task).count() == 0:
            seed_tasks = [
                Task(
                    title="ROS2 Topic 通信机制",
                    objective="掌握 publisher/subscriber 通信，写出可运行 demo",
                    duration=40, difficulty="beginner", status="doing",
                    skill_name="ROS2",
                    acceptance=["创建 publisher 节点发布字符串",
                                "创建 subscriber 节点接收消息",
                                "Git 提交可运行的 demo"],
                    source="seed",
                ),
                Task(
                    title="SO101 ACT 模型泛化调试",
                    objective="采集新数据重训 ACT，对比泛化成功率",
                    duration=30, difficulty="intermediate", status="todo",
                    skill_name="Robot Learning",
                    acceptance=["采集 20+ episodes 新数据",
                                "训练新模型并对比成功率",
                                "记录泛化效果到 LearningLog"],
                    source="seed",
                ),
                Task(
                    title="Career OS Day2 数据库层",
                    objective="完成 4 张表模型定义与健康检查端点",
                    duration=25, difficulty="beginner", status="done",
                    skill_name="Python",
                    acceptance=["完成 4 张表模型定义",
                                "/health/db 返回 ok",
                                "表结构验证通过"],
                    source="seed",
                ),
            ]
            for t in seed_tasks:
                db.add(t)

        # V2 Project 种子
        if db.query(Project).count() == 0:
            p = Project(
                name="SO101 Embodied AI System",
                goal="打造 ROS2 + VLA 驱动的具身智能真机闭环系统",
                description="从 Python 控制 → ROS2 → MoveIt2 → ACT → SmolVLA → Isaac Lab → Sim2Real",
                status="active",
                current_version="V0",
                sort_order=0,
                source="seed",
            )
            db.add(p)
            db.flush()

            seed_milestones = [
                Milestone(project_id=p.id, version="V0", title="Mujoco 仿真控制",
                          goal="Mujoco 仿真机械臂：Python 控制 3-DOF 臂关节角度 → FK 验证 → 轨迹记录",
                          status="locked", sort_order=0, source="seed"),
                Milestone(project_id=p.id, version="V1", title="ROS2 基础控制",
                          goal="通过 ROS2 topic 控制 SO101 关节", status="locked", sort_order=1,
                          source="seed"),
                Milestone(project_id=p.id, version="V2", title="MoveIt2 集成",
                          goal="MoveIt2 运动规划 + 执行", status="locked", sort_order=2,
                          source="seed"),
                Milestone(project_id=p.id, version="V3", title="ACT 模仿学习",
                          goal="ACT 训练 + 泛化实验", status="locked", sort_order=3,
                          source="seed"),
                Milestone(project_id=p.id, version="V4", title="SmolVLA 接入",
                          goal="SmolVLA 推理 + 真机测试", status="locked", sort_order=4,
                          source="seed"),
                Milestone(project_id=p.id, version="V5", title="Isaac Lab 仿真",
                          goal="仿真环境搭建 + 合成数据生成", status="locked", sort_order=5,
                          source="seed"),
                Milestone(project_id=p.id, version="V6", title="Sim2Real 闭环",
                          goal="仿真训练 → 真机部署 → 评估完整闭环", status="locked", sort_order=6,
                          source="seed"),
            ]
            for m in seed_milestones:
                db.add(m)

        # 岗位池种子（Batch 1）：4 条跨赛道样例 JD，首次启动即填满岗位池
        if db.query(JobPosting).count() == 0:
            from app.agents.match.engine import JDParser, MatchEngine

            skill_levels = {s.name.strip().lower(): s.level for s in db.query(Skill).all()}

            sample_postings = [
                JobPosting(
                    company="某头部 AI 公司",
                    title="大模型算法工程师（LLM 训练/对齐）",
                    city="北京",
                    salary_range="36-45K",
                    tier=1,
                    track="llm",
                    source="内推",
                    education="硕士",
                    min_years=3,
                    paper_required=False,
                    jd_text=(
                        "职责：负责大语言模型的预训练与指令微调（SFT），优化 Attention / "
                        "Transformer 结构，落地 LoRA/QLoRA 高效微调。要求精通 PyTorch、"
                        "Python、深度学习，熟悉 KV Cache 与推理加速。有大模型训练经验优先。"
                    ),
                    required_skills=["Transformer", "Attention", "SFT", "LoRA/QLoRA", "PyTorch", "Python", "Deep Learning"],
                ),
                JobPosting(
                    company="某 AI 实验室",
                    title="多模态 / VLM 算法工程师",
                    city="上海",
                    salary_range="36-45K",
                    tier=2,
                    track="vlm",
                    source="猎聘",
                    education="硕士",
                    min_years=2,
                    paper_required=False,
                    jd_text=(
                        "职责：研发视觉语言模型（VLM），基于 ViT / CLIP 做多模态对齐，"
                        "使用 LoRA 微调多模态大模型。要求熟悉 PyTorch、Python、深度学习，"
                        "理解视觉 token 与语言空间差异。"
                    ),
                    required_skills=["ViT", "CLIP", "Multimodal Alignment", "VLM", "LoRA/QLoRA", "PyTorch", "Python"],
                ),
                JobPosting(
                    company="某云厂商",
                    title="AI 算法 / 推理优化工程师",
                    city="杭州",
                    salary_range="30-40K",
                    tier=3,
                    track="ai-algo",
                    source="Boss直聘",
                    education="本科",
                    min_years=3,
                    paper_required=False,
                    jd_text=(
                        "职责：负责模型推理优化与服务化部署，优化推理时延与吞吐。要求熟练 "
                        "Python、深度学习、PyTorch，熟悉 Linux 环境与推理加速（vLLM / TensorRT）。"
                    ),
                    required_skills=["Python", "Deep Learning", "PyTorch", "Inference Optimization", "Linux"],
                ),
                JobPosting(
                    company="某机器人公司",
                    title="具身智能 / VLA 算法工程师",
                    city="深圳",
                    salary_range="36-45K",
                    tier=2,
                    track="embodied",
                    source="官网",
                    education="硕士",
                    min_years=2,
                    paper_required=False,
                    jd_text=(
                        "职责：研发 VLA 具身智能模型，基于 ROS2 与 Isaac 仿真做 Robot Learning，"
                        "推进 Sim2Real。要求熟悉 PyTorch、Python、机器人学基础。"
                    ),
                    required_skills=["ROS2", "VLA", "Robot Learning", "PyTorch", "Isaac"],
                ),
            ]
            for p in sample_postings:
                p.dedup_key = f"{p.company.strip().lower()}::{p.title.strip().lower()}"
                if not p.required_skills and p.jd_text:
                    p.required_skills = JDParser.parse_required_skills(p.jd_text)
                db.add(p)
                db.flush()
                # 录入即匹配（纯规则）
                res = MatchEngine.compute(
                    required_skills=p.required_skills or [],
                    track=p.track,
                    education=p.education,
                    min_years=p.min_years,
                    paper_required=p.paper_required,
                    skill_levels=skill_levels,
                )
                db.add(JobMatch(
                    posting_id=p.id,
                    match_score=res.match_score,
                    grade=res.grade,
                    dimension_scores=res.dimension_scores,
                    gaps=res.gaps,
                    matched_track=res.matched_track,
                ))

        # 简历事实锚点库种子（Batch 2）：真实可陈述事实，源自 docs/MY_CONTEXT.md
        # 防虚构依据的唯一权威来源；首次启动即填满，便于直接看诊断效果。
        if db.query(ResumeFact).count() == 0:
            seed_facts = [
                ResumeFact(
                    category="work",
                    title="东鉴科技 · 文档智能/招投标 Agent",
                    org="北京东鉴科技",
                    start="2026.01",
                    end="2026.09",
                    facts=[
                        "标书审核 Agent 覆盖率 56%→90%",
                        "单份标书处理 30min→10min",
                        "累计处理 3000+ 份标书",
                        "研发协同平台支撑 30+ 人",
                        "交付周期缩短 200%",
                    ],
                    source="工作自评",
                ),
                ResumeFact(
                    category="project",
                    title="科研知识库问答系统",
                    org=None,
                    start=None,
                    end=None,
                    facts=[
                        "Top-5 准确率 56%→78%",
                        "结构化召回 85%",
                    ],
                    source="项目复盘",
                ),
                ResumeFact(
                    category="project",
                    title="油耗 SaaS 预测服务",
                    org=None,
                    start=None,
                    end=None,
                    facts=[
                        "MAPE < 1%",
                        "接入 1000+ 台设备",
                    ],
                    source="项目复盘",
                ),
                ResumeFact(
                    category="paper",
                    title="STM-SHAP 论文",
                    org="IEEE ISCTIS 2026",
                    start=None,
                    end=None,
                    facts=[
                        "EI 一作论文 STM-SHAP",
                        "NSE/RMSE 提升 13%",
                        "DOI 10.1109/ISCTIS70043.2026.11572181",
                    ],
                    source="学术成果",
                ),
                ResumeFact(
                    category="paper",
                    title="学位论文 RL-RA-QR 洪水概率预报",
                    org=None,
                    start=None,
                    end=None,
                    facts=["RL-RA-QR 洪水概率预报（在研）"],
                    source="学术成果",
                ),
                ResumeFact(
                    category="edu",
                    title="北航软件工程硕士（非全在读）",
                    org="北京航空航天大学",
                    start="2023.09",
                    end="2026.12",
                    facts=["软件工程 硕士", "北航 非全日制在读"],
                    source="学历",
                ),
                ResumeFact(
                    category="edu",
                    title="郑州航院计算机科学本科",
                    org="郑州航空航天大学",
                    start="2015.09",
                    end="2019.07",
                    facts=["计算机科学与技术 本科"],
                    source="学历",
                ),
                ResumeFact(
                    category="metric",
                    title="技术栈自评",
                    org=None,
                    start=None,
                    end=None,
                    facts=[
                        "Python",
                        "PyTorch",
                        "Deep Learning",
                        "Linux",
                        "Agent Application",
                        "多 Agent 编排",
                        "React",
                        "Vue",
                    ],
                    source="技能画像",
                ),
                ResumeFact(
                    category="project",
                    title="SO101 具身机械臂",
                    org=None,
                    start=None,
                    end=None,
                    facts=[
                        "SO101 机械臂已组装、舵机可用",
                        "遥操作可用、采集 20 episodes",
                        "ACT 训练完成、推理可用",
                    ],
                    source="硬件项目",
                ),
            ]
            db.add_all(seed_facts)

        # 示例简历版本种子（Batch 2）：主版本，内容多为真实可锚定 + 2 条演示性虚构（标红）
        if db.query(ResumeVersion).count() == 0:
            sample_md = (
                "## 工作经历\n"
                "- 北京东鉴科技 算法工程师（2026.01-2026.09）：负责文档智能与招投标方向，"
                "主导标书审核 Agent，覆盖率 56%→90%，单份处理 30min→10min，累计处理 3000+ 份\n"
                "- 研发协同平台支撑 30+ 人，交付周期缩短 200%\n\n"
                "## 项目经历\n"
                "- 科研知识库问答系统：Top-5 准确率 56%→78%，结构化召回 85%\n"
                "- 油耗 SaaS 预测服务：MAPE < 1%，接入 1000+ 台设备\n"
                "- SO101 具身机械臂：已组装、遥操作可用、采集 20 episodes、ACT 训练完成\n\n"
                "## 学术成果\n"
                "- EI 一作论文 STM-SHAP（IEEE ISCTIS 2026），NSE/RMSE 提升 13%\n\n"
                "## 教育背景\n"
                "- 北京航空航天大学 软件工程 硕士（非全在读，2023-至今）\n"
                "- 郑州航空航天大学 计算机科学与技术 本科（2015-2019）\n\n"
                "## 技能\n"
                "- 熟练 Python、PyTorch，具备 Agent Application 多 Agent 编排经验\n"
                "- 前端 React/Vue 企业级项目\n"
                "- 熟悉 Linux 训练与部署环境\n\n"
                "## 自我评价\n"
                "- 精通 CUDA 内核优化与算子开发（演示：无锚点，应标红）\n"
                "- 主导过千万级 DAU 的推荐系统（演示：无锚点，应标红）\n"
            )
            db.add(ResumeVersion(
                name="LLM 主攻版（示例）",
                content_md=sample_md,
                target_tier=1,
                is_primary=True,
            ))

        # 面试题库种子（Batch 3）：LLM/VLM/Project/Coding 共 15 题，支撑模拟抽题
        if db.query(InterviewQuestion).count() == 0:
            seed_questions = [
                # LLM
                InterviewQuestion(category="LLM", difficulty="intermediate",
                    question="Transformer 中 Self-Attention 的计算复杂度是多少？有哪些优化手段？",
                    answer_outline="O(n²·d)：QK^T 与 softmax 均为 n² 级别。优化：FlashAttention（IO 感知、分块）、稀疏/线性注意力、KV Cache 复用、GQA/MQA 降 KV 头数。",
                    source="自编"),
                InterviewQuestion(category="LLM", difficulty="intermediate",
                    question="LoRA 与 QLoRA 的区别是什么？什么场景选哪个？",
                    answer_outline="LoRA 冻结原权重、注入低秩 A/B 矩阵；QLoRA 先把基座 4bit 量化再挂 LoRA，显存更省但略慢。显存受限选 QLoRA，追求训练速度/精度选 LoRA。",
                    source="自编"),
                InterviewQuestion(category="LLM", difficulty="intermediate",
                    question="KV Cache 是什么？它如何影响推理显存与吞吐？",
                    answer_outline="缓存已生成 token 的 K/V，避免重复计算，把 decode 从 O(n²) 降到 O(n)。显存随 batch×seq×层数×头数×d 线性增长；可用 GQA、PagedAttention、量化压缩。",
                    source="面经"),
                InterviewQuestion(category="LLM", difficulty="intermediate",
                    question="SFT 与 DPO 的训练目标有什么区别？",
                    answer_outline="SFT 是监督式最大似然（对齐格式/指令跟随）；DPO 用偏好对直接优化策略，绕过奖励模型，目标是提高 chosen 相对 rejected 的对数似然比。",
                    source="自编"),
                InterviewQuestion(category="LLM", difficulty="advanced",
                    question="MoE 的参数激活机制是怎样的？为什么能降低推理成本？",
                    answer_outline="每 token 经 Router 只激活 top-k 专家，总参数大但激活参数少；计算量按激活参数算，故单位 token 成本低，但显存仍要放下全部专家权重。",
                    source="自编"),
                InterviewQuestion(category="LLM", difficulty="beginner",
                    question="RMSNorm 与 LayerNorm 的区别？为什么大模型偏爱 RMSNorm？",
                    answer_outline="LayerNorm 减均值除标准差并做仿射；RMSNorm 不减均值，仅按均方根缩放。少一次均值计算、更快，且效果相当，故主流 LLM 采用。",
                    source="自编"),
                # Multimodal
                InterviewQuestion(category="Multimodal", difficulty="intermediate",
                    question="CLIP 的对比学习目标是什么？为什么能做 zero-shot 分类？",
                    answer_outline="图文对 batch 内做 InfoNCE，拉近匹配对、推远非匹配对，对齐图像/文本到同一空间；zero-shot 时用类名文本 embedding 与图像 embedding 比相似度。",
                    source="自编"),
                InterviewQuestion(category="Multimodal", difficulty="beginner",
                    question="ViT 相比 CNN 的优势与劣势？",
                    answer_outline="优势：全局注意力、可扩展性强、大数据下更强；劣势：缺乏局部归纳偏置，小数据易过拟合，计算量随 patch 数平方增长。",
                    source="自编"),
                InterviewQuestion(category="Multimodal", difficulty="advanced",
                    question="LLaVA 是如何把视觉特征对齐到语言空间的？",
                    answer_outline="ViT 提视觉特征 → 投影层（MLP/Q-Former）映射为视觉 token → 与文本 token 拼接入 LLM；两阶段训练：先冻结 LLM 对齐投影，再指令微调。",
                    source="自编"),
                InterviewQuestion(category="Multimodal", difficulty="advanced",
                    question="多模态训练中视觉 token 与文本 token 如何拼接与对齐？",
                    answer_outline="按占位符（如 <image>）位置替换为视觉 token，统一进 LLM 序列；对齐靠对比学习/投影层/Q-Former 压缩，并注意 token 数量与位置编码处理。",
                    source="自编"),
                # Project
                InterviewQuestion(category="Project", difficulty="intermediate",
                    question="讲讲你做的标书审核 Agent：覆盖率怎么从 56% 提到 90%？",
                    answer_outline="拆解审查项 → 规则+LLM 混合抽取 → 多轮检索补全关键字段 → 加入人工标注集评估迭代；弱项（签字盖章/身份证/业绩）针对性召回改进。",
                    source="项目"),
                InterviewQuestion(category="Project", difficulty="intermediate",
                    question="科研知识库的召回是怎么优化的？Top-5 从 56% 到 78% 做了什么？",
                    answer_outline="切块策略（语义+结构）→ 混合检索（BM25+向量）→ rerank → 结构化召回补强；用 Top-5 命中率做指标闭环。",
                    source="项目"),
                InterviewQuestion(category="Project", difficulty="intermediate",
                    question="STM-SHAP 论文的核心创新点是什么？SHAP 在这里解决什么问题？",
                    answer_outline="用 SHAP 量化冗余/滞后特征对洪水预报的贡献，指导特征筛选；结合时空建模，NSE/RMSE 提升约 13%。",
                    source="论文"),
                # Coding
                InterviewQuestion(category="Coding", difficulty="advanced",
                    question="手写一个 Multi-Head Attention（PyTorch）。",
                    answer_outline="Q/K/V 线性投影 → reshape 成多头 → scaled dot-product（含 mask）→ concat → 输出投影；注意维度 (B, H, N, d_head) 与 softmax 缩放 1/sqrt(d)。",
                    source="自编"),
                InterviewQuestion(category="Coding", difficulty="intermediate",
                    question="实现一个 LRU Cache。",
                    answer_outline="HashMap + 双向链表，get/put O(1)；或 Python 直接用 OrderedDict / functools.lru_cache 说明底层。",
                    source="自编"),
            ]
            db.add_all(seed_questions)

        # 示例面经种子（Batch 3）：一条真实感面经，便于直接看弱项统计与回写任务
        if db.query(InterviewLog).count() == 0:
            from datetime import date

            db.add(InterviewLog(
                company="某头部 AI 公司",
                role="大模型算法工程师",
                round="一面",
                asked_questions=[
                    "Self-Attention 计算复杂度与优化",
                    "LoRA 与 QLoRA 的区别",
                    "KV Cache 显存如何估算",
                    "项目：标书审核 Agent 的指标与做法",
                ],
                weak_questions=[
                    "KV Cache 显存估算",
                    "LoRA 与 QLoRA 的取舍",
                    "FlashAttention 原理",
                ],
                jd_gaps=["分布式训练 FSDP/ZeRO"],
                knowledge_gaps=["vLLM PagedAttention"],
                next_actions=["补 KV Cache 显存计算", "复盘 LoRA vs QLoRA 选型"],
                interviewed_at=date(2026, 9, 8),
                notes="整体偏紧，推理侧细节答得不好；项目讲得比较顺。",
                generated_task_ids=[],
            ))

        db.commit()
    finally:
        db.close()
