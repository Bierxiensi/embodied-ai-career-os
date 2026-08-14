-- 0006: commit_suggestions.commit_sha 唯一索引
-- 目的：防止重复 commit（水位回退/重试场景）被多次存储，与 store.save_suggestion 的查重逻辑互为兜底。
--
-- 创建唯一索引前先清理可能已存在的重复 commit_sha 数据（每组保留最早一条）。
-- 该 DELETE 在无重复时影响 0 行，安全幂等。
DELETE FROM commit_suggestions
WHERE id NOT IN (
    SELECT MIN(id) FROM commit_suggestions GROUP BY commit_sha
);

-- 唯一索引（IF NOT EXISTS 保证幂等重跑不报错；SQLite 与 PostgreSQL 均支持）
CREATE UNIQUE INDEX IF NOT EXISTS idx_commit_suggestion_sha
    ON commit_suggestions(commit_sha);
