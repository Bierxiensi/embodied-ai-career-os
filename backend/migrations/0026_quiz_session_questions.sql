-- 0026: 小测验会话题目表
--
-- 背景（2026-09-22 接前端小测验时发现）：
--   POST /api/interview/quiz/start 会用 LLM 把题库原题改写成 choice / judge /
--   fill 变体，并把变体的 question / options / correct_answer 一起返回给前端。
--   但**没有任何地方存放这些变体** —— 前端作答时只回传 question_id 与
--   question_type，判分端 practice_answer 只能拿题库原题（interview_questions）
--   的 options 列来取正确答案，而该列对生成题通常为 NULL。
--
--   于是「生成的正确答案被丢弃」，choice/judge 题退化成按要点关键词评分，
--   即使用真实 LLM 也判不对。
--
--   本表把「本次测验实际下发给用户的那道题」落库，判分时按
--   (session_id, question_id) 取回，生成题才可能被正确判分。
--   同时正确选项也不会随响应下发给浏览器。

CREATE TABLE IF NOT EXISTS quiz_session_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(50) NOT NULL,
    question_id INTEGER NOT NULL REFERENCES interview_questions(id),
    question_type VARCHAR(20) NOT NULL,
    question TEXT NOT NULL,
    options TEXT,            -- JSON string[]：choice/judge 的选项
    correct_answer TEXT,     -- 生成题的真实答案（不下发前端）
    skill_name VARCHAR(100),
    difficulty VARCHAR(20),
    position INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 判分时按 (session_id, question_id) 查，session_id 是选择度最高的一列
CREATE INDEX IF NOT EXISTS idx_quiz_session_questions_session ON quiz_session_questions(session_id);
