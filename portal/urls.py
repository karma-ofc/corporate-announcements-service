from django.urls import path

from portal import views

app_name = "portal"

urlpatterns = [
    path("", views.home, name="home"),
    path("announcements/", views.announcement_list, name="announcement_list"),
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
        views.announcement_detail,
        name="announcement_detail",
    ),
]
