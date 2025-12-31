"""Utility functions for the Lazarus operator."""

import hashlib
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from kubernetes import client


def generate_test_namespace_name(backup_name: str, prefix: str = "lazarus-test") -> str:
    """Generate a unique namespace name for testing.

    Args:
        backup_name: Name of the backup being tested
        prefix: Prefix for the namespace

    Returns:
        Valid Kubernetes namespace name
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    # Sanitize backup name to be DNS-compatible
    safe_backup_name = re.sub(r"[^a-z0-9-]", "-", backup_name.lower())
    safe_backup_name = safe_backup_name[:30]  # Limit length

    namespace = f"{prefix}-{safe_backup_name}-{timestamp}"
    # Ensure it's within Kubernetes limits (63 chars)
    if len(namespace) > 63:
        # Use hash to shorten
        hash_suffix = hashlib.md5(backup_name.encode()).hexdigest()[:8]
        namespace = f"{prefix}-{hash_suffix}-{timestamp}"

    return namespace


def parse_duration(duration_str: str) -> timedelta:
    """Parse duration string to timedelta.

    Supports formats like: 1h, 30m, 1d, 24h, etc.

    Args:
        duration_str: Duration string

    Returns:
        timedelta object
    """
    pattern = r"(\d+)([dhms])"
    match = re.match(pattern, duration_str.lower())

    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}")

    value, unit = match.groups()
    value = int(value)

    units = {
        "d": timedelta(days=value),
        "h": timedelta(hours=value),
        "m": timedelta(minutes=value),
        "s": timedelta(seconds=value),
    }

    return units[unit]


def get_resource_from_secret(
    secret_name: str, secret_key: str, namespace: str
) -> Optional[str]:
    """Retrieve a value from a Kubernetes secret.

    Args:
        secret_name: Name of the secret
        secret_key: Key within the secret
        namespace: Namespace of the secret

    Returns:
        Decoded secret value or None if not found
    """
    try:
        v1 = client.CoreV1Api()
        secret = v1.read_namespaced_secret(name=secret_name, namespace=namespace)
        if secret.data and secret_key in secret.data:
            import base64

            return base64.b64decode(secret.data[secret_key]).decode("utf-8")
    except client.exceptions.ApiException:
        pass
    return None


def create_k8s_event(
    name: str,
    namespace: str,
    reason: str,
    message: str,
    event_type: str = "Normal",
    involved_object: Optional[Dict[str, Any]] = None,
) -> None:
    """Create a Kubernetes event.

    Args:
        name: Event name
        namespace: Event namespace
        reason: Event reason
        message: Event message
        event_type: Type of event (Normal, Warning)
        involved_object: Object the event relates to
    """
    try:
        v1 = client.CoreV1Api()
        timestamp = datetime.utcnow().isoformat() + "Z"

        event = client.V1Event(
            metadata=client.V1ObjectMeta(
                name=f"{name}.{datetime.utcnow().strftime('%s')}",
                namespace=namespace,
            ),
            type=event_type,
            reason=reason,
            message=message,
            first_timestamp=timestamp,
            last_timestamp=timestamp,
            count=1,
            source=client.V1EventSource(component="lazarus-operator"),
            involved_object=involved_object
            or client.V1ObjectReference(
                kind="LaziusRestoreTest",
                namespace=namespace,
                name=name,
            ),
        )

        v1.create_namespaced_event(namespace=namespace, body=event)
    except Exception:
        # Don't fail if event creation fails
        pass


def sanitize_resource_name(name: str, max_length: int = 63) -> str:
    """Sanitize a string to be a valid Kubernetes resource name.

    Args:
        name: Input name
        max_length: Maximum allowed length

    Returns:
        Sanitized name
    """
    # Convert to lowercase and replace invalid chars
    sanitized = re.sub(r"[^a-z0-9-]", "-", name.lower())
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip("-")
    # Ensure within length limit
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip("-")
    return sanitized


def calculate_elapsed_seconds(start_time: str, end_time: Optional[str] = None) -> float:
    """Calculate elapsed time in seconds between two ISO timestamps.

    Args:
        start_time: ISO format start timestamp
        end_time: ISO format end timestamp (defaults to now)

    Returns:
        Elapsed seconds
    """
    start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    if end_time:
        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    else:
        end = datetime.utcnow()

    return (end - start).total_seconds()
