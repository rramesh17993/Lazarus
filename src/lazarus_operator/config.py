"""Configuration management for Lazarus operator."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OperatorConfig(BaseSettings):
    """Operator-level configuration."""

    model_config = SettingsConfigDict(env_prefix="LAZARUS_", env_file=".env", extra="ignore")

    # Operator settings
    log_level: str = Field(default="INFO", description="Logging level")
    namespace: str = Field(default="lazarus-system", description="Operator namespace")
    test_namespace_prefix: str = Field(
        default="lazarus-test", description="Prefix for test namespaces"
    )

    # Velero settings
    velero_namespace: str = Field(default="velero", description="Velero namespace")
    velero_timeout: int = Field(default=600, description="Velero operation timeout in seconds")

    # Default test settings
    default_ttl_hours: int = Field(default=24, description="Default TTL for test namespaces")
    default_health_check_timeout: int = Field(
        default=600, description="Default health check timeout in seconds"
    )
    default_health_check_retries: int = Field(
        default=3, description="Default health check retry count"
    )

    # Metrics settings
    metrics_port: int = Field(default=8080, description="Prometheus metrics port")
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")

    # Notification settings
    slack_webhook_url: Optional[str] = Field(default=None, description="Slack webhook URL")
    slack_channel: str = Field(default="#lazarus-alerts", description="Slack channel")
    enable_slack_notifications: bool = Field(
        default=False, description="Enable Slack notifications"
    )

    # Cleanup settings
    enable_auto_cleanup: bool = Field(default=True, description="Enable automatic cleanup")
    cleanup_on_success: bool = Field(
        default=True, description="Delete test namespace on successful test"
    )
    cleanup_on_failure: bool = Field(
        default=False, description="Delete test namespace on failed test (keep for debugging)"
    )

    # Performance settings
    max_concurrent_tests: int = Field(
        default=5, description="Maximum concurrent restore tests"
    )
    reconcile_interval: int = Field(
        default=60, description="Reconciliation interval in seconds"
    )


# Global config instance
config = OperatorConfig()
