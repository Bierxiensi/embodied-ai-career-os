"""面试 Agent（InterviewAgent）包。

设计偏离说明（与 MatchAgent / ResumeAgent 一致）：
    《求职 Agent 设计》把 InterviewAgent 列为 BaseAgent 子类（依赖 LLM 做模拟出题 / 评分 /
    自然语言反馈）。但本系统真正需要"面经 → 弱项 → 学习任务"的闭环是确定性、可单测、
    不烧 token 的规则：弱项聚合、任务草稿映射、题库抽题。

    因此落地为 backend/app/agents/interview/engine.py 中的独立可测模块，
    API 直接调用；LLM 仅在未来做"模拟评分 / 生成参考答案"的增量。
"""
