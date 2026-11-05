from django.contrib import admin

from portal.models import Announcement, Department


class AnnouncementInline(admin.TabularInline):
    model = Announcement
    extra = 0


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = (AnnouncementInline,)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = (
        "title", "department", "priority", "publish_date", "expiry_date",
        "is_published",
    )
    list_filter = ("department", "priority", "is_published")
    search_fields = ("title", "text", "department__name")
    date_hierarchy = "publish_date"
    list_select_related = ("department",)
