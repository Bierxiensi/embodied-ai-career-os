-- ============================================================
-- Migration: create paper_chunk_embeddings table
-- Phase: Phase 3 Week 1 Day 2
-- Date: 2026-08-05
-- Target DB: SQLite (data/app.db)
--
-- 新增表：
--   paper_chunk_embeddings  论文分块向量嵌入（Day 2 RAG 检索数据源）
--
-- 关系：
--   paper_chunk_embeddings.chunk_id → paper_chunks.id（FK + INDEX）
--
-- 设计说明：
--   - 独立表支持同一 chunk 多模型 embedding 共存（开发态 hash + 生产态 ST）
--   - embedding 存 JSON 字符串（list[float]），零依赖、可调试
--   - model_name 加索引，检索时按模型过滤
--
-- 执行方式：
--   python migrations/run_migration.py
--   或 sqlite3 data/app.db < migrations/0003_paper_chunk_embeddings.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS paper_chunk_embeddings (
    id           VARCHAR        PRIMARY KEY,
    chunk_id     VARCHAR        NOT NULL,
    embedding    TEXT           NOT NULL,
    model_name   VARCHAR(100)   NOT NULL,
    dim          INTEGER        NOT NULL,
    created_at   DATETIME       NOT NULL,
    FOREIGN KEY (chunk_id) REFERENCES paper_chunks(id)
);

CREATE INDEX IF NOT EXISTS idx_pce_chunk_id    ON paper_chunk_embeddings(chunk_id);
CREATE INDEX IF NOT EXISTS idx_pce_model_name  ON paper_chunk_embeddings(model_name);
