import json
import tempfile
from datetime import date
from pathlib import Path

from django.test import TestCase, override_settings


class AnnouncementPageTests(TestCase):
    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        data_file = Path(temporary_directory.name) / "announcements.json"
        data_file.write_text(
            json.dumps(
                [
                    {
                        "title": "Важное объявление",
                        "text": "Информация для сотрудников.",
                        "department": "HR",
                        "priority": 3,
                        "publish_date": date.today().isoformat(),
                        "expiry_date": date.today().isoformat(),
                        "is_published": True,
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        settings_override = override_settings(ANNOUNCEMENTS_FILE=data_file)
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def test_homepage_shows_company_announcements(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Всё важное — в одном месте")
        self.assertContains(response, "Важное объявление")

    def test_announcement_list_shows_published_data(self) -> None:
        response = self.client.get("/announcements/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Важное объявление")

    def test_dynamic_announcement_url_shows_announcement(self) -> None:
        response = self.client.get("/announcements/1/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Важное объявление")
        self.assertContains(response, "Информация для сотрудников.")

    @override_settings(DEBUG=False)
    def test_unknown_announcement_uses_custom_not_found_page(self) -> None:
        response = self.client.get("/announcements/999/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(
            response,
            "Страница не найдена",
            status_code=404,
        )

        missing_page = self.client.get("/does-not-exist/")
        self.assertEqual(missing_page.status_code, 404)
        self.assertContains(
            missing_page,
            "Страница не найдена",
            status_code=404,
        )
