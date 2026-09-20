-- 0016_career_modes.sql
--
-- Career OS 阶段模式化（Milestone A：模式骨架）。本文件建第一张表：
--
--   career_modes     模式定义 + "哪一个是当前模式"这一状态
--   mode_transitions 切换历史，只追加不修改 —— 见 0017
--   ux_career_modes_current（is_current 唯一索引）—— 见 0018
--
-- 产品依据：docs/PRD_CAREER_OS_MODES.md §4 / §7.1
--
-- 关键设计说明（为什么切换阶段不会丢数据）：
--   本表**不加任何指向岗位 / 任务 / 投递 / 面试 / 技能的外键**。
--   模式切换只写 is_current 与 mode_transitions 两处，物理上不可能级联
--   影响既有历史。赛道过滤属于 Milestone B，届时只改查询口径，不改数据。
--
-- 幂等：run_migration.py 会捕获 "already exists" 并记为已应用。
--
-- ⚠️ 本文件里不要出现分号 —— run_migration.py 用朴素的按 "分号" 切分来拆语句，
--    不理解 SQL 注释，注释里写一个分号就会被切出一个非法片段。
--    同理只放一条语句：多语句在"后半句失败 → 整个事务回滚"时会一起回滚，
--    留下静默缺失。因此 mode_transitions 放在 0017，is_current 的唯一索引
--    放在 0018，每个文件只做一件事。
--
-- ⚠️ 严格来说本语句是 SQLite 方言（INTEGER PRIMARY KEY AUTOINCREMENT、
--    datetime('now')），与既有的 0013_experiments.sql 等保持同一口径。
--    PostgreSQL 环境下的建表走 app/db/base.py 的 create_all（方言自适应），
--    新列同理由 ORM 元数据负责。这一点已在交付说明的"已知限制"中列明。

CREATE TABLE IF NOT EXISTS career_modes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(40) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    objective TEXT NOT NULL,
    deadline DATE,
    active_track_keys JSON NOT NULL DEFAULT '[]',
    frozen_track_keys JSON NOT NULL DEFAULT '[]',
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);
