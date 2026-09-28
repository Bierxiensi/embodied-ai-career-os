-- 0028_learning_logs_unit_id.sql
--
-- 给 learning_logs 增加 unit_id：学习日志归属「掌握单元」。
--
-- 背景（2026-09-28）：
--   掌握单元四表模型（mastery_units 等，见 24a891c）引入后，
--   学习日志需要能挂到具体掌握单元上。模型侧新增了该列，
--   但 create_all 只建表不 ALTER，既有 dev 库需要这条迁移补列。
--
-- 可空：历史学习日志与未归属单元的日志不对应任何 mastery_unit。
--
-- 幂等：run_migration.py 会捕获 duplicate column 并视为已应用。
--
-- ⚠️ 本文件里不要出现分号（除了末尾那一个）—— 同 0011 的说明。
--    本迁移只做一件事（加列），不建索引：learning_logs 是个人量级的小表，
--    而且多语句在"ALTER 已存在 → 整事务回滚"时会一起回滚，留下静默缺失。

ALTER TABLE learning_logs ADD COLUMN unit_id INTEGER REFERENCES mastery_units(id) ON DELETE SET NULL;
