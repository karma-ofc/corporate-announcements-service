"""SQLite connection management and announcement queries."""

import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "announcements.sqlite3"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open a configured connection with foreign-key checks enabled."""
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: Path | str | None = None) -> None:
    """Create the domain schema if it does not exist yet."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with closing(get_connection(db_path)) as connection:
        connection.executescript(schema)


def list_announcements(
    db_path: Path | str | None = None,
) -> list[sqlite3.Row]:
    """Return announcements in the site's established priority order."""
    query = """
        SELECT a.id, a.title, a.text, d.name AS department, a.priority,
               a.publish_date, a.expiry_date, a.is_published
        FROM announcements AS a
        JOIN departments AS d ON d.id = a.department_id
        ORDER BY a.priority DESC, a.id ASC
    """
    with closing(get_connection(db_path)) as connection:
        return connection.execute(query).fetchall()


def get_announcement(
    announcement_id: int,
    db_path: Path | str | None = None,
) -> sqlite3.Row | None:
    """Get one announcement by its stable database ID."""
    query = """
        SELECT a.id, a.title, a.text, d.name AS department, a.priority,
               a.publish_date, a.expiry_date, a.is_published
        FROM announcements AS a
        JOIN departments AS d ON d.id = a.department_id
        WHERE a.id = ?
    """
    with closing(get_connection(db_path)) as connection:
        return connection.execute(query, (announcement_id,)).fetchone()


def list_announcements_active_on(
    reference_date: date,
    db_path: Path | str | None = None,
) -> list[sqlite3.Row]:
    """Return published announcements in effect on the specified date."""
    query = """
        SELECT a.id, a.title, a.text, d.name AS department, a.priority,
               a.publish_date, a.expiry_date, a.is_published
        FROM announcements AS a
        JOIN departments AS d ON d.id = a.department_id
        WHERE a.is_published = 1
          AND a.publish_date <= ?
          AND a.expiry_date >= ?
        ORDER BY a.priority DESC, a.id ASC
    """
    date_value = reference_date.isoformat()
    with closing(get_connection(db_path)) as connection:
        return connection.execute(query, (date_value, date_value)).fetchall()


def list_archived_announcements(
    reference_date: date,
    db_path: Path | str | None = None,
) -> list[sqlite3.Row]:
    """Return published announcements whose expiry date has passed."""
    query = """
        SELECT a.id, a.title, a.text, d.name AS department, a.priority,
               a.publish_date, a.expiry_date, a.is_published
        FROM announcements AS a
        JOIN departments AS d ON d.id = a.department_id
        WHERE a.is_published = 1 AND a.expiry_date < ?
        ORDER BY a.priority DESC, a.id ASC
    """
    with closing(get_connection(db_path)) as connection:
        return connection.execute(
            query, (reference_date.isoformat(),)
        ).fetchall()


def get_statistics(
    reference_date: date,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Return aggregate metrics and department/priority breakdowns."""
    summary_query = """
        SELECT COUNT(*) AS total_count,
               SUM(CASE WHEN is_published = 1 THEN 1 ELSE 0 END)
                   AS published_count,
               SUM(CASE WHEN is_published = 1 AND publish_date <= ?
                         AND expiry_date >= ? THEN 1 ELSE 0 END)
                   AS active_count,
               AVG(priority) AS average_priority
        FROM announcements
    """
    department_query = """
        SELECT d.name AS department, COUNT(a.id) AS announcement_count,
               SUM(CASE WHEN a.is_published = 1 THEN 1 ELSE 0 END)
                   AS published_count
        FROM departments AS d
        LEFT JOIN announcements AS a ON a.department_id = d.id
        GROUP BY d.id, d.name
        ORDER BY announcement_count DESC, d.name ASC
    """
    priority_query = """
        SELECT priority, COUNT(*) AS announcement_count
        FROM announcements
        GROUP BY priority
        ORDER BY priority DESC
    """
    value = reference_date.isoformat()
    with closing(get_connection(db_path)) as connection:
        summary = connection.execute(summary_query, (value, value)).fetchone()
        departments = connection.execute(department_query).fetchall()
        priorities = connection.execute(priority_query).fetchall()
    return {
        "summary": dict(summary),
        "departments": [dict(row) for row in departments],
        "priorities": [dict(row) for row in priorities],
    }
