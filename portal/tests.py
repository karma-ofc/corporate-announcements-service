import json
import tempfile
from datetime import date, timedelta
from pathlib import Path

from django.contrib.staticfiles import finders
from django.template.loader import get_template
from django.test import TestCase, override_settings
from django.urls import reverse


class AnnouncementPageTests(TestCase):
    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.data_file = Path(temporary_directory.name) / "announcements.json"
        today = date.today()
        self.data_file.write_text(
            json.dumps(
                [
                    {
                        "title": "Важное объявление",
                        "text": "Информация для сотрудников.",
                        "department": "HR",
                        "priority": 3,
                        "publish_date": today.isoformat(),
                        "expiry_date": today.isoformat(),
                        "is_published": True,
                    },
                    {
                        "title": "Архивное объявление",
                        "text": "Срок этого объявления закончился.",
                        "department": "IT",
                        "priority": 2,
                        "publish_date": (
                            today - timedelta(days=10)
                        ).isoformat(),
                        "expiry_date": (
                            today - timedelta(days=1)
                        ).isoformat(),
                        "is_published": True,
                    },
                    {
                        "title": "Черновик отдела",
                        "text": "Это объявление не опубликовано.",
                        "department": "Finance",
                        "priority": 1,
                        "publish_date": today.isoformat(),
                        "expiry_date": (
                            today + timedelta(days=10)
                        ).isoformat(),
                        "is_published": False,
                    },
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        settings_override = override_settings(
            ANNOUNCEMENTS_FILE=self.data_file
        )
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def test_homepage_shows_company_announcements(self) -> None:
        response = self.client.get(reverse("portal:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Всё важное — в одном месте")
        self.assertContains(response, "Важное объявление")
        self.assertContains(
            response,
            'src="/static/portal/announcements.svg"',
        )

    def test_announcement_list_shows_all_records_and_search(self) -> None:
        response = self.client.get(reverse("portal:announcement_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Важное объявление")
        self.assertContains(response, "Архивное объявление")
        self.assertContains(response, "Черновик отдела")
        self.assertContains(response, 'id="announcement-search"')

    def test_active_and_archived_lists_filter_the_json_objects(self) -> None:
        active_response = self.client.get(
            reverse("portal:active_announcement_list")
        )
        archive_response = self.client.get(
            reverse("portal:archived_announcement_list")
        )

        self.assertContains(active_response, "Важное объявление")
        self.assertNotContains(
            active_response,
            "Архивное объявление",
        )
        self.assertContains(archive_response, "Архивное объявление")
        self.assertNotContains(archive_response, "Черновик отдела")
        self.assertContains(archive_response, 'href="/announcements/2/"')

    def test_dynamic_announcement_url_shows_announcement(self) -> None:
        response = self.client.get(
            reverse("portal:announcement_detail", args=[1])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Важное объявление")
        self.assertContains(response, "Информация для сотрудников.")

    def test_empty_announcement_list_has_an_empty_state(self) -> None:
        self.data_file.write_text("[]", encoding="utf-8")

        response = self.client.get(reverse("portal:announcement_list"))

        self.assertContains(response, "Пока нет объявлений.")
        self.assertNotContains(response, 'id="announcement-results"')

    def test_templates_are_loaded_from_project_directory(self) -> None:
        response = self.client.get(reverse("portal:home"))
        template = get_template("portal/home.html")

        self.assertEqual(
            Path(template.origin.name),
            Path(__file__).resolve().parent.parent
            / "templates"
            / "portal"
            / "home.html",
        )
        self.assertTemplateUsed(response, "portal/partials/navigation.html")

    def test_static_css_javascript_and_image_are_available(self) -> None:
        for asset in (
            "portal/style.css",
            "portal/app.js",
            "portal/announcements.svg",
        ):
            with self.subTest(asset=asset):
                self.assertIsNotNone(finders.find(asset))

    @override_settings(DEBUG=False)
    def test_unknown_announcement_uses_custom_not_found_page(self) -> None:
        response = self.client.get(
            reverse("portal:announcement_detail", args=[999])
        )

        self.assertContains(
            response,
            "Страница не найдена",
            status_code=404,
        )

        missing_page = self.client.get("/does-not-exist/")
        self.assertContains(
            missing_page,
            "Страница не найдена",
            status_code=404,
        )
