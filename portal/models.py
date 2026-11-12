from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
)
from django.db import models
from django.db.models.functions import Length
from django.urls import reverse
from django.utils.text import slugify
from unidecode import unidecode


class Department(models.Model):
    """A company department that publishes announcements."""

    name = models.CharField(
        max_length=100,
        unique=True,
        validators=[MinLengthValidator(1)],
    )

    class Meta:
        """Order departments by their display names."""

        ordering = ["name"]

    def clean(self) -> None:
        """Normalize and validate the department name."""
        super().clean()
        self.name = (self.name or "").strip()
        if not self.name:
            raise ValidationError(
                {"name": "Название отдела не может быть пустым."}
            )

    def __str__(self) -> str:
        """Return the department name for display."""
        return self.name


class AnnouncementQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=self.model.Status.PUBLISHED)

    def drafts(self):
        return self.filter(status=self.model.Status.DRAFT)

    def withdrawn(self):
        return self.filter(status=self.model.Status.WITHDRAWN)

    def active_on(self, reference_date: date):
        return self.published().filter(
            publish_date__lte=reference_date,
            expiry_date__gte=reference_date,
        )


class AnnouncementManager(
    models.Manager.from_queryset(AnnouncementQuerySet)
):
    pass


class Announcement(models.Model):
    class Status(models.TextChoices):
        """Publication lifecycle states for an announcement."""

        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликовано"
        WITHDRAWN = "withdrawn", "Снято с публикации"

    class Priority(models.IntegerChoices):
        """Supported announcement priority levels."""

        LOW = 1, "Низкий приоритет"
        MEDIUM = 2, "Средний приоритет"
        HIGH = 3, "Высокий приоритет"

    objects = AnnouncementManager()

    title = models.CharField(
        max_length=120,
        validators=[MinLengthValidator(5)],
        help_text="Краткий заголовок объявления (от 5 до 120 символов).",
    )
    slug = models.SlugField(
        max_length=180,
        unique=True,
        blank=True,
        editable=False,
        verbose_name="URL-идентификатор",
    )
    title_length = models.GeneratedField(
        expression=Length("title"),
        output_field=models.PositiveIntegerField(),
        db_persist=False,
        editable=False,
        verbose_name="Длина заголовка",
    )
    text = models.TextField(blank=True)
# Привязка к отделу, который публикует объявление
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="announcements",
    )
    priority = models.PositiveSmallIntegerField(
        choices=Priority.choices,
        default=Priority.MEDIUM,
        validators=[MinValueValidator(1), MaxValueValidator(3)],
    )
    publish_date = models.DateField()
    expiry_date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Статус",
    )

    class Meta:
        """Define announcement ordering, database constraints, and indexes."""

        ordering = ["-priority", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(priority__gte=1, priority__lte=3),
                name="announcement_priority_1_to_3",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    expiry_date__gte=models.F("publish_date")
                ),
                name="announcement_expiry_after_publish",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "publish_date", "expiry_date"]
            ),
            models.Index(fields=["priority", "id"]),
        ]

    def __str__(self) -> str:
        """Return a readable announcement summary."""
        return (
            f"{self.title} ({self.department}, "
            f"{self.get_priority_display()})"
        )

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(unidecode(self.title)) or "announcement"
            if self.pk is None:
                super().save(*args, **kwargs)
                suffix = f"-{self.pk}"
                self.slug = f"{base_slug[: 180 - len(suffix)]}{suffix}"
                super().save(update_fields=["slug"])
                return
            suffix = f"-{self.pk}"
            self.slug = f"{base_slug[: 180 - len(suffix)]}{suffix}"
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"slug"}
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse(
            "portal:announcement_detail",
            kwargs={"slug": self.slug},
        )

    @property
    def priority_label(self) -> str:
        """Expose the translated priority for templates."""
        return str(self.get_priority_display())

    def is_active_on(self, reference_date: date) -> bool:
        """Return whether the announcement is active on the given date."""
        return (
            self.status == self.Status.PUBLISHED
            and self.publish_date <= reference_date
            and self.expiry_date >= reference_date
        )

    def clean(self) -> None:
        """Normalize the title and validate the announcement date range."""
        super().clean()
        self.title = (self.title or "").strip()
        if len(self.title) < 5:
            raise ValidationError(
                {"title": "Заголовок должен содержать не менее 5 символов."}
            )
        if self.expiry_date and self.publish_date:
            if self.expiry_date < self.publish_date:
                raise ValidationError(
                    {
                        "expiry_date": (
                            "Дата окончания должна быть не раньше "
                            "даты публикации."
                        )
                    }
                )
