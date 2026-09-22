-- 0024_phd_advisors_contacted.sql
--
-- Phase 2 风险雷达的 phd 维度依赖 Advisor.contacted（是否已联系导师）
-- 镜像 0021-0023 的 SQLite 写法：单语句、注释不含分号、方言翻译由 run_migration.py 处理
-- 幂等：重复列错误被 run_migration 捕获记为已应用

ALTER TABLE phd_advisors ADD COLUMN contacted BOOLEAN NOT NULL DEFAULT FALSE;
