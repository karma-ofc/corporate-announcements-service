from portal.models import Announcement


def announcement_context(request):
    return {
        "site_name": "Внутри компании",
        "announcements_count": Announcement.objects.count(),
    }
