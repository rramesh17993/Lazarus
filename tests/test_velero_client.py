"""Tests for the Velero client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from lazarus_operator.velero_client import VeleroClient, VeleroRestoreConfig


@pytest.fixture
def velero_client():
    """Create a Velero client instance for testing."""
    return VeleroClient(namespace="velero")


@pytest.fixture
def restore_config():
    """Create a sample restore configuration."""
    return VeleroRestoreConfig(
        backup_name="test-backup",
        target_namespace="lazarus-test-123",
        included_namespaces=["default"],
        excluded_namespaces=["kube-system"],
    )


class TestVeleroClient:
    """Test cases for VeleroClient."""

    @pytest.mark.asyncio
    async def test_get_backup_success(self, velero_client):
        """Test successful backup retrieval."""
        mock_backup = {
            "metadata": {"name": "test-backup"},
            "status": {"phase": "Completed"},
        }

        with patch.object(
            velero_client.custom_api,
            "get_namespaced_custom_object",
            return_value=mock_backup,
        ):
            backup = await velero_client.get_backup("test-backup")

            assert backup is not None
            assert backup["metadata"]["name"] == "test-backup"
            assert backup["status"]["phase"] == "Completed"

    @pytest.mark.asyncio
    async def test_get_backup_not_found(self, velero_client):
        """Test backup not found."""
        from kubernetes.client.rest import ApiException

        with patch.object(
            velero_client.custom_api,
            "get_namespaced_custom_object",
            side_effect=ApiException(status=404),
        ):
            backup = await velero_client.get_backup("nonexistent-backup")
            assert backup is None

    @pytest.mark.asyncio
    async def test_create_restore(self, velero_client, restore_config):
        """Test creating a Velero restore."""
        mock_restore = {
            "metadata": {"name": "test-restore"},
            "status": {"phase": "New"},
        }

        with patch.object(
            velero_client.custom_api,
            "create_namespaced_custom_object",
            return_value=mock_restore,
        ):
            restore = await velero_client.create_restore("test-restore", restore_config)

            assert restore is not None
            assert restore["metadata"]["name"] == "test-restore"

    @pytest.mark.asyncio
    async def test_wait_for_restore_success(self, velero_client):
        """Test waiting for restore to complete successfully."""
        completed_restore = {
            "metadata": {"name": "test-restore"},
            "status": {
                "phase": "Completed",
                "progress": {"totalItems": 10, "itemsRestored": 10},
            },
        }

        with patch.object(
            velero_client, "get_restore", return_value=completed_restore
        ):
            restore = await velero_client.wait_for_restore(
                "test-restore", timeout=10, poll_interval=1
            )

            assert restore["status"]["phase"] == "Completed"

    @pytest.mark.asyncio
    async def test_wait_for_restore_timeout(self, velero_client):
        """Test restore timeout."""
        in_progress_restore = {
            "metadata": {"name": "test-restore"},
            "status": {"phase": "InProgress"},
        }

        with patch.object(
            velero_client, "get_restore", return_value=in_progress_restore
        ):
            with pytest.raises(TimeoutError):
                await velero_client.wait_for_restore(
                    "test-restore", timeout=2, poll_interval=1
                )

    @pytest.mark.asyncio
    async def test_wait_for_restore_failed(self, velero_client):
        """Test restore failure."""
        failed_restore = {
            "metadata": {"name": "test-restore"},
            "status": {
                "phase": "Failed",
                "errors": ["Error restoring resource"],
            },
        }

        with patch.object(
            velero_client, "get_restore", return_value=failed_restore
        ):
            with pytest.raises(RuntimeError, match="failed"):
                await velero_client.wait_for_restore("test-restore", timeout=10)

    def test_parse_restore_stats(self, velero_client):
        """Test parsing restore statistics."""
        restore = {
            "status": {
                "phase": "Completed",
                "progress": {
                    "totalItems": 15,
                    "itemsRestored": 14,
                },
                "errors": ["Minor error"],
                "warnings": [],
            }
        }

        stats = velero_client.parse_restore_stats(restore)

        assert stats["items_attempted"] == 15
        assert stats["items_restored"] == 14
        assert stats["errors"] == 1
        assert stats["warnings"] == 0
