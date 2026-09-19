"""Initial scenario for the Corporate Announcements Service (PR1)."""

from datetime import date


announcement_title = "Плановое отключение VPN"
department_name = "IT"
priority_code = 3
is_published = True
publish_date = date(2026, 9, 10)
expiry_date = date(2026, 9, 25)
today = date(2026, 9, 19)


def get_publication_status(is_published_flag: bool) -> str:
    """Return human-readable publication status for an announcement."""
    if is_published_flag:
        return "Объявление опубликовано и доступно сотрудникам"
    return "Объявление в черновике, сотрудники его не видят"


def format_priority_level(priority: int) -> str:
    """Map numeric priority (1–3) to a label."""
    if priority == 1:
        return "Низкий приоритет"
    if priority == 2:
        return "Средний приоритет"
    if priority == 3:
        return "Высокий приоритет"
    return "Неизвестный приоритет"


def validate_announcement_title(title: str) -> str:
    """Validate title length and non-empty value."""
    stripped = title.strip()
    if len(stripped) == 0:
        return "Ошибка: заголовок не может быть пустым"
    if len(stripped) < 5:
        return "Ошибка: заголовок слишком короткий (минимум 5 символов)"
    if len(stripped) > 120:
        return "Ошибка: заголовок слишком длинный (максимум 120 символов)"
    return "Заголовок прошёл проверку"


def get_expiry_message(expiry: date, reference: date) -> str:
    """Describe how many days remain until the announcement expires."""
    days_left = (expiry - reference).days
    if days_left < 0:
        return "Объявление истекло и должно быть снято с публикации"
    if days_left == 0:
        return "Объявление истекает сегодня"
    return f"До истечения объявления осталось {days_left} дн."


print("=== Сервис корпоративных объявлений (начальный сценарий) ===")
print(f"Заголовок: {announcement_title}")
print(f"Отдел: {department_name}")
print(f"Дата публикации: {publish_date}")
print(f"Срок действия до: {expiry_date}")
print()
print(validate_announcement_title(announcement_title))
print(format_priority_level(priority_code))
print(get_publication_status(is_published))
print(get_expiry_message(expiry_date, today))
