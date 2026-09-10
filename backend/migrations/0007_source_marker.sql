-- 0007: 为 projects / tasks / milestones 增加 source 数据来源标记
--
-- 背景（2026-09-10 系统审计）：
--   开发库被历次 pytest 写入的测试数据污染 —— projects 214 行里真实只有 2 行，
--   其余是 "M Test Project"×42、"Scaffold Test"×28、"Test Project"×16 等；
--   tasks 292 行里同一任务最多重复 29 次。
--   根因之一是**三张表都没有任何字段能区分真实数据与测试残留**，事后清理只能靠
--   猜项目名（能猜出 "M Test Project"，猜不出名为 "P" 的项目）。
--
-- 字段语义：
--   user    —— 用户真实数据（默认值，历史数据一律先归为 user，由清理脚本再精确改判）
--   seed    —— 初始化种子数据（app/db/base.py 的 _seed_if_empty）
--   planner —— Planner Agent 生成的任务
--   test    —— 测试残留（可安全清理）
--
-- 说明：历史 212 个测试项目的「改判为 test」不在这里用 LIKE 模式做 —— 模式匹配属于
-- 模糊规则，放在可 review、可 dry-run 的 scripts/purge_test_data.py 里更合适。
-- 本迁移只负责加列并把存量统一置为 user。

ALTER TABLE projects ADD COLUMN source VARCHAR(20) NOT NULL DEFAULT 'user';
ALTER TABLE tasks ADD COLUMN source VARCHAR(20) NOT NULL DEFAULT 'user';
ALTER TABLE milestones ADD COLUMN source VARCHAR(20) NOT NULL DEFAULT 'user';
