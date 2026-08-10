-- V2 Project Management: Add project_id and milestone_id to tasks
-- Also creates projects and milestones tables

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    goal VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    current_version VARCHAR(20) NOT NULL DEFAULT 'V0',
    github_url VARCHAR(500),
    readme TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    goal VARCHAR(500) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'locked',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);

ALTER TABLE tasks ADD COLUMN project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL;
ALTER TABLE tasks ADD COLUMN milestone_id INTEGER REFERENCES milestones(id) ON DELETE SET NULL;
