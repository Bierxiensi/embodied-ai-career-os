-- 0010_day_artifacts.sql
--
-- 新建 day_artifacts 表：计划 §十 要求的「每日四件套」产出记录。
--
-- 背景（2026-09-10）：
--   把平台从「展示」变「学习」的核心机制是每日产出契约 ——
--   ① 代码 ② 笔记 ③ 至少 5 道面试题 ④ git commit。
--   现有的 Task.status（todo/doing/done）是人为切换的，没有客观标准，
--   所以"完成"没有约束力。四件套是可核验的。
--
--   现有的 LearningLog 表达不了这件事：它是"一条自由文本 + 一个可选链接"，
--   无法回答"今天该产出 4 类，哪几类齐了"。
--
-- 范围：
--   P0（本次）：手工勾选 + 手工链接，auto_verified 恒为 0。
--   P2（后续）：自动核验 —— questions 由题库当日新增条数判定，
--              commit 由 GitHub API 按日期归集，code 由 commit diff 佐证。
--   P2+：Skill 晋级改为 evidence-gated，本表成为技能等级的唯一证据来源。
--
-- 关联 plan_days(id) 且 ON DELETE CASCADE —— 计划日被删时其产出无意义。
--
-- 幂等：run_migration.py 会捕获 already exists 并视为已应用。
--
-- ⚠️ 本文件里不要出现分号（除了末尾那一个）—— 同 0009 的说明。

CREATE TABLE IF NOT EXISTS day_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_day_id INTEGER NOT NULL REFERENCES plan_days(id) ON DELETE CASCADE,
    kind VARCHAR(20) NOT NULL,
    title VARCHAR(200),
    url VARCHAR(500),
    payload JSON,
    auto_verified BOOLEAN NOT NULL DEFAULT 0,
    note VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);
