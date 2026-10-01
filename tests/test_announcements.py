from datetime import date

import pytest

from announcements import (
    AnnouncementError,
    active_announcements,
    create_announcement,
    get_expiry_message,
    sort_by_priority,
)
from storage import load_announcements, save_announcements


def test_create_announcement_validates_dates() -> None:
    with pytest.raises(AnnouncementError):
        create_announcement(
            "VPN",
            "IT",
            3,
            date(2026, 9, 25),
            date(2026, 9, 10),
        )


def test_active_announcements_is_a_filtered_generator() -> None:
    announcement = create_announcement(
        "Плановое отключение VPN",
        "IT",
        3,
        date(2026, 9, 10),
        date(2026, 9, 25),
        is_published=True,
    )
    result = list(active_announcements([announcement], date(2026, 9, 19)))
    assert result == [announcement]


def test_sort_by_priority_uses_descending_order() -> None:
    announcements = [
        {"priority": 1, "title": "Обычное"},
        {"priority": 3, "title": "Срочное"},
    ]
    sorted_announcements = sort_by_priority(announcements)
    assert [item["priority"] for item in sorted_announcements] == [3, 1]


def test_json_storage_round_trip(tmp_path) -> None:
    file_path = tmp_path / "announcements.json"
    data = [{"title": "Тест", "priority": 2}]
    save_announcements(file_path, data)
    assert load_announcements(file_path) == data


def test_expiry_message_for_expired_announcement() -> None:
    assert get_expiry_message(
        date(2026, 9, 18), date(2026, 9, 19)
    ) == "Объявление истекло и должно быть снято с публикации"
