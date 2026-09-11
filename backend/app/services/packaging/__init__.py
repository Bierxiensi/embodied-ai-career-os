"""求职包装服务（P4）。

模块划分：
- ``engine.py``  纯函数：证据链 → README 骨架 / 简历技能行（可单测、不碰 DB、不依赖 LLM）
- ``service.py`` 取数：读项目 / 里程碑 / 任务技能 / 实验 + 调 ``core/evidence.py``

与 Match / Resume / Interview / Report 四个引擎保持同一取向：核心是确定性聚合与推导，
不套 BaseAgent / LangGraph（见 JOB_SEARCH_AGENT_DESIGN.md §0.1.3 的有意偏离说明）。
"""
