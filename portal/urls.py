from django.urls import path

from portal import views

app_name = "portal"

urlpatterns = [
    path("", views.home, name="home"),
    path("announcements/", views.announcement_list, name="announcement_list"),
    path("statistics/", views.statistics, name="statistics"),
    path(
        "announcements/new/",
        views.announcement_create,
        name="announcement_create",
    ),
    path(
        "announcements/active/",
        views.active_announcement_list,
        name="active_announcement_list",
    ),
    path(
        "announcements/archive/",
        views.archived_announcement_list,
        name="archived_announcement_list",
    ),
    path(
        "announcements/<int:announcement_id>/",
        views.legacy_announcement_detail,
        name="announcement_detail_legacy",
    ),
    path(
        "announcements/<slug:slug>/",
        views.announcement_detail,
        name="announcement_detail",
    ),
    path(
        "announcements/<slug:slug>/edit/",
        views.announcement_edit,
        name="announcement_edit",
    ),
    path(
        "announcements/<slug:slug>/withdraw/",
        views.announcement_withdraw,
        name="announcement_withdraw",
    ),
]
