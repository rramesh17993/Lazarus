# Lazarus: Backup Recovery Validation Operator
## Complete Design & Architecture Document

**Version:** 1.0  
**Date:** December 31, 2025  
**Status:** Ready for Implementation  
**Tech Stack:** Python 3.11 + Kopf + Velero + Kubernetes  

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Solution Overview](#solution-overview)
4. [Architecture](#architecture)
5. [Data Models & CRDs](#data-models--crds)
6. [Core Components](#core-components)
7. [Implementation Details](#implementation-details)
8. [API Reference](#api-reference)
9. [Testing Strategy](#testing-strategy)
10. [Deployment & Operations](#deployment--operations)
11. [Monitoring & Observability](#monitoring--observability)
12. [Security Considerations](#security-considerations)
13. [Project Structure](#project-structure)
14. [Development Roadmap](#development-roadmap)

---

## Executive Summary

**Lazarus** is a Kubernetes operator that autonomously validates backup recovery by:
1. Detecting backup completion events from **Velero**
2. Creating isolated test restores in temporary namespaces
3. Running configurable health checks against restored resources
4. Measuring recovery time and data integrity
5. Reporting results with detailed metrics

**Core Principle:** *Never trust a backup you haven't tested.*

**Business Value:**
- ✅ Discovers backup failures before disasters
- ✅ Automates compliance validation (SOC2, HIPAA, PCI-DSS)
- ✅ Quantifies RTO/RPO with real data
- ✅ Eliminates "hope-based" disaster recovery

**Key Metrics:**
- Detection to Action: < 5 minutes
- Recovery validation time: Configurable (typically 10-30 minutes)
- Success rate tracking: Per-backup, per-resource-type
- Historical audit trail: All tests logged and queryable

---

## Problem Statement

### The Gap
Every organization has backups. Almost nobody tests them automatically.

**Current State:**
```
Monday 3 AM: Velero completes a backup
Monday 3 AM - Forever: NOBODY KNOWS IF IT WORKS
Monday 2 AM (Disaster Day): "Can we restore?"
Monday 2:15 AM: "Restore failed. Data corruption detected."
Monday 2:30 AM: Panic. Escalation. CEO involved.
```

### The Pain Points

| Pain Point | Impact | Current Solution |
|-----------|--------|-----------------|
| Backup corruption undetected | Unrecoverable data loss | Manual quarterly testing (sporadic) |
| No RTO/RPO validation | SLA violations | Guess from documentation |
| Resource drift between envs | Restore fails on prod | Manual environment parity checks |
| Compliance evidence | Audit findings | Manual test reports |
| Data integrity unknown | Silent data loss | Spot checking |

### Why It Happens
1. **No automation:** Testing requires human effort (provisioning, comparing, cleanup)
2. **No visibility:** Backups appear to work because they don't error
3. **No incentives:** Ops team doesn't get credit for "nothing broke"
4. **Distributed responsibility:** Backups are SRE's concern, restore testing is Ops' concern

---

## Solution Overview

### What Lazarus Does

```
Velero Backup Completed
    ↓
Lazarus detects event
    ↓
Creates LaziusRestoreTest CRD
    ↓
Spins up isolated test namespace
    ↓
Restores from Velero backup
    ↓
Runs configurable smoke tests:
  - Database connectivity
  - Record count validation
  - Schema validation
  - Custom health checks
    ↓
Measures:
  - Recovery time (RTO)
  - Data consistency (RPO)
  - Resource count parity
    ↓
Cleanup temporary namespace
    ↓
Report results:
  - Prometheus metrics
  - Kubernetes events
  - Slack notifications (on failure)
```

### Key Differentiators

| Feature | Lazarus | Manual Testing | Other Tools |
|---------|---------|----------------|-----------|
| **Automation** | Fully automated | Manual | Partial (mostly visualization) |
| **Frequency** | Every backup | Quarterly/annually | On-demand |
| **Test Coverage** | Unlimited configs | Limited by time | Limited by tool capability |
| **Cleanup** | Automatic | Manual (forgotten) | Manual |
| **Cost Tracking** | Built-in (temp namespace cost) | Not tracked | Not tracked |
| **Compliance Ready** | ✅ Audit trail | Manual docs | Partial |
| **Open Source** | ✅ Yes | N/A | Some (Velero-dependent) |

---

## Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                      │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
         ┌──────────────────┐  ┌──────────────────┐
         │   Velero         │  │  Lazarus         │
         │   (Backups)      │  │  (Operator)      │
         └────────┬─────────┘  └────────┬─────────┘
                  │                     │
         Watches: BackupRepository  Creates: LaziusRestoreTest
         Emits: BackupCompleted     Watches: LaziusRestoreTest
                                         │
        ┌────────────────────────────────┼───────────────────┐
        ▼                                ▼                   ▼
   ┌─────────────┐          ┌────────────────────┐    ┌─────────────┐
   │ Velero API  │          │  Test Namespace    │    │  Metrics    │
   │  (REST/CLI) │          │  (Ephemeral)       │    │  (Prometheus)
   └─────────────┘          │                    │    └─────────────┘
                            │  - DB Pod          │
                            │  - Test Runner Pod │
                            │  - Restore Tools   │
                            └────────────────────┘
                                     │
                        ┌────────────┴────────────┐
                        ▼                         ▼
                   ┌─────────────┐         ┌────────────┐
                   │ Smoke Tests │         │   Events   │
                   │ - DB Health │         │ & Slack    │
                   │ - Counts    │         │ Alerts     │
                   │ - Schema    │         └────────────┘
                   └─────────────┘
```

### Component Interaction Flow

```
1. Velero Backup Completes
   └─> BackupCompleted event emitted

2. Lazarus Controller Reconciliation
   └─> Watches BackupRepository CRD
   └─> Detects new/modified backup
   └─> Creates LaziusRestoreTest resource

3. Restore Test Handler Triggered
   └─> Waits for test namespace to exist
   └─> Calls Velero API to create restore
   └─> Waits for Velero restore to complete

4. Smoke Test Runner
   └─> Spins up test pod with health checks
   └─> Executes tests against restored resources
   └─> Collects results

5. Result Reporting
   └─> Updates LaziusRestoreTest status
   └─> Emits Prometheus metrics
   └─> Sends Slack alert (on failure)
   └─> Logs audit event

6. Cleanup
   └─> Deletes test namespace
   └─> Removes temporary resources
```

### Deployment Model

```
┌──────────────────────────────────────────────┐
│  lazarus-system Namespace                    │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │ Deployment: lazarus-operator         │   │
│  │ Replicas: 1-2                        │   │
│  │ Image: lazarus:latest                │   │
│  │ Resources:                           │   │
│  │  - CPU: 100m-500m                    │   │
│  │  - Memory: 128Mi-512Mi               │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │ ConfigMap: lazarus-config            │   │
│  │ (Operator settings, test configs)    │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │ ServiceAccount: lazarus              │   │
│  │ ClusterRole: lazarus-controller      │   │
│  │ ClusterRoleBinding                   │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │ ServiceMonitor (Prometheus scraping) │   │
│  └──────────────────────────────────────┘   │
└──────────────────────────────────────────────┘

Ephemeral Test Namespace (Created per test):
┌──────────────────────────────────────────────┐
│  lazarus-test-{backup-name}-{timestamp}      │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │ Pod: restore-validator               │   │
│  │ (Runs smoke tests)                   │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  [Restored Resources from Backup]           │
│  - Database instances                       │
│  - ConfigMaps                               │
│  - Secrets                                  │
│  - Services                                 │
│                                              │
│  [TTL: After tests, auto-deleted]           │
└──────────────────────────────────────────────┘
```

---

## Data Models & CRDs

### Custom Resource Definition: LaziusRestoreTest

```yaml
apiVersion: lazarus.io/v1alpha1
kind: LaziusRestoreTest
metadata:
  name: backup-test-{backup-name}-{timestamp}
  namespace: lazarus-system
  labels:
    backup-name: {backup-name}
    test-type: restore-validation
spec:
  # Backup to restore from
  backupName: my-database-backup-20251231-030000
  backupNamespace: velero
  
  # Target namespace for restore
  restoreNamespace: lazarus-test-{backup-name}-{timestamp}
  
  # Cleanup configuration
  ttl: 24h  # Keep test namespace for debugging (auto-delete after TTL)
  cleanup:
    enabled: true
    deleteNamespace: true
    deleteSecrets: true  # Sanitize test data
  
  # Restore configuration
  restore:
    includedNamespaces:
      - default
      - app-namespace
    excludedNamespaces:
      - kube-system
    includedResources:
      - deployments
      - statefulsets
      - services
      - configmaps
    restoreStatus: false  # Don't restore pod states
  
  # Health check configuration
  healthChecks:
    enabled: true
    timeout: 600  # seconds
    retries: 3
    
    # Database connectivity check
    database:
      enabled: true
      type: postgres  # postgres | mysql | mongodb
      connectionString:  # Can reference secret
        secretRef:
          name: restore-db-creds
          key: connection-string
      queries:
        - name: record-count
          sql: "SELECT COUNT(*) FROM users"
          expectedRange:
            min: 1000
            max: 10000
        
        - name: schema-validation
          sql: "SELECT column_name FROM information_schema.columns WHERE table_name='users'"
          expectedColumns:
            - id
            - email
            - created_at
        
        - name: data-freshness
          sql: "SELECT MAX(updated_at) FROM users"
          expectedRecency: 3600  # seconds (not older than 1 hour)
    
    # HTTP endpoint health checks
    http:
      enabled: true
      endpoints:
        - name: api-health
          url: http://api-service:8080/health
          expectedStatus: 200
          timeout: 30
          retries: 3
        
        - name: api-metrics
          url: http://api-service:8080/metrics
          expectedStatus: 200
          expectedBody:
            contains: "http_requests_total"
    
    # Custom pod-based health checks
    customChecks:
      enabled: true
      pod:
        image: health-check:latest
        command:
          - /bin/bash
          - -c
          - |
            set -e
            echo "Validating restored data..."
            ./validate-schema.sh
            ./validate-records.sh
            ./validate-integrity.sh
            echo "All checks passed"
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        timeout: 300
        retryPolicy: OnFailure

  # Notification configuration
  notifications:
    onSuccess:
      slack:
        enabled: true
        channel: "#data-platform"
        message: "✅ Backup restore test PASSED"
      email:
        enabled: false
    
    onFailure:
      slack:
        enabled: true
        channel: "#data-platform-alerts"
        mentionOnFailure: "@data-platform-oncall"
        message: "❌ Backup restore test FAILED"
      pagerduty:
        enabled: false
  
  # Metrics configuration
  metrics:
    enabled: true
    recordMetrics:
      - restore-duration-seconds
      - health-check-duration-seconds
      - recovered-resources-count
      - failed-checks-count

status:
  # Status phase: Pending | Running | Succeeded | Failed | Unknown
  phase: Running
  
  # Timestamps
  startTime: "2025-12-31T03:30:00Z"
  completionTime: "2025-12-31T03:55:00Z"
  
  # Restore details
  restore:
    restoreName: restore-test-backup-{backup-name}-{timestamp}
    veleroPhase: Completed
    progress:
      itemsRestored: 45
      itemsAttempted: 50
    errors:
      - "ConfigMap app-secrets: size exceeds limit"
  
  # Health check results
  healthChecks:
    phase: Completed
    database:
      status: Passed
      checks:
        - name: record-count
          status: Passed
          result: "Count: 5432 (within range 1000-10000)"
          duration: 2.34
        - name: schema-validation
          status: Passed
          result: "All columns present"
          duration: 1.12
        - name: data-freshness
          status: Passed
          result: "Latest update: 23 minutes ago"
          duration: 0.98
    http:
      status: Passed
      endpoints:
        - name: api-health
          status: Passed
          statusCode: 200
          duration: 0.45
    custom:
      status: Passed
      podPhase: Completed
      logs: "[health-check output]"
  
  # Overall result
  result:
    success: true
    rto: 1234  # Recovery Time Objective (seconds)
    rpo: 0     # Recovery Point Objective (0 = no data loss)
    message: "Restore test completed successfully"
    resourcesRecovered: 50
    resourcesFailed: 0
  
  # Conditions for monitoring
  conditions:
    - type: RestoreCompleted
      status: "True"
      lastTransitionTime: "2025-12-31T03:45:00Z"
      reason: "VeleroRestoreCompleted"
      message: "Velero restore finished"
    
    - type: HealthChecksCompleted
      status: "True"
      lastTransitionTime: "2025-12-31T03:55:00Z"
      reason: "AllHealthChecksPassed"
      message: "All health checks passed"
    
    - type: CleanupCompleted
      status: "False"
      lastTransitionTime: "2025-12-31T03:55:00Z"
      reason: "TTLNotExpired"
      message: "Will cleanup at 2026-01-01T03:55:00Z"
```

---

## Core Components

### 1. Operator Controller (handlers.py)

**Responsibility:** Main reconciliation loop that watches Velero backups and creates restore tests.

**Key Functions:**

```python
@kopf.on.event('velero.io', 'v1', 'backups', 
               labels={'backup-type': 'validation'})
async def on_backup_created(event, logger, **kwargs):
    """
    Triggered when Velero creates a backup.
    Creates a LaziusRestoreTest resource.
    """
    # Extract backup metadata
    # Create LaziusRestoreTest CRD
    # Set owner reference (for cleanup cascade)

@kopf.on.create('lazarus.io', 'v1', 'lazarusrestoretests')
@kopf.on.update('lazarus.io', 'v1', 'lazarusrestoretests')
async def handle_restore_test(body, status, logger, **kwargs):
    """
    Main reconciliation handler.
    Orchestrates: restore → health checks → cleanup → reporting.
    """
    # Get current state from status
    # Decide next action (restore, health-check, cleanup)
    # Execute action
    # Update status with results

@kopf.on.delete('lazarus.io', 'v1', 'lazarusrestoretests')
async def on_restore_test_deleted(body, logger, **kwargs):
    """
    Cleanup when LaziusRestoreTest is deleted.
    Ensures temporary namespace is cleaned.
    """
    # Delete test namespace
    # Cancel in-flight Velero restore (if any)
    # Cleanup metrics
```

### 2. Velero Client (velero_client.py)

**Responsibility:** Abstracts Velero API calls (Kubernetes resources or REST API).

```python
class VeleroClient:
    async def get_backup(self, backup_name: str, namespace: str = 'velero')
    async def create_restore(self, backup_name: str, restore_name: str, 
                           target_namespace: str, config: RestoreConfig)
    async def wait_for_restore(self, restore_name: str, timeout: int = 600)
    async def get_restore_status(self, restore_name: str)
    async def delete_restore(self, restore_name: str)
```

### 3. Smoke Test Runner (smoke_test.py)

**Responsibility:** Executes health checks (database, HTTP, custom).

```python
class SmokeTestRunner:
    async def run_all_checks(self, health_checks: HealthCheckConfig) -> TestResults
    async def run_database_checks(self, db_config: DatabaseConfig) -> CheckResults
    async def run_http_checks(self, http_config: HTTPConfig) -> CheckResults
    async def run_custom_checks(self, custom_config: CustomCheckConfig) -> CheckResults
```

### 4. Metrics Exporter (metrics.py)

**Responsibility:** Exposes Prometheus metrics.

```python
class MetricsExporter:
    def __init__(self):
        self.restore_duration = Histogram(...)
        self.health_check_duration = Histogram(...)
        self.test_success = Counter(...)
        self.test_failure = Counter(...)
        self.recovered_resources = Gauge(...)
```

**Key Metrics:**
- `lazarus_restore_duration_seconds` - Time to restore
- `lazarus_health_check_duration_seconds` - Time to run checks
- `lazarus_test_success_total` - Successful tests
- `lazarus_test_failure_total` - Failed tests
- `lazarus_recovered_resources` - Resources count
- `lazarus_test_rto_seconds` - Measured RTO
- `lazarus_test_rpo_seconds` - Measured RPO

---

## Implementation Details

### Phase 1: Restore Creation

**Process:**
```
1. Extract backup name from spec
2. Validate backup exists in Velero
3. Generate restore name: restore-test-{backup-name}-{timestamp}
4. Create target namespace (if not exists)
5. Call Velero API to create Restore resource
6. Update status: phase=Running, restore.status=Pending
```

**Example Code:**
```python
async def create_restore(test_resource):
    backup_name = test_resource['spec']['backupName']
    restore_namespace = test_resource['spec']['restoreNamespace']
    
    # Create namespace
    await create_namespace(restore_namespace)
    
    # Create Velero Restore
    restore_spec = {
        'backupName': backup_name,
        'restorePVs': True,
        'namespaceMapping': {},
        'includeNamespaces': ['*'],
        'excludeNamespaces': ['kube-system']
    }
    
    restore = await velero_client.create_restore(
        backup_name=backup_name,
        restore_name=restore_name,
        spec=restore_spec
    )
    
    # Wait for restore completion
    await velero_client.wait_for_restore(restore_name, timeout=600)
    
    return restore
```

### Phase 2: Health Check Execution

**Database Checks:**
```python
async def run_database_checks(db_config: DatabaseConfig):
    # Connect to restored database
    conn = await connect_database(
        host=db_config.host,
        port=db_config.port,
        database=db_config.database,
        credentials=load_from_secret(db_config.credentials_secret)
    )
    
    # Run each query
    for query in db_config.queries:
        result = await conn.execute(query.sql)
        
        # Validate result
        if query.expectedRange:
            assert query.expectedRange.min <= result <= query.expectedRange.max
        elif query.expectedColumns:
            assert all(col in result for col in query.expectedColumns)
        elif query.expectedRecency:
            age_seconds = time.time() - result
            assert age_seconds < query.expectedRecency
    
    conn.close()
    return CheckResults(status='Passed')
```

### Phase 3: Cleanup

**Cleanup Strategy:**
```python
async def cleanup_after_test(test_resource):
    ttl = test_resource['spec'].get('ttl')
    namespace = test_resource['spec']['restoreNamespace']
    
    if ttl:
        # Add deletion timestamp for TTL controller
        patch_namespace_ttl(namespace, ttl)
    else:
        # Immediately delete
        await delete_namespace(namespace)
    
    # Emit metrics
    metrics.test_completed(success=True, duration=elapsed_seconds)
```

---

## Testing Strategy

### Unit Tests
```python
def test_create_restore_handler():
    # Mock Velero client
    # Call handler
    # Assert LaziusRestoreTest created correctly

def test_health_check_runner():
    # Mock database/HTTP responses
    # Call health check runner
    # Assert results correct
```

### Integration Tests
```python
async def test_end_to_end_backup_restore():
    # Setup Kind cluster with Velero
    # Create backup
    # Assert LaziusRestoreTest created
    # Wait for test to complete
    # Assert test passed
    # Assert cleanup occurred
```

---

## Deployment & Operations

### Installation via Helm
```bash
helm repo add lazarus https://charts.lazarus-operator.io
helm install lazarus lazarus/lazarus \
  --namespace lazarus-system \
  --create-namespace \
  --values values.yaml
```

### Post-Deployment Verification
```bash
# Check operator is running
kubectl get pods -n lazarus-system

# Check CRDs are installed
kubectl get crds | grep lazarus

# Test by creating a restore test
kubectl apply -f examples/lazarus-restore-test-example.yaml

# Watch progress
kubectl describe lazarusrestoretest -n lazarus-system
kubectl logs -n lazarus-system -f deployment/lazarus-operator
```

---

## Monitoring & Observability

### Prometheus Metrics

```python
from prometheus_client import start_http_server, Counter, Histogram, Gauge

# Start metrics server
start_http_server(8080)

# Define metrics
test_success = Counter('lazarus_test_success_total', 'Successful restore tests', ['backup_name'])
test_failure = Counter('lazarus_test_failure_total', 'Failed restore tests', ['backup_name'])
restore_duration = Histogram('lazarus_restore_duration_seconds', 'Restore duration', buckets=[10, 30, 60, 120, 300, 600])
```

### Grafana Dashboard Template

```json
{
  "title": "Lazarus Backup Validation",
  "panels": [
    {
      "title": "Test Success Rate",
      "targets": [{
        "expr": "sum(rate(lazarus_test_success_total[5m])) / (sum(rate(lazarus_test_success_total[5m])) + sum(rate(lazarus_test_failure_total[5m])))"
      }]
    }
  ]
}
```

---

## Security Considerations

### RBAC

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: lazarus-controller
rules:
  # LaziusRestoreTest management
  - apiGroups: ["lazarus.io"]
    resources: ["lazarusrestoretests", "lazarusrestoretests/status"]
    verbs: ["get", "list", "watch", "create", "update", "patch"]
  
  # Velero integration (read-only)
  - apiGroups: ["velero.io"]
    resources: ["backups", "restores"]
    verbs: ["get", "list", "watch"]
  
  # Namespace management
  - apiGroups: [""]
    resources: ["namespaces"]
    verbs: ["get", "list", "create", "delete"]
  
  # Pod management (for custom health checks)
  - apiGroups: [""]
    resources: ["pods", "pods/logs"]
    verbs: ["get", "list", "create", "delete"]
  
  # Secrets (read for DB credentials)
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get"]
  
  # Events
  - apiGroups: [""]
    resources: ["events"]
    verbs: ["create", "patch"]
```

---

## Project Structure

```
lazarus-operator/
│
├── src/
│   └── lazarus_operator/
│       ├── __init__.py
│       ├── handlers.py                 # Main reconciliation logic (400 lines)
│       ├── velero_client.py            # Velero API abstraction (200 lines)
│       ├── smoke_test.py               # Health check runner (300 lines)
│       ├── metrics.py                  # Prometheus metrics (150 lines)
│       ├── config.py                   # Configuration management (100 lines)
│       ├── utils.py                    # Utility functions (100 lines)
│       └── logger.py                   # Structured logging (50 lines)
│
├── tests/
│   ├── test_unit.py                    # Unit tests (400 lines)
│   ├── test_integration.py             # Integration tests (300 lines)
│   ├── fixtures.py                     # Test fixtures
│   └── conftest.py                     # Pytest configuration
│
├── deploy/
│   ├── namespace.yaml
│   ├── crd.yaml
│   ├── rbac.yaml
│   ├── operator.yaml
│   ├── config.yaml
│   └── service.yaml
│
├── helm/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│
├── examples/
│   ├── backup-test-simple.yaml
│   ├── backup-test-with-db-checks.yaml
│   └── backup-test-policy.yaml
│
├── docs/
│   ├── README.md
│   ├── INSTALLATION.md
│   ├── USAGE.md
│   └── TROUBLESHOOTING.md
│
├── Dockerfile
├── requirements.txt
├── Makefile
└── pyproject.toml
```

**Total MVP: ~4,100 lines**

---

## Development Roadmap

### Phase 1: MVP (Weeks 1-3)
**Goal:** Basic restore testing with database health checks

- [ ] Project setup (Kopf, dependencies, project structure)
- [ ] CRD definitions (LaziusRestoreTest)
- [ ] Core handlers (restore creation, status tracking)
- [ ] Velero client (create/wait/cleanup restore)
- [ ] Database health checks (connection, query validation)
- [ ] Prometheus metrics (basic)
- [ ] Kubernetes manifests (RBAC, deployment)
- [ ] Integration tests
- [ ] Documentation

**Deliverables:**
- Working operator that runs restore tests
- Passes health checks against restored database
- Cleanup and metrics

### Phase 2: Enhanced Checks (Weeks 4-5)
**Goal:** HTTP and custom check support

- [ ] HTTP health checks (endpoint validation)
- [ ] Custom check pod execution
- [ ] Parallel health check execution
- [ ] Slack notifications

### Phase 3: Automation & Policy (Weeks 6-7)
**Goal:** Schedule-based testing

- [ ] BackupTestPolicy CRD
- [ ] Cron scheduling
- [ ] Policy-based test selection

### Phase 4: Production Hardening (Weeks 8-9)
**Goal:** Production-ready

- [ ] Comprehensive error handling
- [ ] Performance optimization
- [ ] Security audit
- [ ] Helm chart

---

## Example LaziusRestoreTest

```yaml
apiVersion: lazarus.io/v1alpha1
kind: LaziusRestoreTest
metadata:
  name: test-production-db-backup-20251231
  namespace: lazarus-system
  labels:
    backup-name: production-db-backup-20251231
    environment: production

spec:
  backupName: production-db-backup-20251231
  backupNamespace: velero
  
  restoreNamespace: lazarus-test-prod-db-20251231
  
  ttl: 24h
  
  cleanup:
    enabled: true
    deleteNamespace: true
  
  healthChecks:
    enabled: true
    timeout: 600
    
    database:
      enabled: true
      type: postgres
      connectionString:
        secretRef:
          name: restore-db-creds
          key: connection-string
      
      queries:
        - name: verify-users-count
          sql: "SELECT COUNT(*) as cnt FROM users"
          expectedRange:
            min: 100000
            max: 1000000
        
        - name: verify-schema
          sql: "SELECT column_name FROM information_schema.columns WHERE table_name='users' ORDER BY column_name"
          expectedColumns:
            - created_at
            - email
            - id
            - name
            - updated_at

status:
  phase: Succeeded
  startTime: "2025-12-31T03:30:00Z"
  completionTime: "2025-12-31T03:55:00Z"
  
  restore:
    restoreName: restore-test-prod-db-20251231
    veleroPhase: Completed
    progress:
      itemsRestored: 1500
      itemsAttempted: 1500
  
  healthChecks:
    phase: Completed
    database:
      status: Passed
      checks:
        - name: verify-users-count
          status: Passed
          result: "Count: 500000 (within range)"
          duration: 3.45
        
        - name: verify-schema
          status: Passed
          result: "All columns present"
          duration: 1.23
  
  result:
    success: true
    rto: 1234
    rpo: 0
    message: "Restore test completed successfully"
    resourcesRecovered: 1500
    resourcesFailed: 0
```

---

