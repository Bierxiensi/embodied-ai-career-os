-- 0025_phd_advisors_contact_date.sql
--
-- Phase 2 风险雷达的 phd 维度补充：联系日期（可空）
-- 镜像 0021-0023 的 SQLite 写法：单语句、注释不含分号、方言翻译由 run_migration.py 处理
-- 幂等：重复列错误被 run_migration 捕获记为已应用

ALTER TABLE phd_advisors ADD COLUMN contact_date TIMESTAMP;
