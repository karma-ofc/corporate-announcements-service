PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 5 AND 120),
    text TEXT NOT NULL DEFAULT '',
    department_id INTEGER NOT NULL REFERENCES departments(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    priority INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 3),
    publish_date TEXT NOT NULL CHECK (date(publish_date) IS NOT NULL),
    expiry_date TEXT NOT NULL CHECK (date(expiry_date) IS NOT NULL),
    is_published INTEGER NOT NULL DEFAULT 0 CHECK (is_published IN (0, 1)),
    CHECK (expiry_date >= publish_date)
);

CREATE INDEX IF NOT EXISTS idx_announcements_department
    ON announcements(department_id);
CREATE INDEX IF NOT EXISTS idx_announcements_dates
    ON announcements(is_published, publish_date, expiry_date);
CREATE INDEX IF NOT EXISTS idx_announcements_priority
    ON announcements(priority DESC, id ASC);
