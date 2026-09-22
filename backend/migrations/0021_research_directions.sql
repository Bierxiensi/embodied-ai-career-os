-- 0021_research_directions.sql
--
-- 博士模块（Phase 1）第一张表：研究方向主数据
--
-- interest_weight 提供六维匹配中"研究方向契合"维度的基准分（由用户转型目标决定）
--
-- 幂等：run_migration.py 捕获 "already exists" 记为已应用
-- 单语句文件：与 0016/0017/0018 同一惯例，避免多语句事务回滚留下静默缺失
-- 注意：注释里不要出现分号，run_migration.py 按分号切分语句不理解注释

CREATE TABLE IF NOT EXISTS research_directions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(40) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    interest_weight INTEGER NOT NULL DEFAULT 70,
    created_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);
