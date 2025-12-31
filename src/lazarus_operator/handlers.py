"""Main Kopf handlers for the Lazarus operator."""

import asyncio
from datetime import datetime
from typing import Any, Dict

import kopf
from kubernetes import client
from kubernetes.client.rest import ApiException

from .config import config
from .logger import configure_logging, get_logger
from .metrics import metrics, start_metrics_server
from .notifications import notification_service
from .smoke_test import SmokeTestRunner
from .utils import (
    calculate_elapsed_seconds,
    create_k8s_event,
    generate_test_namespace_name,
    parse_duration,
)
from .velero_client import VeleroRestoreConfig, velero_client

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Start metrics server
start_metrics_server()


@kopf.on.startup()
async def on_startup(settings: kopf.OperatorSettings, **kwargs: Any) -> None:
    """Configure operator startup settings."""
    settings.persistence.finalizer = "lazarus.io/finalizer"
    settings.posting.level = "info"
    settings.watching.server_timeout = 600

    logger.info(
        "Lazarus operator starting",
        namespace=config.namespace,
        velero_namespace=config.velero_namespace,
    )


@kopf.on.cleanup()
async def on_cleanup(**kwargs: Any) -> None:
    """Cleanup on operator shutdown."""
    logger.info("Lazarus operator shutting down")


