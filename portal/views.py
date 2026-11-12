from datetime import date

from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from portal.models import Announcement, Department

PAGE_SIZE = 10
SORT_OPTIONS = {
    "-priority": "Сначала высокий приоритет",
    "priority": "Сначала низкий приоритет",
    "-publish_date": "Сначала новые",
    "publish_date": "Сначала старые",
    "title": "Заголовок: А—Я",
    "-title": "Заголовок: Я—А",
    "department__name": "Отдел: А—Я",
    "-department__name": "Отдел: Я—А",
}
SORT_FIELDS = {
    "-priority": ("-priority", "id"),
    "priority": ("priority", "id"),
    "-publish_date": ("-publish_date", "id"),
    "publish_date": ("publish_date", "id"),
    "title": ("title",),
    "-title": ("-title",),
    "department__name": ("department__name", "id"),
    "-department__name": ("-department__name", "id"),
}


def home(request: HttpRequest) -> HttpResponse:
    """Render recent announcements and aggregate counters."""
    today = date.today()
    announcements = Announcement.objects.select_related("department").all()[
        :3
    ]
    totals = Announcement.objects.aggregate(
        announcement_count=Count("pk"),
        active_count=Count(
            "pk",
            filter=Q(
                status=Announcement.Status.PUBLISHED,
                publish_date__lte=today,
                expiry_date__gte=today,
            ),
        ),
    )
    return render(
        request,
        "portal/home.html",
        {"announcements": announcements, **totals},
    )


def _build_page_url(query_string: str, page_number: int) -> str:
    """Keep active filters and sorting in pagination links."""
    suffix = f"{query_string}&" if query_string else ""
    return f"?{suffix}page={page_number}"


