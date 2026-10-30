import json
from datetime import date, timedelta
from pathlib import Path
import sqlite3
import tempfile
import unittest

from db.database import (
    get_connection,
    initialize_database,
    list_announcements,
    list_announcements_active_on,
)
from db.import_json import import_announcements


class SQLiteStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.json_path = self.root / "announcements.json"
        self.db_path = self.root / "announcements.sqlite3"
        today = date.today()
        self.json_path.write_text(
            json.dumps([
                {
                    "title": "Плановое отключение VPN",
                    "text": "Работы ночью.",
                    "department": "IT",
                    "priority": 3,
                    "publish_date": today.isoformat(),
                    "expiry_date": (today + timedelta(days=2)).isoformat(),
                    "is_published": True,
                }
            ], ensure_ascii=False),
            encoding="utf-8",
        )

    def test_connection_returns_rows_and_enforces_foreign_keys(self) -> None:
        initialize_database(self.db_path)
        connection = get_connection(self.db_path)
        self.addCleanup(connection.close)

        self.assertIs(connection.row_factory, sqlite3.Row)
        self.assertEqual(
            connection.execute("PRAGMA foreign_keys").fetchone()[0], 1
        )
        with self.assertRaises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO announcements
                    (title, text, department_id, priority, publish_date,
                     expiry_date, is_published)
                VALUES ('Unknown department', '', 900, 1, '2026-01-01',
                        '2026-01-02', 1)
                """
            )

    def test_import_is_repeatable_and_date_query_works(self) -> None:
        self.assertEqual(import_announcements(self.json_path, self.db_path), 1)
        self.assertEqual(import_announcements(self.json_path, self.db_path), 1)

        rows = list_announcements(self.db_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["department"], "IT")
        self.assertEqual(rows[0]["title"], "Плановое отключение VPN")
        self.assertEqual(
            len(list_announcements_active_on(date.today(), self.db_path)), 1
        )


if __name__ == "__main__":
    unittest.main()
