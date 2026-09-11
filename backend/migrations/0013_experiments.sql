CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_day_id INTEGER REFERENCES plan_days(id) ON DELETE SET NULL,
    day_seq INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    kind VARCHAR(30) NOT NULL DEFAULT 'finetune',
    skill_name VARCHAR(100),
    variants JSON,
    metrics JSON,
    conclusion TEXT,
    artifact_ids JSON,
    created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
)