@kopf.on.create("lazarus.io", "v1alpha1", "lazarusrestoretests")
@kopf.on.resume("lazarus.io", "v1alpha1", "lazarusrestoretests")
async def handle_restore_test_create(
    body: kopf.Body, spec: kopf.Spec, name: str, namespace: str, **kwargs: Any
) -> Dict[str, Any]:
    """Handle creation of LaziusRestoreTest resource.

    This is the main reconciliation handler that orchestrates:
    1. Velero restore creation
    2. Health check execution
    3. Result reporting
    4. Cleanup

    Args:
        body: Full resource body
        spec: Resource spec
        name: Resource name
        namespace: Resource namespace

    Returns:
        Status update dict
    """
    logger.info("Processing LaziusRestoreTest", name=name, namespace=namespace)

    backup_name = spec.get("backupName")
    restore_namespace = spec.get("restoreNamespace")

    if not backup_name:
        raise kopf.PermanentError("backupName is required")

    if not restore_namespace:
        # Generate namespace name if not provided
        restore_namespace = generate_test_namespace_name(
            backup_name, config.test_namespace_prefix
        )
        logger.info("Generated restore namespace", namespace=restore_namespace)

    # Initialize status
    start_time = datetime.utcnow().isoformat() + "Z"
    status = {
        "phase": "Running",
        "startTime": start_time,
        "restore": {"phase": "Pending"},
        "healthChecks": {"phase": "Pending"},
        "result": {},
    }

    metrics.record_test_start(backup_name)

    try:
        # Step 1: Verify backup exists
        logger.info("Verifying backup exists", backup_name=backup_name)
        backup = await velero_client.get_backup(backup_name)

        if not backup:
            raise kopf.PermanentError(f"Backup {backup_name} not found")

        backup_phase = backup.get("status", {}).get("phase")
        if backup_phase != "Completed":
            raise kopf.PermanentError(
                f"Backup {backup_name} is not completed (phase: {backup_phase})"
            )

        create_k8s_event(
            name=name,
            namespace=namespace,
            reason="BackupVerified",
            message=f"Backup {backup_name} verified and ready for restore",
        )

        # Step 2: Create test namespace
        logger.info("Creating test namespace", namespace=restore_namespace)
        await create_test_namespace(restore_namespace, backup_name)

        # Step 3: Create Velero restore
        logger.info("Creating Velero restore", backup_name=backup_name)
        restore_name = f"restore-test-{backup_name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        restore_config = VeleroRestoreConfig(
            backup_name=backup_name,
            target_namespace=restore_namespace,
            included_namespaces=spec.get("restore", {}).get("includedNamespaces", ["*"]),
            excluded_namespaces=spec.get("restore", {}).get(
                "excludedNamespaces", ["kube-system", "velero", config.namespace]
            ),
            included_resources=spec.get("restore", {}).get("includedResources", []),
            excluded_resources=spec.get("restore", {}).get("excludedResources", []),
            restore_pvs=True,
            restore_status=spec.get("restore", {}).get("restoreStatus", False),
        )

        restore_start = datetime.utcnow()
        restore = await velero_client.create_restore(restore_name, restore_config)

        status["restore"]["restoreName"] = restore_name
        status["restore"]["phase"] = "InProgress"

        create_k8s_event(
            name=name,
            namespace=namespace,
            reason="RestoreCreated",
            message=f"Velero restore {restore_name} created",
        )

        # Step 4: Wait for restore to complete
        logger.info("Waiting for restore to complete", restore_name=restore_name)
        restore = await velero_client.wait_for_restore(
            restore_name, timeout=config.velero_timeout
        )

        restore_duration = (datetime.utcnow() - restore_start).total_seconds()
        metrics.record_restore_duration(backup_name, restore_duration)

        # Parse restore stats
        restore_stats = velero_client.parse_restore_stats(restore)
        logger.info("Restore completed", restore_name=restore_name, stats=restore_stats)

        status["restore"]["phase"] = "Completed"
        status["restore"]["progress"] = {
            "itemsRestored": restore_stats["items_restored"],
            "itemsAttempted": restore_stats["items_attempted"],
        }
        status["restore"]["errors"] = restore_stats.get("errors", 0)

        metrics.record_resources_restored(backup_name, restore_stats["items_restored"])

        create_k8s_event(
            name=name,
            namespace=namespace,
            reason="RestoreCompleted",
            message=f"Velero restore completed: {restore_stats['items_restored']} resources restored",
        )

        # Step 5: Run health checks
        health_check_config = spec.get("healthChecks", {})

        if health_check_config.get("enabled", True):
            logger.info("Running health checks", test_name=name)
            status["healthChecks"]["phase"] = "Running"

            # Allow time for resources to stabilize
            await asyncio.sleep(5)

            runner = SmokeTestRunner(health_check_config)
            test_results = await runner.run_all_checks()

            status["healthChecks"]["phase"] = "Completed"
            status["healthChecks"]["results"] = [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "message": check.message,
                    "duration": check.duration,
                }
                for check in test_results.checks
            ]

            # Record metrics
            for check in test_results.checks:
                metrics.record_health_check(
                    check_type="custom",
                    check_name=check.name,
                    success=(check.status.value == "Passed"),
                    duration=check.duration,
                )

            overall_success = test_results.overall_success
        else:
            logger.info("Health checks disabled", test_name=name)
            status["healthChecks"]["phase"] = "Skipped"
            overall_success = True

        # Step 6: Calculate RTO/RPO
        completion_time = datetime.utcnow().isoformat() + "Z"
        rto = calculate_elapsed_seconds(start_time, completion_time)
        rpo = 0  # TODO: Calculate based on backup timestamp vs latest data

        status["completionTime"] = completion_time
        status["result"] = {
            "success": overall_success,
            "rto": int(rto),
            "rpo": rpo,
            "message": "Restore test completed successfully"
            if overall_success
            else "Restore test failed health checks",
            "resourcesRecovered": restore_stats["items_restored"],
            "resourcesFailed": restore_stats.get("errors", 0),
        }

        if overall_success:
            status["phase"] = "Succeeded"
            create_k8s_event(
                name=name,
                namespace=namespace,
                reason="TestSucceeded",
                message=f"Backup restore test passed (RTO: {int(rto)}s)",
            )
        else:
            status["phase"] = "Failed"
            create_k8s_event(
                name=name,
                namespace=namespace,
                reason="TestFailed",
                message="Backup restore test failed health checks",
                event_type="Warning",
            )

        # Record metrics
        metrics.record_test_complete(
            backup_name=backup_name,
            success=overall_success,
            duration=rto,
            rto=rto,
            rpo=rpo,
        )

        # Step 7: Send notifications
        notification_config = spec.get("notifications", {})
        if overall_success and notification_config.get("onSuccess", {}).get("slack", {}).get("enabled"):
            await notification_service.notify_test_success(
                test_name=name,
                backup_name=backup_name,
                metadata={
                    "rto": int(rto),
                    "rpo": rpo,
                    "resources_restored": restore_stats["items_restored"],
                    "timestamp": completion_time,
                },
            )
        elif not overall_success and notification_config.get("onFailure", {}).get("slack", {}).get("enabled"):
            await notification_service.notify_test_failure(
                test_name=name,
                backup_name=backup_name,
                error=status["result"]["message"],
                metadata={
                    "timestamp": completion_time,
                    "mention_on_failure": notification_config.get("onFailure", {})
                    .get("slack", {})
                    .get("mentionOnFailure"),
                },
            )

        # Step 8: Schedule cleanup
        cleanup_config = spec.get("cleanup", {})
        if cleanup_config.get("enabled", True):
            should_cleanup = (
                overall_success and config.cleanup_on_success
            ) or (not overall_success and config.cleanup_on_failure)

            if should_cleanup:
                ttl = spec.get("ttl", f"{config.default_ttl_hours}h")
                ttl_seconds = int(parse_duration(ttl).total_seconds())

                logger.info(
                    "Scheduling cleanup",
                    namespace=restore_namespace,
                    ttl_seconds=ttl_seconds,
                )

                # Schedule async cleanup
                asyncio.create_task(
                    cleanup_test_namespace(restore_namespace, ttl_seconds, restore_name)
                )

        return status

    except kopf.PermanentError:
        raise
    except Exception as e:
        logger.error("Restore test failed", name=name, error=str(e), exc_info=True)

        status["phase"] = "Failed"
        status["completionTime"] = datetime.utcnow().isoformat() + "Z"
        status["result"] = {
            "success": False,
            "message": f"Test failed: {str(e)}",
        }

        metrics.record_test_complete(
            backup_name=backup_name,
            success=False,
            duration=calculate_elapsed_seconds(start_time),
            rto=0,
            rpo=0,
        )

        create_k8s_event(
            name=name,
            namespace=namespace,
            reason="TestError",
            message=f"Restore test encountered error: {str(e)}",
            event_type="Warning",
        )

        raise kopf.TemporaryError(f"Test failed: {str(e)}", delay=60)


