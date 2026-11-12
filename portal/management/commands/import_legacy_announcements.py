import json
import sqlite3
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from announcements import Announcement as LegacyAnnouncement
from portal.models import Announcement, Department


class Command(BaseCommand):
    help = (
        "Copy legacy SQLite or JSON announcement data into Django's database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=Path,
            default=settings.ANNOUNCEMENTS_DB_PATH,
            help=(
                "Legacy SQLite database or JSON file "
                "(defaults to configured SQLite)."
            ),
        )

    def handle(self, *args, **options):
        source = options["source"]
        if not source.is_file():
            raise CommandError(f"Source file does not exist: {source}")
        try:
            if source.suffix.lower() == ".json":
                records = self._read_json(source)
            else:
                records = self._read_sqlite(source)
            created = 0
            updated = 0
            with transaction.atomic():
                for record_id, announcement in records:
                    department, _ = Department.objects.get_or_create(
                        name=announcement.department
                    )
                    _, was_created = Announcement.objects.update_or_create(
                        pk=record_id,
                        defaults={
                            "title": announcement.title,
                            "text": announcement.text,
                            "department": department,
                            "priority": announcement.priority,
                            "publish_date": announcement.publish_date,
                            "expiry_date": announcement.expiry_date,
                            "status": (
                                Announcement.Status.PUBLISHED
                                if announcement.is_published
                                else Announcement.Status.DRAFT
                            ),
                        },
                    )
                    created += int(was_created)
                    updated += int(not was_created)
        except (
            OSError,
            sqlite3.Error,
            ValueError,
            KeyError,
            TypeError,
        ) as error:
            message = f"Could not import {source}: {error}"
            raise CommandError(message) from error
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(records)} announcements "
                f"({created} created, {updated} updated)."
            )
        )

    @staticmethod
    def _read_json(source: Path):
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("JSON source must contain a list")
        return [
            (index, LegacyAnnouncement.from_dict(item))
            for index, item in enumerate(data, start=1)
        ]

    @staticmethod
    def _read_sqlite(source: Path):
        connection = sqlite3.connect(
            f"file:{source.resolve()}?mode=ro",
            uri=True,
        )
        try:
            rows = connection.execute(
                """
                SELECT a.id, a.title, a.text, d.name, a.priority,
                       a.publish_date, a.expiry_date, a.is_published
                FROM announcements AS a
                JOIN departments AS d ON d.id = a.department_id
                ORDER BY a.id
                """
            ).fetchall()
        finally:
            connection.close()
        return [
            (
                row[0],
                LegacyAnnouncement(
                    title=row[1],
                    text=row[2] or "",
                    department=row[3],
                    priority=int(row[4]),
                    publish_date=date.fromisoformat(row[5]),
                    expiry_date=date.fromisoformat(row[6]),
                    is_published=bool(row[7]),
                ),
            )
            for row in rows
        ]
