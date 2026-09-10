"""日报 / 周报服务（Batch 4）。

模块划分：
- ``engine.py``  纯规则：读库 → 组装 ReportData → 渲染 markdown（可单测、不依赖 LLM）
- ``service.py`` 编排：落库 ReportLog + 走提醒通道推送（幂等）

与 Match / Resume / Interview 三个引擎保持同一实现取向：核心是确定性聚合，
不套 BaseAgent / LangGraph（见 JOB_SEARCH_AGENT_DESIGN.md §0.1.3 的有意偏离说明）。
"""
