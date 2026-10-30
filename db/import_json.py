"""Import the legacy JSON collection into the SQLite domain database."""

import argparse
import json
from contextlib import closing
from pathlib import Path
from typing import Any

from announcements import Announcement
from db.database import DEFAULT_DB_PATH, get_connection, initialize_database

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_PATH = PROJECT_ROOT / "data" / "announcements.json"


def import_announcements(
    json_path: Path | str = DEFAULT_JSON_PATH,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> int:
    """Replace SQLite's announcement dataset from JSON, atomically.

    Re-running this migration is safe: IDs follow the source record order, and
    any invalid record rolls the data replacement back as a single transaction.
    """
    source = Path(json_path)
    with source.open("r", encoding="utf-8") as json_file:
        records: Any = json.load(json_file)
    if not isinstance(records, list):
        raise ValueError("JSON-файл должен содержать список объявлений")

    parsed = [Announcement.from_dict(record) for record in records]
    initialize_database(db_path)
    with closing(get_connection(db_path)) as connection:
        with connection:
            connection.execute("DELETE FROM announcements")
            connection.execute("DELETE FROM departments")
            department_ids: dict[str, int] = {}
            for record_id, announcement in enumerate(parsed, start=1):
                department_id = department_ids.get(announcement.department)
                if department_id is None:
                    cursor = connection.execute(
                        "INSERT INTO departments (name) VALUES (?)",
                        (announcement.department,),
                    )
                    department_id = cursor.lastrowid
                    department_ids[announcement.department] = department_id
                connection.execute(
                    """
                    INSERT INTO announcements (
                        id, title, text, department_id, priority, publish_date,
                        expiry_date, is_published
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        announcement.title,
                        announcement.text,
                        department_id,
                        announcement.priority,
                        announcement.publish_date.isoformat(),
                        announcement.expiry_date.isoformat(),
                        int(announcement.is_published),
                    ),
                )
    return len(parsed)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Импортировать объявления из JSON в SQLite"
    )
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON_PATH)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    print(
        f"Импортировано объявлений: "
        f"{import_announcements(args.json, args.db)} "
        f"({args.db})"
    )


if __name__ == "__main__":
    main()
