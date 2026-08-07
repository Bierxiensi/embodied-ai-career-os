-- ============================================================
-- Migration: add Observability fields to agent_runs
-- Phase: Phase 2 Week 1 Day 6
-- Date: 2026-08-04
-- Target DB: SQLite (data/app.db)
--
-- 新增字段：
--   status       VARCHAR(20) NOT NULL DEFAULT 'success'
--   duration_ms  INTEGER     NOT NULL DEFAULT 0
--   trace_id     VARCHAR(64) NULL
--
-- 旧数据回填策略：
--   - status：旧记录均为成功执行（失败不会入库），统一设 'success'
--   - duration_ms：旧记录无计时信息，设 0
--   - trace_id：旧记录无 trace_id，保持 NULL
--
-- 兼容性：
--   - 模型已设 server_default，新字段 NOT NULL 不影响旧 INSERT 兼容
--   - 应用层新写入会显式传 status / duration_ms / trace_id
--
-- 执行方式：
--   sqlite3 data/app.db < migrations/0001_agent_runs_observability.sql
--   或应用层执行：python migrations/run_migration.py
-- ============================================================

-- 1. 新增字段（IF NOT EXISTS 语义：SQLite 不支持，用 try-except 模式）
--    重复执行会报"duplicate column"错误，属于幂等保护，可忽略

ALTER TABLE agent_runs ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'success';
ALTER TABLE agent_runs ADD COLUMN duration_ms INTEGER NOT NULL DEFAULT 0;
ALTER TABLE agent_runs ADD COLUMN trace_id VARCHAR(64);

-- 2. 旧数据回填（已通过 DEFAULT 自动填充，此处显式 UPDATE 做二次确认）
UPDATE agent_runs SET status = 'success' WHERE status IS NULL OR status = '';
UPDATE agent_runs SET duration_ms = 0 WHERE duration_ms IS NULL;
-- trace_id 保持 NULL（旧数据无 trace_id）
