import json
import sqlite3
import tempfile
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from django.contrib import admin
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.template.loader import get_template
from django.test import TestCase, override_settings
from django.urls import reverse

from portal.models import Announcement, Department


class AnnouncementPageTests(TestCase):
    def setUp(self) -> None:
        today = date.today()
        self.hr = Department.objects.create(name="Кадры")
        self.it = Department.objects.create(name="ИТ")
        self.finance = Department.objects.create(name="Финансы")
        self.active = Announcement.objects.create(
            title="Важное объявление",
            text="Информация для сотрудников отдела.",
            department=self.hr,
            priority=3,
            publish_date=today,
            expiry_date=today + timedelta(days=10),
            is_published=True,
        )
        self.archived = Announcement.objects.create(
            title="Архивное сообщение",
            text="Срок этого сообщения закончился.",
            department=self.it,
            priority=2,
            publish_date=today - timedelta(days=10),
            expiry_date=today - timedelta(days=1),
            is_published=True,
        )
        self.draft = Announcement.objects.create(
            title="Черновик отдела",
            text="Это объявление ещё не опубликовано.",
            department=self.finance,
            priority=1,
            publish_date=today,
            expiry_date=today + timedelta(days=10),
            is_published=False,
        )

    def test_homepage_uses_orm_counts_and_shows_announcements(self) -> None:
        response = self.client.get(reverse("portal:home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["announcement_count"], 3)
        self.assertEqual(response.context["active_count"], 1)
        self.assertContains(response, "Всё важное — в одном месте")
        self.assertContains(response, "Важное объявление")

    def test_list_filters_by_related_department_and_combined_conditions(
        self,
    ) -> None:
        response = self.client.get(
            reverse("portal:announcement_list"),
            {
                "department": self.hr.pk,
                "priority": "3",
                "status": "published",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["announcements"].object_list),
            [self.active],
        )
        self.assertContains(response, "Важное объявление")

    def test_search_matches_title_text_and_related_department(self) -> None:
        cases = (
            ({"title": "Важное"}, self.active),
            ({"q": "сотрудников"}, self.active),
            ({"q": "Финансы"}, self.draft),
        )
        for parameters, expected in cases:
            with self.subTest(parameters=parameters):
                response = self.client.get(
                    reverse("portal:announcement_list"),
                    parameters,
                )
                self.assertEqual(
                    list(response.context["announcements"].object_list),
                    [expected],
                )

    def test_status_filter_uses_exclude_for_drafts(self) -> None:
        response = self.client.get(
            reverse("portal:announcement_list"),
            {"status": "published"},
        )

        self.assertEqual(
            set(response.context["announcements"].object_list),
            {self.active, self.archived},
        )
        self.assertEqual(
            Announcement.objects.exclude(is_published=False).count(),
            2,
        )

    def test_lists_sort_by_fields_and_related_department(self) -> None:
        another_hr = Announcement.objects.create(
            title="Другое объявление",
            department=self.hr,
            priority=1,
            publish_date=date.today(),
            expiry_date=date.today() + timedelta(days=1),
        )
        title_response = self.client.get(
            reverse("portal:announcement_list"),
            {"sort": "title"},
        )
        department_response = self.client.get(
            reverse("portal:announcement_list"),
            {"sort": "department__name"},
        )

        self.assertEqual(
            [item.title for item in title_response.context["announcements"]],
            [
                "Архивное сообщение",
                "Важное объявление",
                "Другое объявление",
                "Черновик отдела",
            ],
        )
        self.assertEqual(
            [
                item.department.name
                for item in department_response.context["announcements"]
            ],
            ["ИТ", "Кадры", "Кадры", "Финансы"],
        )
        hr_ids = [
            item.pk
            for item in department_response.context["announcements"]
            if item.department == self.hr
        ]
        self.assertEqual(hr_ids, sorted([self.active.pk, another_hr.pk]))

    def test_active_and_archived_lists_filter_orm_objects(self) -> None:
        active_response = self.client.get(
            reverse("portal:active_announcement_list")
        )
        archive_response = self.client.get(
            reverse("portal:archived_announcement_list")
        )

        self.assertEqual(
            list(active_response.context["announcements"].object_list),
            [self.active],
        )
        self.assertEqual(
            list(archive_response.context["announcements"].object_list),
            [self.archived],
        )

    def test_active_list_accepts_date_and_handles_invalid_date(self) -> None:
        reference_date = date.today() - timedelta(days=5)
        response = self.client.get(
            reverse("portal:active_announcement_list"),
            {"date": reference_date.isoformat()},
        )
        invalid_response = self.client.get(
            reverse("portal:active_announcement_list"),
            {"date": "not-a-date"},
        )

        self.assertEqual(
            list(response.context["announcements"].object_list),
            [self.archived],
        )
        self.assertContains(response, f'value="{reference_date.isoformat()}"')
        self.assertTrue(invalid_response.context["invalid_date"])
        self.assertContains(invalid_response, "Некорректная дата")

    def test_invalid_filters_and_page_are_handled_safely(self) -> None:
        response = self.client.get(
            reverse("portal:announcement_list"),
            {
                "department": "999999",
                "priority": "999",
                "sort": "text;drop",
                "page": "not-a-number",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Некоторые параметры")
        self.assertEqual(response.context["selected_sort"], "-priority")
        self.assertEqual(response.context["page_obj"].number, 1)

    def test_pagination_preserves_query_parameters(self) -> None:
        for number in range(12):
            Announcement.objects.create(
                title=f"Дополнительное объявление {number:02}",
                department=self.hr,
                priority=2,
                publish_date=date.today(),
                expiry_date=date.today() + timedelta(days=1),
                is_published=True,
            )

        response = self.client.get(
            reverse("portal:announcement_list"),
            {
                "q": "Дополнительное",
                "title": "Дополнительное",
                "department": str(self.hr.pk),
                "priority": "2",
                "status": "published",
                "sort": "title",
                "page": "2",
            },
        )

        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(response.context["page_obj"].paginator.count, 12)
        previous_params = parse_qs(
            urlsplit(response.context["previous_url"]).query
        )
        self.assertEqual(previous_params["q"], ["Дополнительное"])
        self.assertEqual(previous_params["title"], ["Дополнительное"])
        self.assertEqual(previous_params["department"], [str(self.hr.pk)])
        self.assertEqual(previous_params["priority"], ["2"])
        self.assertEqual(previous_params["status"], ["published"])
        self.assertEqual(previous_params["sort"], ["title"])
        self.assertEqual(previous_params["page"], ["1"])

    def test_statistics_aggregate_and_annotate_related_groups(self) -> None:
        response = self.client.get(reverse("portal:statistics"))

        self.assertEqual(response.context["summary"]["total_count"], 3)
        self.assertEqual(response.context["summary"]["published_count"], 2)
        self.assertEqual(response.context["summary"]["active_count"], 1)
        self.assertEqual(response.context["summary"]["average_priority"], 2)
        departments = {
            row["name"]: row for row in response.context["departments"]
        }
        self.assertEqual(departments["Кадры"]["announcement_count"], 1)
        self.assertEqual(departments["Финансы"]["published_count"], 0)
        self.assertContains(response, "Статистика объявлений")

    def test_detail_loads_related_data_and_reverse_relation(self) -> None:
        related = Announcement.objects.create(
            title="Дополнительная новость",
            department=self.hr,
            priority=1,
            publish_date=date.today(),
            expiry_date=date.today() + timedelta(days=1),
        )
        response = self.client.get(
            reverse("portal:announcement_detail", args=[self.active.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["announcement"].department, self.hr)
        self.assertIn(
            "department",
            response.context["announcement"]._state.fields_cache,
        )
        self.assertEqual(
            list(response.context["related_announcements"]),
            [related],
        )
        self.assertEqual(self.hr.announcements.count(), 2)
        self.assertContains(response, "Другие объявления отдела")

    def test_department_values_and_empty_state(self) -> None:
        response = self.client.get(reverse("portal:announcement_list"))
        self.assertEqual(
            response.context["departments"][0],
            {"id": self.it.pk, "name": "ИТ"},
        )

        Announcement.objects.all().delete()
        empty_response = self.client.get(reverse("portal:announcement_list"))
        self.assertContains(empty_response, "Пока нет объявлений.")
        self.assertNotContains(empty_response, 'id="announcement-results"')

    def test_orm_crud_and_model_constraints(self) -> None:
        item = Announcement.objects.create(
            title="Новое объявление",
            department=self.hr,
            priority=2,
            publish_date=date.today(),
            expiry_date=date.today() + timedelta(days=2),
        )
        item.title = "Изменённое объявление"
        item.save(update_fields=["title"])
        self.assertTrue(
            Announcement.objects.filter(
                pk=item.pk,
                title="Изменённое объявление",
            ).exists()
        )
        item.delete()
        self.assertFalse(Announcement.objects.filter(pk=item.pk).exists())
        with self.assertRaises(ProtectedError):
            self.hr.delete()

        invalid = Announcement(
            title="Коротко",
            department=self.hr,
            priority=4,
            publish_date=date.today(),
            expiry_date=date.today() - timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            invalid.full_clean()
        invalid_department = Department(name="   ")
        with self.assertRaises(ValidationError):
            invalid_department.full_clean()

    def test_admin_provides_announcement_and_department_crud(self) -> None:
        self.assertIn(Announcement, admin.site._registry)
        self.assertIn(Department, admin.site._registry)
        self.assertTrue(
            hasattr(admin.site._registry[Announcement], "save_model")
        )
        response = self.client.get(reverse("admin:login"))
        self.assertEqual(response.status_code, 200)

    def test_templates_and_static_assets_are_available(self) -> None:
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
        self.assertContains(response, "Страница не найдена", status_code=404)
        missing_page = self.client.get("/does-not-exist/")
        self.assertContains(
            missing_page,
            "Страница не найдена",
            status_code=404,
        )


class LegacyImportCommandTests(TestCase):
    def test_sqlite_import_is_repeatable_and_preserves_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "legacy.sqlite3"
            connection = sqlite3.connect(source)
            connection.executescript(
                """
                CREATE TABLE departments (id INTEGER PRIMARY KEY, name TEXT);
                CREATE TABLE announcements (
                    id INTEGER PRIMARY KEY, title TEXT, text TEXT,
                    department_id INTEGER, priority INTEGER,
                    publish_date TEXT, expiry_date TEXT, is_published INTEGER
                );
                INSERT INTO departments VALUES (1, 'ИТ');
                INSERT INTO announcements VALUES (
                    47, 'Плановое отключение VPN', 'Работы ночью.',
                    1, 3, '2026-09-10', '2026-09-25', 1
                );
                """
            )
            connection.close()

            call_command(
                "import_legacy_announcements",
                source=source,
                verbosity=0,
            )
            call_command(
                "import_legacy_announcements",
                source=source,
                verbosity=0,
            )

        imported = Announcement.objects.get(pk=47)
        self.assertEqual(imported.title, "Плановое отключение VPN")
        self.assertEqual(imported.department.name, "ИТ")
        self.assertEqual(Announcement.objects.filter(pk=47).count(), 1)

    def test_json_import_is_repeatable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "announcements.json"
            source.write_text(
                json.dumps(
                    [
                        {
                            "title": "Новое сообщение",
                            "text": "Текст для сотрудников.",
                            "department": "Служба поддержки",
                            "priority": 2,
                            "publish_date": "2026-09-10",
                            "expiry_date": "2026-09-25",
                            "is_published": True,
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            call_command(
                "import_legacy_announcements",
                source=source,
                verbosity=0,
            )
            call_command(
                "import_legacy_announcements",
                source=source,
                verbosity=0,
            )

        self.assertEqual(
            Announcement.objects.filter(title="Новое сообщение").count(),
            1,
        )
