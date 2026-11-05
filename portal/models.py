from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
)
from django.db import models


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


class Announcement(models.Model):
    class Priority(models.IntegerChoices):
        """Supported announcement priority levels."""

        LOW = 1, "Низкий приоритет"
        MEDIUM = 2, "Средний приоритет"
        HIGH = 3, "Высокий приоритет"

    title = models.CharField(
        max_length=120,
        validators=[MinLengthValidator(5)],
    )
    text = models.TextField(blank=True)
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
    is_published = models.BooleanField(default=False)

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
                fields=["is_published", "publish_date", "expiry_date"]
            ),
            models.Index(fields=["priority", "id"]),
        ]

    def __str__(self) -> str:
        """Return a readable announcement summary."""
        return (
            f"{self.title} ({self.department}, "
            f"{self.get_priority_display()})"
        )

    @property
    def priority_label(self) -> str:
        """Expose the translated priority for templates."""
        return str(self.get_priority_display())

    def is_active_on(self, reference_date: date) -> bool:
        """Return whether the announcement is active on the given date."""
        return (
            self.is_published
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
