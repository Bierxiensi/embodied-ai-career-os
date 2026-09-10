-- 0009_plan_days.sql
--
-- 新建 plan_days 表：30 天施工计划的课程脊梁（Day 1..30）。
--
-- 背景（2026-09-10 用户反馈「平台更像展示平台，不能支撑学习」）：
--   平台此前只有状态机（Skill.level / Task.status / Milestone.status），
--   没有任何"计划"实体 —— 30 天计划只活在用户读的那份文档里，系统里没有投影。
--   于是 Planner 只能按技能缺口生成"最合理的随机任务"，
--   不知道"今天是 Day 2，内容是 Attention 手写实现，验收是能解释 √d"。
--   度量而不驱动，就是展示。
--
-- 语义：
--   seq（1..30）是**不可变的课程序号**，绝不与日历日期绑定。
--   "今天是第几天"由日历与 DayProgress（P1）共同推导 ——
--   落后只提示、不自动顺延，否则滑一天后面全错位，30 天会变成 45 天。
--
-- 内容来源：app/core/plan_30d.py（唯一事实来源）。
-- 本表只是它的数据库投影，由 scripts/seed_plan_30d.py 幂等写入。
-- 不做 CRUD 管理界面 —— 改计划 = 改 Python 文件 + 重跑脚本。
--
-- 幂等：run_migration.py 会捕获 already exists 并视为已应用。
--
-- ⚠️ 本文件里不要出现分号（除了末尾那一个）—— run_migration.py 用朴素的
--    按分号切分来拆语句，不理解 SQL 注释，注释里写一个分号就会被切出非法片段。

CREATE TABLE IF NOT EXISTS plan_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seq INTEGER NOT NULL UNIQUE,
    phase INTEGER NOT NULL,
    phase_name VARCHAR(100) NOT NULL,
    title VARCHAR(200) NOT NULL,
    theme VARCHAR(50) NOT NULL,
    objectives JSON,
    acceptance JSON,
    interview_topics JSON,
    resources JSON,
    est_minutes INTEGER NOT NULL DEFAULT 360,
    track_key VARCHAR(40) NOT NULL DEFAULT 'llm',
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);
