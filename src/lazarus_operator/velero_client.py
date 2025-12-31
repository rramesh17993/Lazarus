"""Velero client for interacting with Velero backups and restores."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from kubernetes import client
from kubernetes.client.rest import ApiException

from .config import config
from .logger import get_logger

logger = get_logger(__name__)


class VeleroRestoreConfig:
    """Configuration for a Velero restore operation."""

    def __init__(
        self,
        backup_name: str,
        target_namespace: str,
        included_namespaces: Optional[List[str]] = None,
        excluded_namespaces: Optional[List[str]] = None,
        included_resources: Optional[List[str]] = None,
        excluded_resources: Optional[List[str]] = None,
        restore_pvs: bool = True,
        restore_status: bool = False,
    ):
        """Initialize restore configuration."""
        self.backup_name = backup_name
        self.target_namespace = target_namespace
        self.included_namespaces = included_namespaces or ["*"]
        self.excluded_namespaces = excluded_namespaces or []
        self.included_resources = included_resources or []
        self.excluded_resources = excluded_resources or []
        self.restore_pvs = restore_pvs
        self.restore_status = restore_status


class VeleroClient:
    """Client for interacting with Velero resources."""

    def __init__(self, namespace: str = "velero"):
        """Initialize Velero client.

        Args:
            namespace: Namespace where Velero is installed
        """
        self.namespace = namespace
        self.custom_api = client.CustomObjectsApi()
        self.group = "velero.io"
        self.version = "v1"

    async def get_backup(self, backup_name: str) -> Optional[Dict[str, Any]]:
        """Get a Velero backup by name.

        Args:
            backup_name: Name of the backup

        Returns:
            Backup resource dict or None if not found
        """
        try:
            backup = await asyncio.get_event_loop().run_in_executor(
                None,
                self.custom_api.get_namespaced_custom_object,
                self.group,
                self.version,
                self.namespace,
                "backups",
                backup_name,
            )
            logger.info("Retrieved backup", backup_name=backup_name)
            return backup
        except ApiException as e:
            if e.status == 404:
                logger.warning("Backup not found", backup_name=backup_name)
                return None
            logger.error("Error retrieving backup", backup_name=backup_name, error=str(e))
            raise

    async def create_restore(
        self, restore_name: str, restore_config: VeleroRestoreConfig
    ) -> Dict[str, Any]:
        """Create a Velero restore from a backup.

        Args:
            restore_name: Name for the restore
            restore_config: Restore configuration

        Returns:
            Created restore resource
        """
        restore_spec = {
            "backupName": restore_config.backup_name,
            "includedNamespaces": restore_config.included_namespaces,
            "excludedNamespaces": restore_config.excluded_namespaces,
            "restorePVs": restore_config.restore_pvs,
            "includeClusterResources": False,
        }

        # Add optional filters
        if restore_config.included_resources:
            restore_spec["includedResources"] = restore_config.included_resources
        if restore_config.excluded_resources:
            restore_spec["excludedResources"] = restore_config.excluded_resources

        # Add namespace mapping to restore into test namespace
        restore_spec["namespaceMapping"] = {
            ns: restore_config.target_namespace
            for ns in restore_config.included_namespaces
            if ns != "*"
        }

        restore_body = {
            "apiVersion": f"{self.group}/{self.version}",
            "kind": "Restore",
            "metadata": {
                "name": restore_name,
                "namespace": self.namespace,
                "labels": {
                    "lazarus.io/test": "true",
                    "lazarus.io/backup": restore_config.backup_name,
                },
            },
            "spec": restore_spec,
        }

        try:
            restore = await asyncio.get_event_loop().run_in_executor(
                None,
                self.custom_api.create_namespaced_custom_object,
                self.group,
                self.version,
                self.namespace,
                "restores",
                restore_body,
            )
            logger.info(
                "Created Velero restore",
                restore_name=restore_name,
                backup_name=restore_config.backup_name,
            )
            return restore
        except ApiException as e:
            logger.error("Failed to create restore", restore_name=restore_name, error=str(e))
            raise

    async def get_restore(self, restore_name: str) -> Optional[Dict[str, Any]]:
        """Get a Velero restore by name.

        Args:
            restore_name: Name of the restore

        Returns:
            Restore resource dict or None if not found
        """
        try:
            restore = await asyncio.get_event_loop().run_in_executor(
                None,
                self.custom_api.get_namespaced_custom_object,
                self.group,
                self.version,
                self.namespace,
                "restores",
                restore_name,
            )
            return restore
        except ApiException as e:
            if e.status == 404:
                return None
            raise

    async def wait_for_restore(
        self, restore_name: str, timeout: int = 600, poll_interval: int = 5
    ) -> Dict[str, Any]:
        """Wait for a Velero restore to complete.

        Args:
            restore_name: Name of the restore
            timeout: Maximum time to wait in seconds
            poll_interval: Polling interval in seconds

        Returns:
            Final restore resource

        Raises:
            TimeoutError: If restore doesn't complete within timeout
            RuntimeError: If restore fails
        """
        start_time = datetime.utcnow()
        elapsed = 0

        logger.info("Waiting for restore to complete", restore_name=restore_name, timeout=timeout)

        while elapsed < timeout:
            restore = await self.get_restore(restore_name)

            if not restore:
                raise RuntimeError(f"Restore {restore_name} not found")

            phase = restore.get("status", {}).get("phase", "New")
            logger.debug("Restore status", restore_name=restore_name, phase=phase)

            if phase == "Completed":
                logger.info("Restore completed successfully", restore_name=restore_name)
                return restore
            elif phase in ["Failed", "PartiallyFailed"]:
                errors = restore.get("status", {}).get("errors", [])
                warnings = restore.get("status", {}).get("warnings", [])
                logger.error(
                    "Restore failed",
                    restore_name=restore_name,
                    phase=phase,
                    errors=errors,
                    warnings=warnings,
                )
                raise RuntimeError(
                    f"Restore {restore_name} {phase.lower()}: "
                    f"errors={len(errors)}, warnings={len(warnings)}"
                )

            await asyncio.sleep(poll_interval)
            elapsed = (datetime.utcnow() - start_time).total_seconds()

        raise TimeoutError(
            f"Restore {restore_name} did not complete within {timeout} seconds"
        )

    async def delete_restore(self, restore_name: str) -> None:
        """Delete a Velero restore.

        Args:
            restore_name: Name of the restore to delete
        """
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.custom_api.delete_namespaced_custom_object,
                self.group,
                self.version,
                self.namespace,
                "restores",
                restore_name,
            )
            logger.info("Deleted restore", restore_name=restore_name)
        except ApiException as e:
            if e.status != 404:
                logger.warning("Failed to delete restore", restore_name=restore_name, error=str(e))

    def parse_restore_stats(self, restore: Dict[str, Any]) -> Dict[str, int]:
        """Parse statistics from a restore resource.

        Args:
            restore: Restore resource dict

        Returns:
            Dict with restored/failed resource counts
        """
        status = restore.get("status", {})
        progress = status.get("progress", {})

        return {
            "items_attempted": progress.get("totalItems", 0),
            "items_restored": progress.get("itemsRestored", 0),
            "errors": len(status.get("errors", [])),
            "warnings": len(status.get("warnings", [])),
        }


# Global Velero client instance
velero_client = VeleroClient(namespace=config.velero_namespace)
