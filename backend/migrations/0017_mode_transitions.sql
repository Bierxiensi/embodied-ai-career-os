-- 0017_mode_transitions.sql
--
-- 模式切换历史表：只追加，不修改、不删除（PRD §5 F1.4）。
--
-- 为什么 from_mode 允许为 NULL：
--   建库时把默认模式置为当前，也是一次"进入某模式"，只是没有来源模式。
--   允许 NULL 比伪造一个 'init' 模式更诚实 —— 前端据此显示为"系统初始化"
--   而不是一次用户切换。
--
-- 为什么不加指向 career_modes.key 的外键：
--   历史记录必须在模式目录变更之后依然可读。加了外键，未来删改某个模式定义
--   就会连带阻塞历史查询；而"切换不丢历史"正是 PRD §5 F1.3 对用户的承诺。
--   模式 key 本身是稳定业务标识，按它引用而不加约束是刻意选择。
--
-- ⚠️ 本文件里不要出现分号 —— 见 0016 的说明。

CREATE TABLE IF NOT EXISTS mode_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_mode VARCHAR(40),
    to_mode VARCHAR(40) NOT NULL,
    transitioned_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    note TEXT
);
