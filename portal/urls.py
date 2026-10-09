from django.urls import path

from portal import views

app_name = "portal"

urlpatterns = [
    path("", views.home, name="home"),
    path("announcements/", views.announcement_list, name="announcement_list"),
    path(
        "announcements/<int:announcement_id>/",
        views.announcement_detail,
        name="announcement_detail",
    ),
]
