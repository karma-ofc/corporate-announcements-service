from datetime import date
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render

from announcements import (
    Announcement,
    active_announcements,
    sort_by_priority,
)
from storage import load_announcements


def _get_announcements() -> list[Announcement]:
    announcements = load_announcements(Path(settings.ANNOUNCEMENTS_FILE))
    return sort_by_priority(announcements)


def _number_announcements(
    announcements: list[Announcement],
    all_announcements: list[Announcement],
) -> list[tuple[int, Announcement]]:
    positions = {
        id(announcement): number
        for number, announcement in enumerate(all_announcements, start=1)
    }
    return [
        (positions[id(announcement)], announcement)
        for announcement in announcements
    ]


def home(request: HttpRequest) -> HttpResponse:
    announcements = _get_announcements()
    today = date.today()
    active_count = sum(1 for _ in active_announcements(announcements, today))
    return render(
        request,
        "portal/home.html",
        {
            "announcements": _number_announcements(
                announcements[:3],
                announcements,
            ),
            "announcement_count": len(announcements),
            "active_count": active_count,
        },
    )


def _announcement_list_page(
    request: HttpRequest,
    announcements: list[Announcement],
    title: str,
    description: str,
    empty_message: str,
    all_announcements: list[Announcement],
) -> HttpResponse:
    return render(
        request,
        "portal/announcement_list.html",
        {
            "announcements": _number_announcements(
                announcements,
                all_announcements,
            ),
            "page_title": title,
            "page_description": description,
            "empty_message": empty_message,
        },
    )


def announcement_list(request: HttpRequest) -> HttpResponse:
    announcements = _get_announcements()
    return _announcement_list_page(
        request,
        announcements,
        "Все объявления",
        "Сообщения и новости от отделов компании.",
        "Пока нет объявлений.",
        announcements,
    )


def active_announcement_list(request: HttpRequest) -> HttpResponse:
    all_announcements = _get_announcements()
    announcements = list(active_announcements(all_announcements, date.today()))
    return _announcement_list_page(
        request,
        announcements,
        "Активные объявления",
        "Опубликованные сообщения, срок действия которых ещё не истёк.",
        "Сейчас активных объявлений нет.",
        all_announcements,
    )


def archived_announcement_list(request: HttpRequest) -> HttpResponse:
    today = date.today()
    all_announcements = _get_announcements()
    announcements = [
        item
        for item in all_announcements
        if item.is_published and item.expiry_date < today
    ]
    return _announcement_list_page(
        request,
        announcements,
        "Архив объявлений",
        "Опубликованные сообщения с истёкшим сроком действия.",
        "В архиве пока нет объявлений.",
        all_announcements,
    )


def announcement_detail(
    request: HttpRequest,
    announcement_id: int,
) -> HttpResponse:
    announcements = _get_announcements()
    index = announcement_id - 1
    if index < 0 or index >= len(announcements):
        raise Http404("Объявление не найдено")
    announcement = announcements[index]
    return render(
        request,
        "portal/announcement_detail.html",
        {
            "announcement": announcement,
            "is_active": announcement.is_active(date.today()),
        },
    )


def page_not_found(
    request: HttpRequest,
    exception: Exception,
) -> HttpResponse:
    return render(request, "404.html", status=404)
