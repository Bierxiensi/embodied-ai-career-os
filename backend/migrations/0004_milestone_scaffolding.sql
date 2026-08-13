-- V2.1 Task Scaffolding: Add workspace + required_modifications to milestones
-- workspace: 物理工作空间路径（Claude Code 写 baseline 时落盘，后端只存路径）
-- required_modifications: 必改项清单（JSON 数组）

ALTER TABLE milestones ADD COLUMN workspace VARCHAR(200);
ALTER TABLE milestones ADD COLUMN required_modifications JSON;
