ALTER TABLE interview_questions ADD COLUMN source_day_seq INTEGER;
ALTER TABLE interview_questions ADD COLUMN skill_name VARCHAR(100);
ALTER TABLE interview_questions ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT 0