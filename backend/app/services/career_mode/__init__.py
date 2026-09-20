"""职业阶段模式（Career Mode）模块。

模块划分：
- ``presets.py`` 纯配置：有哪几种模式、默认是哪种、各模式的赛道策略（无副作用）
- ``service.py`` 用例：把预置物化到库、解析当前模式、切换模式、读切换历史

产品依据：docs/PRD_CAREER_OS_MODES.md（Milestone A：模式骨架）
边界（docs/CODEX_MODULAR_DESIGN_STANDARD.md §1）：本模块只管「当前阶段、模式切换、
赛道策略」，不碰 JD 解析、任务 CRUD、岗位状态。切换模式不删除、不修改、不隐藏
任何既有职业 / 岗位 / 任务 / 投递 / 面试历史。

Milestone A 的完成定义：默认进入 job_hunt；切换后刷新页面仍保持；求职历史保持可读。
赛道策略本期只**存下来**，不执行任何过滤 —— 任务与推荐口径的收紧属于 Milestone B。
"""
