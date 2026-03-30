"""Тесты для валидатора EMAIL_TO."""

from app.core.config import Settings


class TestEmailToValidator:
    """Тесты валидации поля EMAIL_TO."""

    def test_parse_comma_separated_string_with_spaces(self):
        """Строка с пробелами после запятых."""
        settings = Settings(EMAIL_TO="admin@example.com, manager@example.com, test@test.ru")
        assert settings.EMAIL_TO == ["admin@example.com", "manager@example.com", "test@test.ru"]

    def test_parse_comma_separated_string_no_spaces(self):
        """Строка без пробелов."""
        settings = Settings(EMAIL_TO="admin@example.com,manager@example.com")
        assert settings.EMAIL_TO == ["admin@example.com", "manager@example.com"]

    def test_empty_string(self):
        """Пустая строка."""
        settings = Settings(EMAIL_TO="")
        assert settings.EMAIL_TO == []

    def test_none_value(self):
        """None значение."""
        settings = Settings(EMAIL_TO=None)
        assert settings.EMAIL_TO == []

    def test_list_from_tests(self):
        """Список из тестов (без конвертации)."""
        settings = Settings(EMAIL_TO=["test@example.com"])
        assert settings.EMAIL_TO == ["test@example.com"]

    def test_single_email_string(self):
        """Один email строкой."""
        settings = Settings(EMAIL_TO="admin@example.com")
        assert settings.EMAIL_TO == ["admin@example.com"]

    def test_use_email_with_valid_emails(self):
        """use_email=True при валидных EMAIL_TO."""
        settings = Settings(
            SMTP_HOST="smtp.example.com",
            SMTP_USER="user",
            SMTP_PASSWORD="pass",
            EMAIL_TO="admin@example.com",
        )
        assert settings.use_email is True

    def test_use_email_with_empty_string(self):
        """use_email=False при пустой строке EMAIL_TO."""
        settings = Settings(
            SMTP_HOST="smtp.example.com",
            SMTP_USER="user",
            SMTP_PASSWORD="pass",
            EMAIL_TO="",
        )
        assert settings.use_email is False

    def test_use_email_with_none(self):
        """use_email=False при None EMAIL_TO."""
        settings = Settings(
            SMTP_HOST="smtp.example.com",
            SMTP_USER="user",
            SMTP_PASSWORD="pass",
            EMAIL_TO=None,
        )
        assert settings.use_email is False

    def test_use_email_with_empty_list(self):
        """use_email=False при пустом списке."""
        settings = Settings(
            SMTP_HOST="smtp.example.com",
            SMTP_USER="user",
            SMTP_PASSWORD="pass",
            EMAIL_TO=[],
        )
        assert settings.use_email is False

    def test_trim_whitespace_from_emails(self):
        """Обрезка пробелов вокруг email."""
        settings = Settings(EMAIL_TO="  admin@example.com  ,  manager@example.com  ")
        assert settings.EMAIL_TO == ["admin@example.com", "manager@example.com"]
