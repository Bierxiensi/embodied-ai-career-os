-- 0020: 题库练习记录表 + 题目表新增题型字段
-- 对齐 docs/superpowers/specs/2026-09-16-question-practice-scoring-design.md

-- 题目表新增题型和手动选项字段
ALTER TABLE interview_questions ADD COLUMN question_type VARCHAR(20) NOT NULL DEFAULT 'open';
ALTER TABLE interview_questions ADD COLUMN options TEXT;  -- JSON: {"choices": [...], "correct": "B"} or null

-- 练习记录表
CREATE TABLE IF NOT EXISTS practice_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL REFERENCES interview_questions(id),
    question_type VARCHAR(20) NOT NULL,
    user_answer TEXT NOT NULL,
    correct_answer TEXT,
    correct INTEGER NOT NULL DEFAULT 0,
    score INTEGER NOT NULL DEFAULT 0,
    feedback TEXT,
    outline_covered TEXT,   -- JSON string[]
    outline_missed TEXT,    -- JSON string[]
    skill_name VARCHAR(100),
    mode VARCHAR(20) NOT NULL DEFAULT 'single',
    session_id VARCHAR(50),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_practice_records_question ON practice_records(question_id);
CREATE INDEX IF NOT EXISTS idx_practice_records_session ON practice_records(session_id);
CREATE INDEX IF NOT EXISTS idx_practice_records_skill ON practice_records(skill_name);
