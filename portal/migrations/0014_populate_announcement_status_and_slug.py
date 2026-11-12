from django.db import migrations
from django.utils.text import slugify
from unidecode import unidecode


def populate_status_and_slug(apps, schema_editor):
    Announcement = apps.get_model("portal", "Announcement")
    database = schema_editor.connection.alias
    announcements = Announcement.objects.using(database)

    announcements.filter(is_published=True).update(status="published")
    announcements.filter(is_published=False).update(status="draft")

    for announcement in announcements.order_by("pk").iterator():
        base_slug = slugify(unidecode(announcement.title)) or "announcement"
        suffix = f"-{announcement.pk}"
        announcement.slug = f"{base_slug[: 180 - len(suffix)]}{suffix}"
        announcement.save(using=database, update_fields=["slug"])


def restore_published_flag(apps, schema_editor):
    Announcement = apps.get_model("portal", "Announcement")
    database = schema_editor.connection.alias
    announcements = Announcement.objects.using(database)

    announcements.filter(status="published").update(is_published=True)
    announcements.exclude(status="published").update(is_published=False)


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0013_add_announcement_status_slug_and_title_length"),
    ]

    operations = [
        migrations.RunPython(
            populate_status_and_slug,
            restore_published_flag,
        ),
    ]
