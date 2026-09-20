"""行动规划（Action Planning）模块。

模块职责（docs/CODEX_MODULAR_DESIGN_STANDARD.md §1）：
- ``task_scope.py`` 任务**赛道口径** —— 按当前 CareerMode 决定"哪些任务进入默认
  视图"，并向调用方说明"为什么排除、排除了多少"。

本模块不负责（刻意划出去，避免边界再次糊掉）：
- 不解析 JD、不生成任务、不改任务状态或赛道（那是 job_match / 任务 CRUD 的事）；
- 不渲染页面、不返回裸字典；
- 不读 cookie、不认识 ViewRole —— 视角是展示层概念，不是业务策略。

产品依据：docs/PRD_CAREER_OS_MODES.md（Milestone B：阶段驱动的任务口径）。
"""
