-- 0022_phd_targets.sql
--
-- 博士模块（Phase 1）第二张表：院校 / 项目机会
--
-- tier / min_publication / application_deadline / in_service_friendly 供六维匹配计算
-- direction_key / track_key 为逻辑引用，不建物理外键（与 career_modes 一致）
--
-- 幂等：run_migration.py 捕获 "already exists" 记为已应用

CREATE TABLE IF NOT EXISTS phd_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    institution VARCHAR(200) NOT NULL,
    city VARCHAR(50),
    tier VARCHAR(30),
    direction_key VARCHAR(40),
    track_key VARCHAR(40),
    in_service_friendly BOOLEAN NOT NULL DEFAULT FALSE,
    min_publication VARCHAR(20),
    application_deadline DATE,
    notes TEXT,
    source VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);
