"""
Unit tests for validation utilities.
"""

import pytest

from src.cses_mcp.utils.validation import MCPValidationError, sanitize_input


class TestInputSanitization:
    """Tests for input sanitization."""

    def test_normal_input(self):
        input_text = "Hello, World!"
        assert sanitize_input(input_text) == input_text

    def test_dangerous_characters(self):
        input_text = 'Hello <script>alert("xss")</script> World'
        result = sanitize_input(input_text)
        assert "<script>" not in result
        assert "alert" in result

    def test_length_limit(self):
        long_text = "a" * 2000
        with pytest.raises(MCPValidationError):
            sanitize_input(long_text, max_length=1000)

    def test_none_input(self):
        assert sanitize_input(None) == ""

    def test_non_string_input(self):
        assert sanitize_input(123) == "123"
