"""技能结构（Skill Graph）模块 —— Phase 3。

模块划分：
- ``service.py`` 六域聚合（R2 雷达数据源）与依赖图装配

真源分工（不要让任何一处变成第二份真相）：
- 技能自评 + **六域归属** → ``core/skill_profile.py``
- 先修边（依赖图）        → ``core/skill_graph.py``
- 技能当前等级            → ``skills`` 表
- 依赖边持久化            → ``skill_dependency`` 表（由 scripts/seed_skill_graph.py 从上面的种子投影）

本模块自己不持有任何名单，只做"读真源 + 组装"。
"""
