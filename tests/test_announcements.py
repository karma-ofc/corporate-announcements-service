from datetime import date

import pytest

from announcements import (
    Announcement,
    AnnouncementError,
    active_announcements,
    create_announcement,
    get_expiry_message,
    sort_by_priority,
)
from storage import StorageError, load_announcements, save_announcements


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
    assert str(announcement).startswith("Плановое отключение VPN (IT")


def test_sort_by_priority_uses_descending_order() -> None:
    announcements = [
        create_announcement(
            "Обычное объявление", "IT", 1, date(2026, 9, 1), date(2026, 9, 30)
        ),
        create_announcement(
            "Срочное объявление", "IT", 3, date(2026, 9, 1), date(2026, 9, 30)
        ),
    ]
    sorted_announcements = sort_by_priority(announcements)
    assert [item.priority for item in sorted_announcements] == [3, 1]


def test_json_storage_round_trip(tmp_path) -> None:
    file_path = tmp_path / "announcements.json"
    data = [
        Announcement(
            "Тестовое объявление",
            "IT",
            2,
            date(2026, 9, 1),
            date(2026, 9, 30),
        )
    ]
    save_announcements(file_path, data)
    loaded = load_announcements(file_path)
    assert loaded[0].title == data[0].title
    assert loaded[0].publish_date == data[0].publish_date


def test_expiry_message_for_expired_announcement() -> None:
    assert get_expiry_message(
        date(2026, 9, 18), date(2026, 9, 19)
    ) == "Объявление истекло и должно быть снято с публикации"


def test_announcement_from_dict_creates_domain_object() -> None:
    announcement = Announcement.from_dict(
        {
            "title": "Важное объявление",
            "department": "HR",
            "priority": 2,
            "publish_date": "2026-09-01",
            "expiry_date": "2026-09-30",
            "is_published": True,
        }
    )
    assert isinstance(announcement, Announcement)
    assert announcement.is_active(date(2026, 9, 19))
    assert announcement.to_dict()["publish_date"] == "2026-09-01"


def test_load_announcements_rejects_invalid_record(tmp_path) -> None:
    file_path = tmp_path / "announcements.json"
    invalid_json = "[{\"title\": \"Неполная запись\"}]"
    file_path.write_text(invalid_json, encoding="utf-8")

    with pytest.raises(StorageError):
        load_announcements(file_path)
