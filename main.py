"""Console entry point for the corporate announcements project."""

from datetime import date
from pathlib import Path

from announcements import (
    active_announcements,
    create_announcement,
    format_priority_level,
    get_expiry_message,
    get_publication_status,
    sort_by_priority,
    validate_announcement_title,
)
from storage import StorageError, load_announcements, save_announcements
from utils import describe_function


DATA_FILE = Path(__file__).parent / "data" / "announcements.json"


def run() -> None:
    """Load, display and save announcements."""
    today = date(2026, 9, 19)
    try:
        announcements = load_announcements(DATA_FILE)
        if not announcements:
            announcements.append(
                create_announcement(
                    title="Плановое отключение VPN",
                    department="IT",
                    priority=3,
                    publish_date=date(2026, 9, 10),
                    expiry_date=date(2026, 9, 25),
                    is_published=True,
                )
            )
            save_announcements(DATA_FILE, announcements)

        announcement = announcements[0]
        expiry_date = date.fromisoformat(str(announcement["expiry_date"]))
        print("=== Сервис корпоративных объявлений ===")
        print(f"Заголовок: {announcement['title']}")
        print(f"Отдел: {announcement['department']}")
        print(f"Срок действия до: {expiry_date}")
        print()
        print(validate_announcement_title(str(announcement["title"])))
        print(format_priority_level(int(announcement["priority"])))
        print(get_publication_status(bool(announcement["is_published"])))
        print(get_expiry_message(expiry_date, today))
        active_count = len(list(active_announcements(announcements, today)))
        print(f"Активных объявлений: {active_count}")
        print(f"Функция: {describe_function(create_announcement)}")
        save_announcements(DATA_FILE, sort_by_priority(announcements))
    except (StorageError, ValueError) as error:
        print(f"Ошибка приложения: {error}")


if __name__ == "__main__":
    run()
