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


def home(request: HttpRequest) -> HttpResponse:
    announcements = _get_announcements()
    today = date.today()
    active_count = sum(1 for _ in active_announcements(announcements, today))
    return render(
        request,
        "portal/home.html",
        {
            "announcements": announcements[:3],
            "announcement_count": len(announcements),
            "active_count": active_count,
        },
    )


def announcement_list(request: HttpRequest) -> HttpResponse:
    announcements = _get_announcements()
    return render(
        request,
        "portal/announcement_list.html",
        {
            "announcements": announcements,
            "today": date.today(),
        },
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
