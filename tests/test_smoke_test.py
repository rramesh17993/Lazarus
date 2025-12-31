"""Tests for smoke test framework."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from lazarus_operator.smoke_test import (
    CheckStatus,
    DatabaseHealthCheck,
    HTTPHealthCheck,
    SmokeTestRunner,
)


class TestDatabaseHealthCheck:
    """Test cases for database health checks."""

    @pytest.mark.asyncio
    async def test_postgres_check_success(self):
        """Test successful PostgreSQL health check."""
        config = {
            "type": "postgres",
            "namespace": "default",
            "connectionString": {"value": "postgresql://localhost/testdb"},
            "queries": [
                {
                    "name": "count-check",
                    "sql": "SELECT COUNT(*) FROM users",
                    "expectedRange": {"min": 100, "max": 1000},
                }
            ],
            "timeout": 30,
            "retries": 1,
        }

        check = DatabaseHealthCheck(name="db-check", config=config)

        with patch(
            "lazarus_operator.smoke_test.asyncpg.connect"
        ) as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchval = AsyncMock(return_value=500)
            mock_connect.return_value = mock_conn

            result = await check.execute()

            assert result.status == CheckStatus.PASSED
            assert "500" in result.message

    @pytest.mark.asyncio
    async def test_postgres_check_out_of_range(self):
        """Test PostgreSQL check with out-of-range result."""
        config = {
            "type": "postgres",
            "namespace": "default",
            "connectionString": {"value": "postgresql://localhost/testdb"},
            "queries": [
                {
                    "name": "count-check",
                    "sql": "SELECT COUNT(*) FROM users",
                    "expectedRange": {"min": 100, "max": 1000},
                }
            ],
            "timeout": 30,
            "retries": 1,
        }

        check = DatabaseHealthCheck(name="db-check", config=config)

        with patch(
            "lazarus_operator.smoke_test.asyncpg.connect"
        ) as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchval = AsyncMock(return_value=50)  # Below min
            mock_connect.return_value = mock_conn

            result = await check.execute()

            assert result.status == CheckStatus.FAILED
            assert "not in range" in result.message


class TestHTTPHealthCheck:
    """Test cases for HTTP health checks."""

    @pytest.mark.asyncio
    async def test_http_check_success(self):
        """Test successful HTTP health check."""
        config = {
            "endpoints": [
                {
                    "name": "api-health",
                    "url": "http://api:8080/health",
                    "expectedStatus": 200,
                }
            ],
            "timeout": 30,
            "retries": 1,
        }

        check = HTTPHealthCheck(name="http-check", config=config)

        with patch("lazarus_operator.smoke_test.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "OK"
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await check.execute()

            assert result.status == CheckStatus.PASSED
            assert "api-health" in result.message

    @pytest.mark.asyncio
    async def test_http_check_wrong_status(self):
        """Test HTTP check with wrong status code."""
        config = {
            "endpoints": [
                {
                    "name": "api-health",
                    "url": "http://api:8080/health",
                    "expectedStatus": 200,
                }
            ],
            "timeout": 30,
            "retries": 1,
        }

        check = HTTPHealthCheck(name="http-check", config=config)

        with patch("lazarus_operator.smoke_test.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await check.execute()

            assert result.status == CheckStatus.FAILED
            assert "500" in result.message


class TestSmokeTestRunner:
    """Test cases for smoke test runner."""

    @pytest.mark.asyncio
    async def test_run_all_checks_success(self):
        """Test running all checks successfully."""
        config = {
            "http": {
                "enabled": True,
                "endpoints": [
                    {
                        "name": "test-endpoint",
                        "url": "http://test:8080/health",
                        "expectedStatus": 200,
                    }
                ],
            }
        }

        runner = SmokeTestRunner(config)

        with patch("lazarus_operator.smoke_test.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "OK"
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            results = await runner.run_all_checks()

            assert results.overall_success is True
            assert results.passed_count == 1
            assert results.failed_count == 0

    @pytest.mark.asyncio
    async def test_run_all_checks_with_failure(self):
        """Test running checks with one failure."""
        config = {
            "http": {
                "enabled": True,
                "endpoints": [
                    {
                        "name": "test-endpoint",
                        "url": "http://test:8080/health",
                        "expectedStatus": 200,
                    }
                ],
            }
        }

        runner = SmokeTestRunner(config)

        with patch("lazarus_operator.smoke_test.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            results = await runner.run_all_checks()

            assert results.overall_success is False
            assert results.failed_count == 1
