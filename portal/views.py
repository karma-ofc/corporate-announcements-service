from datetime import date
from pathlib import Path
import sqlite3

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render

from announcements import format_priority_level
from db.database import (
    get_announcement,
    get_statistics,
    list_announcements,
    list_announcements_active_on,
    list_archived_announcements,
)


def _database_path() -> Path:
    return Path(settings.ANNOUNCEMENTS_DB_PATH)


def _as_announcement(row: sqlite3.Row) -> dict[str, object]:
    announcement = dict(row)
    announcement["publish_date"] = date.fromisoformat(
        announcement["publish_date"]
    )
    announcement["expiry_date"] = date.fromisoformat(
        announcement["expiry_date"]
    )
    announcement["is_published"] = bool(announcement["is_published"])
    announcement["priority_label"] = format_priority_level(
        announcement["priority"]
    )
    return announcement


def _get_announcements() -> list[dict[str, object]]:
    rows = list_announcements(_database_path())
    return [_as_announcement(row) for row in rows]


def home(request: HttpRequest) -> HttpResponse:
    announcements = _get_announcements()
    active_count = len(
        list_announcements_active_on(date.today(), _database_path())
    )
    return render(
        request,
        "portal/home.html",
        {
            "announcements": announcements[:3],
            "announcement_count": len(announcements),
            "active_count": active_count,
        },
    )


def _announcement_list_page(
    request: HttpRequest,
    announcements: list[dict[str, object]],
    title: str,
    description: str,
    empty_message: str,
    **context: object,
) -> HttpResponse:
    return render(
        request,
        "portal/announcement_list.html",
        {
            "announcements": announcements,
            "page_title": title,
            "page_description": description,
            "empty_message": empty_message,
            **context,
        },
    )


def announcement_list(request: HttpRequest) -> HttpResponse:
    return _announcement_list_page(
        request,
        [
            _as_announcement(row)
            for row in list_announcements(_database_path())
        ],
        "Все объявления",
        "Сообщения и новости от отделов компании.",
        "Пока нет объявлений.",
    )


def active_announcement_list(request: HttpRequest) -> HttpResponse:
    date_value = request.GET.get("date", "").strip()
    invalid_date = False
    if date_value:
        try:
            reference_date = date.fromisoformat(date_value)
        except ValueError:
            reference_date = date.today()
            invalid_date = True
    else:
        reference_date = date.today()
    announcements = [
        _as_announcement(row)
        for row in list_announcements_active_on(
            reference_date, _database_path()
        )
    ]
    return _announcement_list_page(
        request,
        announcements,
        "Активные объявления",
        "Опубликованные сообщения, действующие на выбранную дату.",
        "На эту дату активных объявлений нет.",
        selected_date=reference_date.isoformat(),
        invalid_date=invalid_date,
    )


def archived_announcement_list(request: HttpRequest) -> HttpResponse:
    announcements = [
        _as_announcement(row)
        for row in list_archived_announcements(date.today(), _database_path())
    ]
    return _announcement_list_page(
        request,
        announcements,
        "Архив объявлений",
        "Опубликованные сообщения с истёкшим сроком действия.",
        "В архиве пока нет объявлений.",
    )


def statistics(request: HttpRequest) -> HttpResponse:
    report = get_statistics(date.today(), _database_path())
    return render(request, "portal/statistics.html", report)


def announcement_detail(
    request: HttpRequest,
    announcement_id: int,
) -> HttpResponse:
    row = get_announcement(announcement_id, _database_path())
    if row is None:
        raise Http404("Объявление не найдено")
    announcement = _as_announcement(row)
    is_active = (
        announcement["is_published"]
        and announcement["publish_date"] <= date.today()
        and announcement["expiry_date"] >= date.today()
    )
    return render(
        request,
        "portal/announcement_detail.html",
        {"announcement": announcement, "is_active": is_active},
    )


def page_not_found(
    request: HttpRequest,
    exception: Exception,
) -> HttpResponse:
    return render(request, "404.html", status=404)
