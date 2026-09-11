-- 0012_day_progress.sql
--
-- 新建 day_progress 表：课程执行记录，与日历解耦（P1 滑期机制的核心实体）。
--
-- 背景（docs/platform-direction-30day.md §四 决策 1 / §七 P1）：
--   计划日 PlanDay.seq 是不可变的课程序号，绝不绑死日历日期。
--   滑期是必然事件（9 月底离职、10 月海投面试），若 Day 绑死日期，
--   滑 1 天 → 后面 29 天全错位，用户第一反应是放弃平台。
--   解耦后由 day_progress 记录「你实际在哪天执行、状态如何、为什么偏离」。
--
-- 语义：
--   plan_day_id  UNIQUE —— 一天最多一条进度记录，直接 CASCADE 跟随 plan_days
--   status        执行状态：pending/done/compressed/deferred/skipped
--   calendar_date 实际执行日期（可移动；done/compressed 时写入，deferred/skipped 留空）
--   actual_minutes 实际投入分钟（可选）
--   deviation_note 偏离说明，滑期决策的硬性落点（压缩/顺延/放弃都要落 note）
--
-- 幂等：run_migration.py 捕获 already exists 视作已应用。
-- ⚠️ 注释里不要出现分号（run_migration.py 按分号裸切分、不识注释），
--    本迁移只建一张表，单语句。

CREATE TABLE IF NOT EXISTS day_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_day_id INTEGER NOT NULL UNIQUE REFERENCES plan_days(id) ON DELETE CASCADE,
    calendar_date VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    actual_minutes INTEGER,
    deviation_note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);
