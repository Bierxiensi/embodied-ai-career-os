"""就绪度（Readiness）模块。

模块划分：
- ``service.py`` 用例：岗位对齐的匹配计算（推进度 / 硬性达标率 / 技能明细）

产品边界（docs/CODEX_MODULAR_DESIGN_STANDARD.md §1）：
    本模块只回答「离目标岗位还差多少」，不碰任务、投递、面试、风险。
    它**不持有**目标岗位配置 —— 那是 ``core/target_roles.py`` 的职责；
    也不重复实现严格达标率 —— 那是 ``core/risk.track_strict_pct`` 的职责。

为什么必须有这个模块（Phase 3）：
    ``/api/job-hunt`` 与 ``/api/transition/dashboard`` 要给出同一组数字。
    匹配计算一旦有第二份实现，两页的"就绪度"就会分叉，
    而用户无法判断哪个可信（本项目 2026-09-22 刚因同类分叉吃过一次亏）。
"""
