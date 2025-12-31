# Usage Guide

## Creating Restore Tests

### Basic Test

The simplest restore test validates that a backup can be restored:

```yaml
apiVersion: lazarus.io/v1alpha1
kind: LaziusRestoreTest
metadata:
  name: my-backup-test
  namespace: lazarus-system
spec:
  backupName: my-app-backup-20251231
  backupNamespace: velero
```

Apply it:

```bash
kubectl apply -f basic-test.yaml
```

### Watch Test Progress

```bash
# Watch status
kubectl get lazarusrestoretest my-backup-test -n lazarus-system -w

# Detailed status
kubectl describe lazarusrestoretest my-backup-test -n lazarus-system

# View operator logs
kubectl logs -n lazarus-system -l app.kubernetes.io/name=lazarus-operator -f
```

### Test with Health Checks

Add HTTP endpoint validation:

```yaml
apiVersion: lazarus.io/v1alpha1
kind: LaziusRestoreTest
metadata:
  name: app-with-health-check
  namespace: lazarus-system
spec:
  backupName: my-app-backup-20251231
  
  healthChecks:
    enabled: true
    timeout: 300
    retries: 3
    
    http:
      enabled: true
      endpoints:
        - name: app-health
          url: http://my-app-service:8080/health
          expectedStatus: 200
```

### Database Validation

Test PostgreSQL backup with data validation:

```yaml
apiVersion: lazarus.io/v1alpha1
kind: LaziusRestoreTest
metadata:
  name: postgres-backup-test
  namespace: lazarus-system
spec:
  backupName: postgres-backup-20251231
  
  healthChecks:
    enabled: true
    database:
      enabled: true
      type: postgres
      connectionString:
        secretRef:
          name: postgres-creds
          key: connection-string
      
      queries:
        - name: record-count
          sql: "SELECT COUNT(*) FROM users"
          expectedRange:
            min: 1000
            max: 1000000
        
        - name: data-freshness
          sql: "SELECT MAX(updated_at) FROM users"
          expectedRecency: 3600  # Within 1 hour
```

### With Notifications

Get alerted on failures:

```yaml
apiVersion: lazarus.io/v1alpha1
kind: LaziusRestoreTest
metadata:
  name: critical-backup-test
  namespace: lazarus-system
spec:
  backupName: critical-app-backup-20251231
  
  notifications:
    onSuccess:
      slack:
        enabled: true
        channel: "#backups"
    
    onFailure:
      slack:
        enabled: true
        channel: "#backup-alerts"
        mentionOnFailure: "@oncall"
```

## Managing Tests

### List All Tests

```bash
# All tests
kubectl get lazarusrestoretests -A

# With custom columns
kubectl get lazarusrestoretests -A \
  -o custom-columns=\
NAME:.metadata.name,\
BACKUP:.spec.backupName,\
PHASE:.status.phase,\
SUCCESS:.status.result.success,\
RTO:.status.result.rto
```

### View Test Status

```bash
# Quick status
kubectl get lazarusrestoretest my-test -n lazarus-system

# Detailed info
kubectl describe lazarusrestoretest my-test -n lazarus-system

# Just the status
kubectl get lazarusrestoretest my-test -n lazarus-system -o jsonpath='{.status}' | jq
```

### Delete Tests

```bash
# Delete single test
kubectl delete lazarusrestoretest my-test -n lazarus-system

# Delete all completed tests
kubectl delete lazarusrestoretests -n lazarus-system \
  --field-selector status.phase=Succeeded

# Delete tests older than 7 days
kubectl get lazarusrestoretests -A -o json | \
  jq -r '.items[] | select(.metadata.creationTimestamp < (now - 604800 | todate)) | .metadata.name' | \
  xargs kubectl delete lazarusrestoretest -n lazarus-system
```

## Common Workflows

### Automated Testing After Backup

Create a LaziusRestoreTest after each Velero backup:

```bash
# Watch for new backups
kubectl get backups -n velero --watch-only | while read line; do
  BACKUP_NAME=$(echo $line | awk '{print $1}')
  
  cat <<EOF | kubectl apply -f -
apiVersion: lazarus.io/v1alpha1
kind: LaziusRestoreTest
metadata:
  name: test-$BACKUP_NAME
  namespace: lazarus-system
spec:
  backupName: $BACKUP_NAME
  healthChecks:
    enabled: true
EOF
done
```

