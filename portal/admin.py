from django.contrib import admin

from portal.models import Announcement, Department


class AnnouncementInline(admin.TabularInline):
    model = Announcement
    extra = 0
    fields = ("title", "priority", "status", "publish_date", "expiry_date")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = (AnnouncementInline,)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = (
        "title", "department", "priority", "status", "publish_date",
        "expiry_date", "title_length",
    )
    list_display_links = ("title",)
    list_editable = ("priority", "status")
    list_filter = ("department", "priority", "status")
    search_fields = ("title", "text", "department__name")
    date_hierarchy = "publish_date"
    ordering = ("-priority", "id")
    list_per_page = 20
    list_select_related = ("department",)
