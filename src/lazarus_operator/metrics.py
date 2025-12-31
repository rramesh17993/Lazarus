"""Prometheus metrics for Lazarus operator."""

from prometheus_client import Counter, Gauge, Histogram, Info, start_http_server

from .config import config
from .logger import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """Centralized metrics collection for the operator."""

    def __init__(self) -> None:
        """Initialize metrics collectors."""
        # Info metric
        self.operator_info = Info(
            "lazarus_operator",
            "Information about the Lazarus operator",
        )
        self.operator_info.info(
            {
                "version": "0.1.0",
                "namespace": config.namespace,
            }
        )

        # Test execution metrics
        self.tests_total = Counter(
            "lazarus_restore_tests_total",
            "Total number of restore tests executed",
            ["backup_name", "result"],
        )

        self.test_duration = Histogram(
            "lazarus_restore_test_duration_seconds",
            "Duration of restore tests in seconds",
            ["backup_name", "phase"],
            buckets=[10, 30, 60, 120, 300, 600, 900, 1800, 3600],
        )

        # Restore metrics
        self.restore_duration = Histogram(
            "lazarus_velero_restore_duration_seconds",
            "Duration of Velero restore operation in seconds",
            ["backup_name"],
            buckets=[10, 30, 60, 120, 300, 600, 900, 1800],
        )

        self.resources_restored = Gauge(
            "lazarus_resources_restored_total",
            "Number of resources restored from backup",
            ["backup_name"],
        )

        self.restore_errors = Counter(
            "lazarus_restore_errors_total",
            "Total number of restore errors",
            ["backup_name", "error_type"],
        )

        # Health check metrics
        self.health_checks_total = Counter(
            "lazarus_health_checks_total",
            "Total number of health checks executed",
            ["check_type", "check_name", "result"],
        )

        self.health_check_duration = Histogram(
            "lazarus_health_check_duration_seconds",
            "Duration of health checks in seconds",
            ["check_type", "check_name"],
            buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
        )

        # RTO/RPO metrics
        self.rto_seconds = Histogram(
            "lazarus_recovery_time_objective_seconds",
            "Measured Recovery Time Objective in seconds",
            ["backup_name"],
            buckets=[60, 300, 600, 1800, 3600, 7200],
        )

        self.rpo_seconds = Gauge(
            "lazarus_recovery_point_objective_seconds",
            "Measured Recovery Point Objective in seconds",
            ["backup_name"],
        )

        # Active tests gauge
        self.active_tests = Gauge(
            "lazarus_active_tests",
            "Number of currently running restore tests",
        )

        # Cleanup metrics
        self.cleanup_total = Counter(
            "lazarus_cleanup_operations_total",
            "Total number of cleanup operations",
            ["result"],
        )

        logger.info("Metrics collector initialized")

    def record_test_start(self, backup_name: str) -> None:
        """Record test start."""
        self.active_tests.inc()
        logger.debug("Test started", backup_name=backup_name)

    def record_test_complete(
        self, backup_name: str, success: bool, duration: float, rto: float, rpo: float
    ) -> None:
        """Record test completion."""
        result = "success" if success else "failure"
        self.tests_total.labels(backup_name=backup_name, result=result).inc()
        self.test_duration.labels(backup_name=backup_name, phase="total").observe(duration)
        self.rto_seconds.labels(backup_name=backup_name).observe(rto)
        self.rpo_seconds.labels(backup_name=backup_name).set(rpo)
        self.active_tests.dec()
        logger.info(
            "Test completed",
            backup_name=backup_name,
            success=success,
            duration=duration,
            rto=rto,
            rpo=rpo,
        )

    def record_restore_duration(self, backup_name: str, duration: float) -> None:
        """Record Velero restore duration."""
        self.restore_duration.labels(backup_name=backup_name).observe(duration)

    def record_resources_restored(self, backup_name: str, count: int) -> None:
        """Record number of resources restored."""
        self.resources_restored.labels(backup_name=backup_name).set(count)

    def record_restore_error(self, backup_name: str, error_type: str) -> None:
        """Record restore error."""
        self.restore_errors.labels(backup_name=backup_name, error_type=error_type).inc()

    def record_health_check(
        self, check_type: str, check_name: str, success: bool, duration: float
    ) -> None:
        """Record health check result."""
        result = "pass" if success else "fail"
        self.health_checks_total.labels(
            check_type=check_type, check_name=check_name, result=result
        ).inc()
        self.health_check_duration.labels(check_type=check_type, check_name=check_name).observe(
            duration
        )

    def record_cleanup(self, success: bool) -> None:
        """Record cleanup operation."""
        result = "success" if success else "failure"
        self.cleanup_total.labels(result=result).inc()


# Global metrics instance
metrics = MetricsCollector()


def start_metrics_server() -> None:
    """Start Prometheus metrics HTTP server."""
    if config.enable_metrics:
        start_http_server(config.metrics_port)
        logger.info("Metrics server started", port=config.metrics_port)