def _announcement_list_page(
    request: HttpRequest,
    queryset: QuerySet[Announcement],
    title: str,
    description: str,
    empty_message: str,
    *,
    selected_date: date | None = None,
    invalid_date: bool = False,
) -> HttpResponse:
    """Apply validated list filters and render one paginated result page."""
    search = request.GET.get("q", "").strip()[:100]
    title_search = request.GET.get("title", "").strip()[:100]
    invalid_filters = False
    if title_search:
        queryset = queryset.filter(title__icontains=title_search)
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(text__icontains=search)
            | Q(department__name__icontains=search)
        )

    department_id = request.GET.get("department", "").strip()
    if department_id:
        department_name = None
        if department_id.isdecimal():
            department_name = Department.objects.filter(
                pk=department_id
            ).values_list("name", flat=True).first()
        if department_name is not None:
            queryset = queryset.filter(department__name=department_name)
        else:
            department_id = ""
            invalid_filters = True

    priority = request.GET.get("priority", "").strip()
    if priority:
        if priority in {"1", "2", "3"}:
            queryset = queryset.filter(priority=int(priority))
        else:
            priority = ""
            invalid_filters = True

    status = request.GET.get("status", "all").strip()
    if status == "published":
        queryset = queryset.published()
    elif status == "draft":
        queryset = queryset.drafts()
    elif status == "withdrawn":
        queryset = queryset.withdrawn()
    elif status != "all":
        status = "all"
        invalid_filters = True

    requested_sort = request.GET.get("sort", "-priority").strip()
    if requested_sort not in SORT_OPTIONS:
        requested_sort = "-priority"
        invalid_filters = True
    queryset = queryset.order_by(*SORT_FIELDS[requested_sort])

    paginator = Paginator(queryset, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page", "1"))
    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_string = query_params.urlencode()
    page_links = [
        {
            "number": number,
            "url": _build_page_url(query_string, number),
            "current": number == page_obj.number,
        }
        for number in paginator.page_range
    ]
    departments = Department.objects.order_by("name").values("id", "name")
    return render(
        request,
        "portal/announcement_list.html",
        {
            "announcements": page_obj,
            "page_obj": page_obj,
            "page_links": page_links,
            "previous_url": (
                _build_page_url(
                    query_string,
                    page_obj.previous_page_number(),
                )
                if page_obj.has_previous()
                else ""
            ),
            "next_url": (
                _build_page_url(
                    query_string,
                    page_obj.next_page_number(),
                )
                if page_obj.has_next()
                else ""
            ),
            "page_title": title,
            "page_description": description,
            "empty_message": empty_message,
            "departments": departments,
            "search_query": search,
            "title_search": title_search,
            "selected_department": department_id,
            "selected_priority": priority,
            "selected_status": status,
            "selected_sort": requested_sort,
            "sort_options": SORT_OPTIONS,
            "invalid_filters": invalid_filters,
            "selected_date": (
                selected_date.isoformat() if selected_date else ""
            ),
            "invalid_date": invalid_date,
        },
    )


def announcement_list(request: HttpRequest) -> HttpResponse:
    """Show all announcements with search, filters, sorting, and paging."""
    return _announcement_list_page(
        request,
        Announcement.objects.select_related("department").all(),
        "Все объявления",
        "Новости и сообщения от отделов компании.",
        "Пока нет объявлений.",
    )


def active_announcement_list(request: HttpRequest) -> HttpResponse:
    """Show published announcements active on a selected date."""
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

    queryset = Announcement.objects.active_on(reference_date).select_related(
        "department"
    )
    return _announcement_list_page(
        request,
        queryset,
        "Активные объявления",
        "Опубликованные сообщения, действующие на выбранную дату.",
        "На эту дату активных объявлений нет.",
        selected_date=reference_date,
        invalid_date=invalid_date,
    )


def archived_announcement_list(request: HttpRequest) -> HttpResponse:
    """Show published announcements whose expiry date has passed."""
    queryset = Announcement.objects.published().select_related(
        "department"
    ).filter(expiry_date__lt=date.today())
    return _announcement_list_page(
        request,
        queryset,
        "Архив объявлений",
        "Опубликованные объявления с истёкшим сроком действия.",
        "В архиве пока нет объявлений.",
    )


def statistics(request: HttpRequest) -> HttpResponse:
    """Render summary and grouped statistics calculated by the ORM."""
    today = date.today()
    summary = Announcement.objects.aggregate(
        total_count=Count("pk"),
        published_count=Count(
            "pk",
            filter=Q(status=Announcement.Status.PUBLISHED),
        ),
        draft_count=Count(
            "pk",
            filter=Q(status=Announcement.Status.DRAFT),
        ),
        withdrawn_count=Count(
            "pk",
            filter=Q(status=Announcement.Status.WITHDRAWN),
        ),
        active_count=Count(
            "pk",
            filter=Q(
                status=Announcement.Status.PUBLISHED,
                publish_date__lte=today,
                expiry_date__gte=today,
            ),
        ),
        average_priority=Avg("priority"),
    )
    departments = (
        Department.objects.annotate(
            announcement_count=Count("announcements"),
            published_count=Count(
                "announcements",
                filter=Q(
                    announcements__status=Announcement.Status.PUBLISHED
                ),
            ),
        )
        .values("name", "announcement_count", "published_count")
        .order_by("-announcement_count", "name")
    )
    priorities = (
        Announcement.objects.values("priority")
        .annotate(announcement_count=Count("pk"))
        .order_by("-priority")
    )
    return render(
        request,
        "portal/statistics.html",
        {
            "summary": summary,
            "departments": departments,
            "priorities": priorities,
        },
    )


def announcement_detail(
    request: HttpRequest,
    slug: str,
) -> HttpResponse:
    """Show an announcement, its department, and related announcements."""
    announcement = get_object_or_404(
        Announcement.objects.select_related("department"),
        slug=slug,
    )
    related_announcements = (
        announcement.department.announcements.exclude(pk=announcement.pk)
        .select_related("department")
        .order_by("-priority", "id")[:3]
    )
    return render(
        request,
        "portal/announcement_detail.html",
        {
            "announcement": announcement,
            "is_active": announcement.is_active_on(date.today()),
            "related_announcements": related_announcements,
        },
    )


def legacy_announcement_detail(
    request: HttpRequest,
    announcement_id: int,
) -> HttpResponse:
    """Redirect old ID-based announcement URLs to their canonical slug."""
    announcement = get_object_or_404(Announcement, pk=announcement_id)
    return redirect(announcement)


def page_not_found(
    request: HttpRequest,
    exception: Exception,
) -> HttpResponse:
    """Render the project's custom not-found page."""
    return render(request, "404.html", status=404)