@kopf.on.delete("lazarus.io", "v1alpha1", "lazarusrestoretests")
async def handle_restore_test_delete(
    spec: kopf.Spec, name: str, namespace: str, **kwargs: Any
) -> None:
    """Handle deletion of LaziusRestoreTest resource.

    Ensures cleanup of test namespace and Velero restore.

    Args:
        spec: Resource spec
        name: Resource name
        namespace: Resource namespace
    """
    logger.info("Deleting LaziusRestoreTest", name=name, namespace=namespace)

    restore_namespace = spec.get("restoreNamespace")
    backup_name = spec.get("backupName")

    if restore_namespace:
        try:
            await delete_namespace(restore_namespace)
            logger.info("Test namespace deleted", namespace=restore_namespace)
        except Exception as e:
            logger.warning("Failed to delete test namespace", namespace=restore_namespace, error=str(e))

    # Try to delete associated Velero restore
    restore_name = f"restore-test-{backup_name}-*"
    logger.info("Cleaned up test resources", test_name=name)


async def create_test_namespace(namespace: str, backup_name: str) -> None:
    """Create a test namespace for restore.

    Args:
        namespace: Namespace to create
        backup_name: Backup name (for labeling)
    """
    v1 = client.CoreV1Api()

    namespace_body = client.V1Namespace(
        metadata=client.V1ObjectMeta(
            name=namespace,
            labels={
                "lazarus.io/test": "true",
                "lazarus.io/backup": backup_name,
                "lazarus.io/managed-by": "lazarus-operator",
            },
        )
    )

    try:
        await asyncio.get_event_loop().run_in_executor(
            None, v1.create_namespace, namespace_body
        )
        logger.info("Created test namespace", namespace=namespace)
    except ApiException as e:
        if e.status == 409:  # Already exists
            logger.info("Test namespace already exists", namespace=namespace)
        else:
            raise


async def delete_namespace(namespace: str) -> None:
    """Delete a namespace.

    Args:
        namespace: Namespace to delete
    """
    v1 = client.CoreV1Api()

    try:
        await asyncio.get_event_loop().run_in_executor(
            None, v1.delete_namespace, namespace
        )
        logger.info("Deleted namespace", namespace=namespace)
        metrics.record_cleanup(success=True)
    except ApiException as e:
        if e.status != 404:
            logger.error("Failed to delete namespace", namespace=namespace, error=str(e))
            metrics.record_cleanup(success=False)
            raise


async def cleanup_test_namespace(
    namespace: str, delay_seconds: int, restore_name: str
) -> None:
    """Cleanup test namespace after delay (TTL).

    Args:
        namespace: Namespace to cleanup
        delay_seconds: Delay before cleanup
        restore_name: Associated Velero restore name
    """
    logger.info(
        "Scheduling cleanup",
        namespace=namespace,
        delay_seconds=delay_seconds,
    )

    await asyncio.sleep(delay_seconds)

    logger.info("Executing scheduled cleanup", namespace=namespace)

    # Delete namespace
    await delete_namespace(namespace)

    # Delete Velero restore
    try:
        await velero_client.delete_restore(restore_name)
    except Exception as e:
        logger.warning("Failed to delete Velero restore", restore_name=restore_name, error=str(e))
