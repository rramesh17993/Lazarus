"""Tests for utility functions."""

import pytest
from datetime import timedelta

from lazarus_operator.utils import (
    generate_test_namespace_name,
    parse_duration,
    sanitize_resource_name,
    calculate_elapsed_seconds,
)


class TestUtils:
    """Test cases for utility functions."""

    def test_generate_test_namespace_name(self):
        """Test namespace name generation."""
        backup_name = "my-backup"
        namespace = generate_test_namespace_name(backup_name)

        assert namespace.startswith("lazarus-test-")
        assert "my-backup" in namespace
        assert len(namespace) <= 63  # Kubernetes limit

    def test_generate_test_namespace_name_long_backup(self):
        """Test namespace name generation with long backup name."""
        backup_name = "a" * 100
        namespace = generate_test_namespace_name(backup_name)

        assert len(namespace) <= 63
        assert namespace.startswith("lazarus-test-")

    def test_parse_duration_hours(self):
        """Test parsing hour duration."""
        duration = parse_duration("24h")
        assert duration == timedelta(hours=24)

    def test_parse_duration_minutes(self):
        """Test parsing minute duration."""
        duration = parse_duration("30m")
        assert duration == timedelta(minutes=30)

    def test_parse_duration_days(self):
        """Test parsing day duration."""
        duration = parse_duration("7d")
        assert duration == timedelta(days=7)

    def test_parse_duration_invalid(self):
        """Test parsing invalid duration."""
        with pytest.raises(ValueError):
            parse_duration("invalid")

    def test_sanitize_resource_name(self):
        """Test resource name sanitization."""
        name = "My_Backup@2024"
        sanitized = sanitize_resource_name(name)

        assert sanitized == "my-backup-2024"
        assert len(sanitized) <= 63

    def test_sanitize_resource_name_long(self):
        """Test sanitizing long resource name."""
        name = "a" * 100
        sanitized = sanitize_resource_name(name, max_length=63)

        assert len(sanitized) == 63
        assert sanitized.endswith("a")  # No trailing hyphen

    def test_calculate_elapsed_seconds(self):
        """Test elapsed time calculation."""
        start = "2025-12-31T00:00:00Z"
        end = "2025-12-31T00:10:00Z"

        elapsed = calculate_elapsed_seconds(start, end)
        assert elapsed == 600  # 10 minutes

    def test_calculate_elapsed_seconds_no_end(self):
        """Test elapsed time with no end time (uses now)."""
        start = "2025-12-31T00:00:00Z"
        elapsed = calculate_elapsed_seconds(start)

        assert elapsed > 0  # Should be positive
