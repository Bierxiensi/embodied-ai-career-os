-- 0023_phd_advisors.sql
--
-- 博士模块（Phase 1）第三张表：导师 + 缓存的六维匹配结果
--
-- match_json 存 {overall, grade, dimensions, gaps, computed_at}
-- target_id 为逻辑外键（不建物理外键）
--
-- 幂等：run_migration.py 捕获 "already exists" 记为已应用

CREATE TABLE IF NOT EXISTS phd_advisors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id INTEGER,
    name VARCHAR(100) NOT NULL,
    title VARCHAR(50),
    research_area TEXT,
    recruiting BOOLEAN NOT NULL DEFAULT TRUE,
    in_service_friendly BOOLEAN NOT NULL DEFAULT FALSE,
    homepage VARCHAR(300),
    notes TEXT,
    match_json JSON,
    last_matched_at TIMESTAMP,
    source VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);
