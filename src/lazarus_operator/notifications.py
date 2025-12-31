"""Notification system for test results."""

import asyncio
from typing import Any, Dict, Optional

import httpx
from slack_sdk.webhook.async_client import AsyncWebhookClient

from .config import config
from .logger import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Service for sending notifications about test results."""

    def __init__(self):
        """Initialize notification service."""
        self.slack_webhook_url = config.slack_webhook_url
        self.slack_client: Optional[AsyncWebhookClient] = None

        if self.slack_webhook_url and config.enable_slack_notifications:
            self.slack_client = AsyncWebhookClient(url=self.slack_webhook_url)
            logger.info("Slack notifications enabled")

    async def notify_test_success(
        self, test_name: str, backup_name: str, metadata: Dict[str, Any]
    ) -> None:
        """Send notification for successful test.

        Args:
            test_name: Name of the test
            backup_name: Name of the backup tested
            metadata: Additional metadata (RTO, RPO, etc.)
        """
        logger.info("Test succeeded", test_name=test_name, backup_name=backup_name)

        if not self.slack_client:
            return

        try:
            rto = metadata.get("rto", "N/A")
            rpo = metadata.get("rpo", "N/A")
            resources = metadata.get("resources_restored", 0)

            message = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Backup Restore Test Passed",
                            "emoji": False,
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Backup:*\n{backup_name}"},
                            {"type": "mrkdwn", "text": f"*Test:*\n{test_name}"},
                            {"type": "mrkdwn", "text": f"*RTO:*\n{rto}s"},
                            {"type": "mrkdwn", "text": f"*RPO:*\n{rpo}s"},
                            {
                                "type": "mrkdwn",
                                "text": f"*Resources Restored:*\n{resources}",
                            },
                        ],
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"Backup recovery validated successfully at {metadata.get('timestamp', 'unknown')}",
                            }
                        ],
                    },
                ],
            }

            await self.slack_client.send(
                text=f"Backup restore test passed: {backup_name}",
                blocks=message["blocks"],
            )
            logger.info("Slack notification sent (success)", test_name=test_name)
        except Exception as e:
            logger.error("Failed to send Slack notification", error=str(e))

    async def notify_test_failure(
        self, test_name: str, backup_name: str, error: str, metadata: Dict[str, Any]
    ) -> None:
        """Send notification for failed test.

        Args:
            test_name: Name of the test
            backup_name: Name of the backup tested
            error: Error message
            metadata: Additional metadata
        """
        logger.error("Test failed", test_name=test_name, backup_name=backup_name, error=error)

        if not self.slack_client:
            return

        try:
            message = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Backup Restore Test Failed",
                            "emoji": False,
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Backup:*\n{backup_name}"},
                            {"type": "mrkdwn", "text": f"*Test:*\n{test_name}"},
                        ],
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Error:*\n```{error[:500]}```",
                        },
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"Backup recovery validation failed at {metadata.get('timestamp', 'unknown')}. Investigate immediately!",
                            }
                        ],
                    },
                ],
            }

            # Add mention if configured
            mention = metadata.get("mention_on_failure")
            if mention:
                message["blocks"].insert(
                    1,
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"cc: {mention}"},
                    },
                )

            await self.slack_client.send(
                text=f"Backup restore test failed: {backup_name}",
                blocks=message["blocks"],
            )
            logger.info("Slack notification sent (failure)", test_name=test_name)
        except Exception as e:
            logger.error("Failed to send Slack notification", error=str(e))


# Global notification service instance
notification_service = NotificationService()
