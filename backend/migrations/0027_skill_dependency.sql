-- 0027_skill_dependency.sql
--
-- Phase 3（技能依赖图）：技能之间的**先修关系**表
--
-- 背景：v2.1 施工计划 Phase 3 Day 3.1 要求「技能依赖图」。
--   在此之前，技能只是一张平表（skills：name / level / target_level），
--   平台能回答"哪项技能缺口最大"，但回答不了"该先学哪个" ——
--   而后者才决定学习顺序。本表存有向边 prerequisite -> dependent，
--   语义是「必须先掌握 prerequisite，dependent 才学得动」。
--
-- 为什么进库而不是只留在 Python 常量：
--   依赖边是会被反复调整的知识（学到哪儿、发现哪条边不成立都要改）。
--   放库里才能由脚本幂等重放，并允许后续前端 / Agent 回写。
--   Python 侧的 core/skill_graph.py 只作为**种子真源**（与 skill_profile 同款约定）。
--
-- 为什么不再建第二张表存节点：
--   skill_dependency 的两个端点都指向 skills.name（逻辑引用，不建物理外键）。
--   技能节点本身已由 skills 表承载，复制一张节点表只会产生第三份技能清单。
--
-- ⚠️ 本文件里注释不要出现分号 —— run_migration.py 用朴素的按 "分号" 切分来拆语句，
--    不理解 SQL 注释。表后跟索引是本仓库的既定惯例（见 0026），
--    三段各自幂等，重复应用被 "already exists" 捕获。
--
-- ⚠️ 方言：SQLite 写法（INTEGER PRIMARY KEY AUTOINCREMENT / datetime('now')），
--    由 run_migration.py 的 _PG_TRANSLATIONS 翻译为 PG 等价写法，
--    tests/test_migration_dialect_compat.py 会逐文件断言翻译后无残留。

CREATE TABLE IF NOT EXISTS skill_dependency (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prerequisite VARCHAR(100) NOT NULL,
    dependent VARCHAR(100) NOT NULL,
    note VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- 同一对先修->后继只允许一条，种子脚本据此幂等
CREATE UNIQUE INDEX IF NOT EXISTS ux_skill_dependency_edge
    ON skill_dependency(prerequisite, dependent);

-- 反向查询索引：某技能的"先修有哪些"（雷达卡片标注"先修 X"走这条路）
CREATE INDEX IF NOT EXISTS idx_skill_dependency_dependent
    ON skill_dependency(dependent);
