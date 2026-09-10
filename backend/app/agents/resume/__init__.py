"""简历 Agent（ResumeAgent）包。

设计偏离说明（与 MatchAgent 一致）：
    《求职 Agent 设计》把 ResumeAgent 列为 BaseAgent 子类（依赖 LLM 做解析/诊断/生成）。
    但"防虚构校验"是硬约束（v2.0 §8：每条 claim 必须有 ResumeFact 锚点，否则标红），
    必须是确定性、可单测、可解释、不烧 token 的规则。因此落地的核心能力是
    backend/app/agents/resume/engine.py 中的独立可测模块（纯规则 + 锚点库），
    API 直接调用。LLM 仅在未来做"措辞优化 / 生成建议"的增量，且生成内容同样要再过一遍
    防虚构校验。这仍是 Agent 能力，只是不强制 LangGraph 契约。
"""
