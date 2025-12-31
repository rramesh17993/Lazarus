"""Smoke test framework for validating restored resources."""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from .config import config
from .logger import get_logger
from .utils import get_resource_from_secret

logger = get_logger(__name__)


class CheckStatus(str, Enum):
    """Status of a health check."""

    PASSED = "Passed"
    FAILED = "Failed"
    SKIPPED = "Skipped"
    ERROR = "Error"


@dataclass
class CheckResult:
    """Result of a single health check."""

    name: str
    status: CheckStatus
    message: str
    duration: float
    details: Optional[Dict[str, Any]] = None


@dataclass
class TestResults:
    """Aggregated results from all health checks."""

    checks: List[CheckResult]
    overall_success: bool
    total_duration: float

    @property
    def passed_count(self) -> int:
        """Count of passed checks."""
        return sum(1 for c in self.checks if c.status == CheckStatus.PASSED)

    @property
    def failed_count(self) -> int:
        """Count of failed checks."""
        return sum(1 for c in self.checks if c.status == CheckStatus.FAILED)


class HealthCheck(ABC):
    """Abstract base class for health checks."""

    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize health check.

        Args:
            name: Name of the check
            config: Configuration dict for the check
        """
        self.name = name
        self.config = config
        self.timeout = config.get("timeout", 30)
        self.retries = config.get("retries", 3)

    @abstractmethod
    async def execute(self) -> CheckResult:
        """Execute the health check.

        Returns:
            CheckResult with outcome
        """
        pass

    async def run_with_retry(self) -> CheckResult:
        """Execute check with retry logic."""
        start_time = time.time()
        last_error = None

        for attempt in range(self.retries):
            try:
                logger.debug(
                    "Executing health check", name=self.name, attempt=attempt + 1, max=self.retries
                )
                result = await asyncio.wait_for(self.execute(), timeout=self.timeout)
                duration = time.time() - start_time
                result.duration = duration
                return result
            except asyncio.TimeoutError:
                last_error = f"Check timed out after {self.timeout}s"
                logger.warning("Health check timeout", name=self.name, attempt=attempt + 1)
            except Exception as e:
                last_error = str(e)
                logger.warning("Health check error", name=self.name, attempt=attempt + 1, error=str(e))

            if attempt < self.retries - 1:
                await asyncio.sleep(2**attempt)  # Exponential backoff

        duration = time.time() - start_time
        return CheckResult(
            name=self.name,
            status=CheckStatus.ERROR,
            message=f"Check failed after {self.retries} attempts: {last_error}",
            duration=duration,
        )


class DatabaseHealthCheck(HealthCheck):
    """Health check for database connectivity and queries."""

    async def execute(self) -> CheckResult:
        """Execute database health check."""
        db_type = self.config.get("type", "postgres")
        connection_config = self.config.get("connectionString", {})

        # Get connection string from secret or value
        if "secretRef" in connection_config:
            secret_ref = connection_config["secretRef"]
            connection_string = get_resource_from_secret(
                secret_ref["name"], secret_ref["key"], self.config.get("namespace", "default")
            )
        else:
            connection_string = connection_config.get("value")

        if not connection_string:
            return CheckResult(
                name=self.name,
                status=CheckStatus.ERROR,
                message="No connection string provided",
                duration=0,
            )

        try:
            if db_type == "postgres":
                result = await self._check_postgres(connection_string)
            elif db_type == "mysql":
                result = await self._check_mysql(connection_string)
            elif db_type == "mongodb":
                result = await self._check_mongodb(connection_string)
            else:
                return CheckResult(
                    name=self.name,
                    status=CheckStatus.ERROR,
                    message=f"Unsupported database type: {db_type}",
                    duration=0,
                )

            return result
        except Exception as e:
            logger.error("Database check failed", name=self.name, error=str(e))
            return CheckResult(
                name=self.name,
                status=CheckStatus.FAILED,
                message=f"Database check error: {str(e)}",
                duration=0,
            )

    async def _check_postgres(self, connection_string: str) -> CheckResult:
        """Check PostgreSQL database."""
        import asyncpg

        conn = await asyncpg.connect(connection_string)
        try:
            queries = self.config.get("queries", [])
            results = []

            for query_config in queries:
                query_name = query_config.get("name", "unnamed")
                sql = query_config.get("sql")

                if not sql:
                    continue

                result = await conn.fetchval(sql)
                logger.debug("Query result", query=query_name, result=result)

                # Validate result
                if "expectedRange" in query_config:
                    range_config = query_config["expectedRange"]
                    min_val = range_config.get("min", float("-inf"))
                    max_val = range_config.get("max", float("inf"))

                    if not (min_val <= result <= max_val):
                        return CheckResult(
                            name=self.name,
                            status=CheckStatus.FAILED,
                            message=f"Query {query_name}: value {result} not in range [{min_val}, {max_val}]",
                            duration=0,
                        )

                results.append(f"{query_name}={result}")

            return CheckResult(
                name=self.name,
                status=CheckStatus.PASSED,
                message=f"All {len(queries)} queries passed: {', '.join(results)}",
                duration=0,
            )
        finally:
            await conn.close()

    async def _check_mysql(self, connection_string: str) -> CheckResult:
        """Check MySQL database."""
        import aiomysql

        # Parse connection string
        # Format: mysql://user:password@host:port/database
        import re

        match = re.match(
            r"mysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", connection_string
        )
        if not match:
            raise ValueError("Invalid MySQL connection string format")

        user, password, host, port, database = match.groups()

        conn = await aiomysql.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            db=database,
        )
        try:
            async with conn.cursor() as cursor:
                queries = self.config.get("queries", [])
                results = []

                for query_config in queries:
                    query_name = query_config.get("name", "unnamed")
                    sql = query_config.get("sql")

                    if not sql:
                        continue

                    await cursor.execute(sql)
                    result = await cursor.fetchone()
                    results.append(f"{query_name}={result[0] if result else None}")

                return CheckResult(
                    name=self.name,
                    status=CheckStatus.PASSED,
                    message=f"All {len(queries)} queries passed: {', '.join(results)}",
                    duration=0,
                )
        finally:
            conn.close()

    async def _check_mongodb(self, connection_string: str) -> CheckResult:
        """Check MongoDB database."""
        from motor.motor_asyncio import AsyncIOMotorClient

        client = AsyncIOMotorClient(connection_string)
        try:
            # Simple ping test
            await client.admin.command("ping")

            return CheckResult(
                name=self.name,
                status=CheckStatus.PASSED,
                message="MongoDB connection successful",
                duration=0,
            )
        finally:
            client.close()


class HTTPHealthCheck(HealthCheck):
    """Health check for HTTP endpoints."""

    async def execute(self) -> CheckResult:
        """Execute HTTP health check."""
        endpoints = self.config.get("endpoints", [])
        results = []

        async with httpx.AsyncClient() as client:
            for endpoint_config in endpoints:
                endpoint_name = endpoint_config.get("name", "unnamed")
                url = endpoint_config.get("url")
                expected_status = endpoint_config.get("expectedStatus", 200)
                expected_body = endpoint_config.get("expectedBody", {})

                if not url:
                    continue

                try:
                    response = await client.get(url, timeout=self.timeout)

                    # Check status code
                    if response.status_code != expected_status:
                        return CheckResult(
                            name=self.name,
                            status=CheckStatus.FAILED,
                            message=f"Endpoint {endpoint_name}: expected status {expected_status}, got {response.status_code}",
                            duration=0,
                        )

                    # Check response body if specified
                    if "contains" in expected_body:
                        if expected_body["contains"] not in response.text:
                            return CheckResult(
                                name=self.name,
                                status=CheckStatus.FAILED,
                                message=f"Endpoint {endpoint_name}: response body doesn't contain expected text",
                                duration=0,
                            )

                    results.append(f"{endpoint_name}=OK")
                except httpx.RequestError as e:
                    return CheckResult(
                        name=self.name,
                        status=CheckStatus.FAILED,
                        message=f"Endpoint {endpoint_name}: request failed: {str(e)}",
                        duration=0,
                    )

        return CheckResult(
            name=self.name,
            status=CheckStatus.PASSED,
            message=f"All {len(endpoints)} endpoints passed: {', '.join(results)}",
            duration=0,
        )


class SmokeTestRunner:
    """Orchestrates execution of all health checks."""

    def __init__(self, health_check_config: Dict[str, Any]):
        """Initialize smoke test runner.

        Args:
            health_check_config: Configuration for health checks
        """
        self.config = health_check_config
        self.checks: List[HealthCheck] = []
        self._build_checks()

    def _build_checks(self) -> None:
        """Build health check instances from configuration."""
        # Database checks
        if self.config.get("database", {}).get("enabled"):
            db_config = self.config["database"]
            self.checks.append(
                DatabaseHealthCheck(
                    name="database-health",
                    config=db_config,
                )
            )

        # HTTP checks
        if self.config.get("http", {}).get("enabled"):
            http_config = self.config["http"]
            self.checks.append(
                HTTPHealthCheck(
                    name="http-endpoints",
                    config=http_config,
                )
            )

        logger.info("Built health checks", count=len(self.checks))

    async def run_all_checks(self) -> TestResults:
        """Execute all configured health checks.

        Returns:
            Aggregated test results
        """
        start_time = time.time()
        logger.info("Starting health checks", count=len(self.checks))

        if not self.checks:
            logger.warning("No health checks configured")
            return TestResults(
                checks=[],
                overall_success=True,
                total_duration=0,
            )

        # Run checks concurrently
        results = await asyncio.gather(
            *[check.run_with_retry() for check in self.checks],
            return_exceptions=True,
        )

        check_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                check_results.append(
                    CheckResult(
                        name=self.checks[i].name,
                        status=CheckStatus.ERROR,
                        message=f"Unexpected error: {str(result)}",
                        duration=0,
                    )
                )
            else:
                check_results.append(result)

        total_duration = time.time() - start_time
        overall_success = all(r.status == CheckStatus.PASSED for r in check_results)

        test_results = TestResults(
            checks=check_results,
            overall_success=overall_success,
            total_duration=total_duration,
        )

        logger.info(
            "Health checks completed",
            passed=test_results.passed_count,
            failed=test_results.failed_count,
            duration=total_duration,
        )

        return test_results
