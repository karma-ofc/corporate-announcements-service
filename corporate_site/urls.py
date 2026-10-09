from django.urls import include, path

urlpatterns = [
    path("", include("portal.urls")),
]

handler404 = "portal.views.page_not_found"
