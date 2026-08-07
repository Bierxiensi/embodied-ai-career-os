-- ============================================================
-- Migration: create papers + paper_chunks tables
-- Phase: Phase 3 Week 1 Day 1
-- Date: 2026-08-05
-- Target DB: SQLite (data/app.db)
--
-- 新增表：
--   papers         论文结构化摘要（PaperAgent.summarizer 产出）
--   paper_chunks   论文分块（PaperAgent.chunker 产出，Day2 RAG 数据源）
--
-- 关系：
--   paper_chunks.paper_id → papers.id（FK + INDEX，便于按论文检索 chunk）
--   paper_chunks.section 加索引，便于 Day2 按 section 过滤检索
--
-- 执行方式：
--   python migrations/run_migration.py
--   或 sqlite3 data/app.db < migrations/0002_papers_and_chunks.sql
-- ============================================================

-- 1. papers 表
CREATE TABLE IF NOT EXISTS papers (
    id                    VARCHAR        PRIMARY KEY,
    title                 VARCHAR(500)   NOT NULL,
    source_path           VARCHAR(500)   NOT NULL,
    file_type             VARCHAR(10)    NOT NULL,
    arxiv_id              VARCHAR(20),
    method                TEXT           NOT NULL DEFAULT '',
    dataset               TEXT           NOT NULL DEFAULT '',
    contribution          TEXT           NOT NULL DEFAULT '',
    relation_to_my_project TEXT          NOT NULL DEFAULT '',
    confidence            VARCHAR(10)    NOT NULL DEFAULT 'low',
    page_count            INTEGER        NOT NULL DEFAULT 1,
    chunk_count           INTEGER        NOT NULL DEFAULT 0,
    created_at            DATETIME       NOT NULL
);

-- 2. paper_chunks 表
CREATE TABLE IF NOT EXISTS paper_chunks (
    id           VARCHAR        PRIMARY KEY,
    paper_id     VARCHAR        NOT NULL,
    text         TEXT           NOT NULL,
    section      VARCHAR(30)    NOT NULL DEFAULT 'unknown',
    page         INTEGER        NOT NULL DEFAULT 1,
    char_offset  INTEGER        NOT NULL DEFAULT 0,
    token_count  INTEGER        NOT NULL DEFAULT 0,
    created_at   DATETIME       NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES papers(id)
);

-- 3. 索引（加速 Day2 RAG 检索）
CREATE INDEX IF NOT EXISTS idx_paper_chunks_paper_id ON paper_chunks(paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_chunks_section ON paper_chunks(section);
