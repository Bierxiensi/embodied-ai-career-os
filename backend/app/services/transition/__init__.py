"""Career Transition Dashboard 模块（Phase 3）。

模块划分：
- ``service.py`` 聚合用例：把「职业进度 / 当前工作 / 学术与博士」三区拼成一份 payload

它解决的问题：
    平台原先有 /dashboard（我现在什么水平）、/today（今天干什么）、
    /jobs（离岗位差多少）、/phd（博士进度）四页，各自只回答一半问题。
    在职转型期真正要看的是"这四条线现在各到哪儿了" —— 本模块把它们收口一屏。

真源分工（本模块不持有任何数据，只做只读聚合）：
- 就绪度            → services/readiness（与 /api/job-hunt 同源）
- 答辩截止 / 在职事实 → core/transition_context
- 博士目标与导师     → phd_targets / phd_advisors 表
- 当前模式          → services/career_mode

ROI 任务与风险雷达**不在**本模块：它们随"今天"变化，由 /api/plan/today 提供。
"""
