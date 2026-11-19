from django import forms
from django.core.exceptions import ValidationError

from portal.models import Announcement, Department


class AnnouncementFilterForm(forms.Form):
    """Validate filters used by the announcement list."""

    q = forms.CharField(
        required=False,
        label="Поиск",
        max_length=100,
    )
    title = forms.CharField(
        required=False,
        label="Заголовок",
        max_length=100,
    )
    date = forms.DateField(
        required=False,
        label="Дата активности",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.order_by("name"),
        required=False,
        label="Отдел",
        empty_label="Все отделы",
    )
    priority = forms.ChoiceField(
        required=False,
        label="Приоритет",
        choices=(("", "Любой"),) + tuple(
            (str(value), label)
            for value, label in Announcement.Priority.choices
        ),
    )
    status = forms.ChoiceField(
        required=False,
        label="Статус",
        choices=(
            ("all", "Все"),
            ("published", "Опубликованные"),
            ("draft", "Черновики"),
            ("withdrawn", "Снятые с публикации"),
        ),
    )
    sort = forms.ChoiceField(
        required=False,
        label="Сортировка",
        choices=tuple(
            (value, label)
            for value, label in (
                ("-priority", "Сначала высокий приоритет"),
                ("priority", "Сначала низкий приоритет"),
                ("-publish_date", "Сначала новые"),
                ("publish_date", "Сначала старые"),
                ("title", "Заголовок: А—Я"),
                ("-title", "Заголовок: Я—А"),
                ("department__name", "Отдел: А—Я"),
                ("-department__name", "Отдел: Я—А"),
            )
        ),
    )


class AnnouncementForm(forms.ModelForm):
    """Create or edit a corporate announcement."""

    class Meta:
        """Configure the announcement model form."""

        model = Announcement
        fields = (
            "title",
            "text",
            "department",
            "priority",
            "publish_date",
            "expiry_date",
            "status",
        )
        labels = {
            "title": "Заголовок объявления",
            "text": "Текст объявления",
            "department": "Отдел",
            "priority": "Приоритет",
            "publish_date": "Дата публикации",
            "expiry_date": "Дата окончания",
            "status": "Статус",
        }
        widgets = {
            "text": forms.Textarea(attrs={"rows": 6}),
            "publish_date": forms.DateInput(attrs={"type": "date"}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        publish_date = cleaned_data.get("publish_date")
        expiry_date = cleaned_data.get("expiry_date")
        if publish_date and expiry_date and expiry_date < publish_date:
            self.add_error(
                "expiry_date",
                "Дата окончания должна быть не раньше даты публикации.",
            )

        department = cleaned_data.get("department")
        status = cleaned_data.get("status")
        if (
            department
            and status == Announcement.Status.PUBLISHED
            and publish_date
            and expiry_date
        ):
            overlapping = Announcement.objects.filter(
                department=department,
                status=Announcement.Status.PUBLISHED,
                publish_date__lte=expiry_date,
                expiry_date__gte=publish_date,
            )
            if self.instance.pk:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            if overlapping.exists():
                raise ValidationError(
                    "В выбранный период в этом отделе уже есть "
                    "опубликованное объявление."
                )
        return cleaned_data
