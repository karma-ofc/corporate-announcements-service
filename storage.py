"""JSON storage for the announcement collection."""

import json
from pathlib import Path

from announcements import Announcement, AnnouncementError


class StorageError(RuntimeError):
    """Raised when announcement data cannot be read or written."""


def load_announcements(file_path: Path) -> list[Announcement]:
    """Load announcements from JSON, returning an empty list if absent."""
    try:
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError) as error:
        raise StorageError(f"Не удалось загрузить данные: {error}") from error
    if not isinstance(data, list):
        raise StorageError("Файл данных должен содержать список объявлений")
    try:
        return [Announcement.from_dict(item) for item in data]
    except (AnnouncementError, TypeError) as error:
        message = f"Некорректные данные объявлений: {error}"
        raise StorageError(message) from error


def save_announcements(
    file_path: Path,
    announcements: list[Announcement],
) -> None:
    """Save announcements to a UTF-8 JSON file."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8") as file:
            json.dump(
                [announcement.to_dict() for announcement in announcements],
                file,
                ensure_ascii=False,
                indent=2,
            )
    except OSError as error:
        raise StorageError(f"Не удалось сохранить данные: {error}") from error
