"""Business logic and object model for corporate announcements."""

from datetime import date
from typing import Any, Iterator, Mapping


class AnnouncementError(ValueError):
    """Raised when announcement data is invalid."""


def get_publication_status(is_published_flag: bool) -> str:
    """Return a human-readable publication status."""
    if is_published_flag:
        return "Объявление опубликовано и доступно сотрудникам"
    return "Объявление в черновике, сотрудники его не видят"


def format_priority_level(priority: int) -> str:
    """Map a numeric priority from 1 to 3 to a label."""
    priority_levels = {
        1: "Низкий приоритет",
        2: "Средний приоритет",
        3: "Высокий приоритет",
    }
    return priority_levels.get(priority, "Неизвестный приоритет")


def validate_announcement_title(title: str) -> str:
    """Validate a title and return a console-friendly message."""
    stripped = title.strip()
    if not stripped:
        return "Ошибка: заголовок не может быть пустым"
    if len(stripped) < 5:
        return "Ошибка: заголовок слишком короткий (минимум 5 символов)"
    if len(stripped) > 120:
        return "Ошибка: заголовок слишком длинный (максимум 120 символов)"
    return "Заголовок прошёл проверку"


def get_expiry_message(expiry: date, reference: date) -> str:
    """Describe how many days remain until an announcement expires."""
    days_left = (expiry - reference).days
    if days_left < 0:
        return "Объявление истекло и должно быть снято с публикации"
    if days_left == 0:
        return "Объявление истекает сегодня"
    return f"До истечения объявления осталось {days_left} дн."


class Announcement:
    """A domain object describing one corporate announcement."""

    def __init__(
        self,
        title: str,
        department: str,
        priority: int,
        publish_date: date,
        expiry_date: date,
        is_published: bool = False,
        text: str = "",
    ) -> None:
        title_message = validate_announcement_title(title)
        if title_message != "Заголовок прошёл проверку":
            raise AnnouncementError(title_message)
        if not department.strip():
            raise AnnouncementError("Отдел не может быть пустым")
        if priority not in (1, 2, 3):
            raise AnnouncementError("Приоритет должен быть от 1 до 3")
        if expiry_date < publish_date:
            raise AnnouncementError(
                "Дата окончания не может быть раньше даты публикации"
            )
        self.title = title.strip()
        self.text = text.strip()
        self.department = department.strip()
        self.priority = priority
        self.publish_date = publish_date
        self.expiry_date = expiry_date
        self.is_published = is_published

    def __str__(self) -> str:
        """Return a human-readable summary of the announcement."""
        return (
            f"{self.title} ({self.department}, "
            f"{format_priority_level(self.priority)})"
        )

    def is_active(self, reference: date) -> bool:
        """Return whether the announcement is published and not expired."""
        return self.is_published and self.expiry_date >= reference

    def to_dict(self) -> dict[str, object]:
        """Convert the object to the JSON-compatible storage format."""
        return {
            "title": self.title,
            "text": self.text,
            "department": self.department,
            "priority": self.priority,
            "publish_date": self.publish_date.isoformat(),
            "expiry_date": self.expiry_date.isoformat(),
            "is_published": self.is_published,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Announcement":
        """Build an announcement object from one JSON record."""
        try:
            return cls(
                title=str(data["title"]),
                text=str(data.get("text", "")),
                department=str(data["department"]),
                priority=int(data["priority"]),
                publish_date=date.fromisoformat(str(data["publish_date"])),
                expiry_date=date.fromisoformat(str(data["expiry_date"])),
                is_published=bool(data.get("is_published", False)),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise AnnouncementError(
                "Некорректная запись объявления в JSON"
            ) from error


def create_announcement(
    title: str,
    department: str,
    priority: int,
    publish_date: date,
    expiry_date: date,
    is_published: bool = False,
    text: str = "",
) -> Announcement:
    """Create and validate an announcement object."""
    return Announcement(
        title=title,
        department=department,
        priority=priority,
        publish_date=publish_date,
        expiry_date=expiry_date,
        is_published=is_published,
        text=text,
    )


def active_announcements(
    announcements: list[Announcement],
    reference: date,
) -> Iterator[Announcement]:
    """Yield published announcements that have not expired."""
    for announcement in announcements:
        if announcement.is_active(reference):
            yield announcement


def sort_by_priority(announcements: list[Announcement]) -> list[Announcement]:
    """Return announcements from highest to lowest priority."""
    return sorted(
        announcements,
        key=lambda announcement: announcement.priority,
        reverse=True,
    )
