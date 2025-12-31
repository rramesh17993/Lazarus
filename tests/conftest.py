"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import MagicMock

# Configure asyncio for pytest
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def mock_kubernetes_client():
    """Mock Kubernetes client."""
    return MagicMock()


@pytest.fixture
def sample_backup():
    """Sample Velero backup resource."""
    return {
        "apiVersion": "velero.io/v1",
        "kind": "Backup",
        "metadata": {
            "name": "test-backup",
            "namespace": "velero",
        },
        "spec": {
            "includedNamespaces": ["default"],
            "storageLocation": "default",
        },
        "status": {
            "phase": "Completed",
            "expiration": "2026-01-31T00:00:00Z",
        },
    }


@pytest.fixture
def sample_restore():
    """Sample Velero restore resource."""
    return {
        "apiVersion": "velero.io/v1",
        "kind": "Restore",
        "metadata": {
            "name": "test-restore",
            "namespace": "velero",
        },
        "spec": {
            "backupName": "test-backup",
            "includedNamespaces": ["*"],
        },
        "status": {
            "phase": "Completed",
            "progress": {
                "totalItems": 10,
                "itemsRestored": 10,
            },
        },
    }


@pytest.fixture
def sample_lazarus_restore_test():
    """Sample LaziusRestoreTest resource."""
    return {
        "apiVersion": "lazarus.io/v1alpha1",
        "kind": "LaziusRestoreTest",
        "metadata": {
            "name": "test-restore-test",
            "namespace": "lazarus-system",
        },
        "spec": {
            "backupName": "test-backup",
            "backupNamespace": "velero",
            "restoreNamespace": "lazarus-test-123",
            "ttl": "24h",
            "cleanup": {
                "enabled": True,
                "deleteNamespace": True,
            },
            "healthChecks": {
                "enabled": True,
                "timeout": 600,
                "http": {
                    "enabled": True,
                    "endpoints": [
                        {
                            "name": "api-health",
                            "url": "http://api:8080/health",
                            "expectedStatus": 200,
                        }
                    ],
                },
            },
        },
        "status": {},
    }