### Scheduled Testing

Use CronJob to test backups periodically:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: weekly-backup-test
  namespace: lazarus-system
spec:
  schedule: "0 2 * * 0"  # Every Sunday at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: create-test
            image: bitnami/kubectl:latest
            command:
            - /bin/sh
            - -c
            - |
              LATEST_BACKUP=$(kubectl get backups -n velero -o json | \
                jq -r '.items | sort_by(.metadata.creationTimestamp) | reverse | .[0].metadata.name')
              
              kubectl apply -f - <<EOF
              apiVersion: lazarus.io/v1alpha1
              kind: LaziusRestoreTest
              metadata:
                name: weekly-test-$(date +%Y%m%d)
                namespace: lazarus-system
              spec:
                backupName: $LATEST_BACKUP
                healthChecks:
                  enabled: true
              EOF
          restartPolicy: OnFailure
```

### Testing Multiple Backups

Test all recent backups:

```bash
#!/bin/bash
# test-recent-backups.sh

LOOKBACK_DAYS=7

kubectl get backups -n velero -o json | \
  jq -r ".items[] | select(.metadata.creationTimestamp > (now - (${LOOKBACK_DAYS} * 86400) | todate)) | .metadata.name" | \
  while read backup; do
    echo "Creating test for backup: $backup"
    
    cat <<EOF | kubectl apply -f -
apiVersion: lazarus.io/v1alpha1
kind: LaziusRestoreTest
metadata:
  name: test-$backup
  namespace: lazarus-system
spec:
  backupName: $backup
  healthChecks:
    enabled: true
  ttl: 1h
EOF
  done
```

## Monitoring Tests

### View Metrics

```bash
# Port-forward to metrics endpoint
kubectl port-forward -n lazarus-system svc/lazarus-operator-metrics 8080:8080

# Query metrics
curl http://localhost:8080/metrics | grep lazarus
```

### Check Test Results

```bash
# Success rate
kubectl get lazarusrestoretests -A -o json | \
  jq '[.items[] | .status.result.success] | group_by(.) | map({key: .[0], count: length}) | from_entries'

# Average RTO
kubectl get lazarusrestoretests -A -o json | \
  jq '[.items[] | .status.result.rto] | add / length'

# Failed tests
kubectl get lazarusrestoretests -A -o json | \
  jq '.items[] | select(.status.result.success == false) | {name: .metadata.name, message: .status.result.message}'
```

## Best Practices

### 1. Use Labels

Organize tests with labels:

```yaml
metadata:
  labels:
    environment: production
    application: my-app
    criticality: high
```

Query by labels:

```bash
kubectl get lazarusrestoretests -A -l environment=production
```

### 2. Set Appropriate TTLs

```yaml
spec:
  ttl: 24h  # Keep for debugging
  cleanup:
    enabled: true
```

### 3. Test Representative Backups

Don't test every backup - test:
- Latest backup (data freshness)
- Random older backup (corruption detection)
- Different backup types (full, incremental)

### 4. Use Namespace Isolation

Test in dedicated namespaces:

```yaml
spec:
  restoreNamespace: lazarus-test-myapp
```

### 5. Health Check Timeouts

Set realistic timeouts:

```yaml
healthChecks:
  timeout: 600  # 10 minutes for large restores
  retries: 3
```

## Troubleshooting

### Test Stuck in "Running"

```bash
# Check restore status
kubectl get restore -n velero | grep test

# Check test namespace
TEST_NS=$(kubectl get lazarusrestoretest my-test -n lazarus-system -o jsonpath='{.spec.restoreNamespace}')
kubectl get pods -n $TEST_NS

# Check operator logs
kubectl logs -n lazarus-system -l app.kubernetes.io/name=lazarus-operator --tail=100
```

### Health Checks Failing

```bash
# Get detailed status
kubectl get lazarusrestoretest my-test -n lazarus-system -o jsonpath='{.status.healthChecks}' | jq

# Check service accessibility
TEST_NS=$(kubectl get lazarusrestoretest my-test -n lazarus-system -o jsonpath='{.spec.restoreNamespace}')
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n $TEST_NS -- \
  curl -v http://my-service:8080/health
```

## Next Steps

- [Configuration Reference](configuration.md) - All configuration options
- [Health Checks](health-checks.md) - Advanced health check configuration
- [Metrics](metrics.md) - Monitoring and alerting
