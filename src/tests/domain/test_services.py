"""
Tests for Domain Services.

Test Isolation Principle:
- Service tests are database-independent
- Only business logic is tested
"""

from app.domain.services.services import FingerprintService, MaskingService


class TestFingerprintService:
    """Tests for fingerprinting service."""

    def setup_method(self):
        """Setup service before each test."""
        self.service = FingerprintService()

    def test_same_errors_same_fingerprint(self):
        """Same errors should have same fingerprint."""
        error_a = {
            "exception_type": "ValueError",
            "message": "Invalid value",
            "stack_trace": "File 'app.py', line 10",
        }
        error_b = {
            "exception_type": "ValueError",
            "message": "Invalid value",
            "stack_trace": "File 'app.py', line 10",
        }

        fp_a = self.service.generate(**error_a)
        fp_b = self.service.generate(**error_b)

        assert fp_a == fp_b

    def test_different_errors_different_fingerprint(self):
        """Different errors should have different fingerprint."""
        error_a = {
            "exception_type": "ValueError",
            "message": "Invalid value",
            "stack_trace": "",
        }
        error_b = {
            "exception_type": "TypeError",
            "message": "Wrong type",
            "stack_trace": "",
        }

        fp_a = self.service.generate(**error_a)
        fp_b = self.service.generate(**error_b)

        assert fp_a != fp_b

    def test_fingerprint_ignores_line_numbers(self):
        """Fingerprint should ignore line numbers."""
        error_a = {
            "exception_type": "ValueError",
            "message": "Invalid value",
            "stack_trace": "File 'app.py', line 10",
        }
        error_b = {
            "exception_type": "ValueError",
            "message": "Invalid value",
            "stack_trace": "File 'app.py', line 999",
        }

        fp_a = self.service.generate(**error_a)
        fp_b = self.service.generate(**error_b)

        assert fp_a == fp_b

    def test_fingerprint_ignores_numeric_values(self):
        """Fingerprint should ignore numbers in message."""
        error_a = {
            "exception_type": "ValueError",
            "message": "User 123 not found",
            "stack_trace": "",
        }
        error_b = {
            "exception_type": "ValueError",
            "message": "User 999 not found",
            "stack_trace": "",
        }

        fp_a = self.service.generate(**error_a)
        fp_b = self.service.generate(**error_b)

        assert fp_a == fp_b

    def test_empty_stack_trace(self):
        """Test with empty stack trace."""
        error = {
            "exception_type": "Exception",
            "message": "Test error",
            "stack_trace": None,
        }

        fingerprint = self.service.generate(**error)

        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64  # SHA256 = 64 hex characters


class TestMaskingService:
    """Tests for masking service."""

    def setup_method(self):
        """Setup service before each test."""
        self.service = MaskingService()

    def test_mask_token(self):
        """Test token masking."""
        result = self.service.mask({"token": "secret_123"})
        assert result["token"] == "***REDACTED***"

    def test_mask_password(self):
        """Test password masking."""
        result = self.service.mask({"password": "my_password"})
        assert result["password"] == "***REDACTED***"

    def test_mask_api_key(self):
        """Test API key masking."""
        result = self.service.mask({"api_key": "sk-123456"})
        assert result["api_key"] == "***REDACTED***"

    def test_mask_email(self):
        """Test email masking."""
        result = self.service.mask({"email": "test@example.com"})
        assert "@" in result["email"]
        assert "*" in result["email"]
        assert "example.com" in result["email"]

    def test_mask_phone(self):
        """Test phone masking."""
        result = self.service.mask({"phone": "+79991234567"})
        assert "****" in result["phone"]

    def test_mask_credit_card(self):
        """Test credit card masking."""
        result = self.service.mask({"credit_card": "4111111111111111"})
        assert "****" in result["credit_card"]
        assert result["credit_card"].endswith("1111")

    def test_non_sensitive_unchanged(self):
        """Test non-sensitive data unchanged."""
        result = self.service.mask({"user_id": 123, "action": "login"})
        assert result["user_id"] == 123
        assert result["action"] == "login"

    def test_mask_nested_dict(self):
        """Test nested dictionary masking."""
        data = {
            "user": {
                "email": "test@example.com",
                "password": "secret",
            },
            "meta": {
                "token": "api_token",
            },
        }

        masked = self.service.mask(data)

        assert masked["user"]["password"] == "***REDACTED***"
        assert masked["meta"]["token"] == "***REDACTED***"

    def test_mask_list(self):
        """Test list masking."""
        data = {
            "items": [
                {"email": "a@example.com", "token": "tok1"},
                {"email": "b@example.com", "token": "tok2"},
            ]
        }

        masked = self.service.mask(data)

        assert masked["items"][0]["token"] == "***REDACTED***"
        assert masked["items"][1]["token"] == "***REDACTED***"

    def test_empty_dict(self):
        """Test empty dictionary."""
        result = self.service.mask({})
        assert result == {}

    def test_mask_string_in_value(self):
        """Test masking email/phone in string value."""
        result = self.service.mask(
            {"description": "User email: test@example.com called from +79991234567"}
        )

        assert "test@example.com" not in result["description"]
        assert "+79991234567" not in result["description"]
        assert "@" in result["description"]  # Domain preserved
        assert "****" in result["description"]  # Phone masked
