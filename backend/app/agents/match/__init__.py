"""JD 匹配 Agent 能力包（纯规则引擎）。

对外暴露 JDParser / MatchEngine，供 API 与定时报告调用。
不实现 BaseAgent（LangGraph）契约——纯规则评分无需图编排，见 engine.py 说明。
"""
