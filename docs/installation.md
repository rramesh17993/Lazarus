# Installation Guide

## Prerequisites

Before installing Lazarus, ensure you have:

### Required
- **Kubernetes Cluster**: v1.25 or later
- **Velero**: Installed and configured with at least one backup location
- **Helm**: v3.x for installing the operator
- **kubectl**: Configured to access your cluster

### Optional
- **Prometheus Operator**: For ServiceMonitor support
- **Slack Webhook**: For failure notifications

## Verify Prerequisites

```bash
# Check Kubernetes version
kubectl version --short

# Verify Velero installation
kubectl get deployment -n velero
kubectl get backupstoragelocation -n velero

# Check Helm version
helm version
```

## Installation Methods

### Method 1: Helm (Recommended)

#### Quick Install

```bash
# Add Helm repository
helm repo add lazarus https://yourusername.github.io/lazarus-operator
helm repo update

# Install with default values
helm install lazarus lazarus/lazarus \
  --namespace lazarus-system \
  --create-namespace
```

#### Custom Values

Create a `values.yaml` file:

```yaml
# values.yaml
config:
  velero:
    namespace: velero  # Your Velero namespace
  
  notifications:
    slack:
      enabled: true
      webhookUrl: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
      channel: "#backup-alerts"

  metrics:
    enabled: true

serviceMonitor:
  enabled: true  # If using Prometheus Operator
  labels:
    prometheus: kube-prometheus
```

Install with custom values:

```bash
helm install lazarus lazarus/lazarus \
  --namespace lazarus-system \
  --create-namespace \
  --values values.yaml
```

### Method 2: kubectl (Raw Manifests)

```bash
# Clone repository
git clone https://github.com/yourusername/lazarus-operator.git
cd lazarus-operator

# Apply manifests
kubectl apply -f deploy/namespace.yaml
kubectl apply -f deploy/crd.yaml
kubectl apply -f deploy/rbac.yaml
kubectl apply -f deploy/configmap.yaml
kubectl apply -f deploy/deployment.yaml
kubectl apply -f deploy/service.yaml
```

### Method 3: Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/lazarus-operator.git
cd lazarus-operator

# Install dependencies
make dev

# Setup Kind cluster (optional)
make kind-setup

# Deploy to Kind
make deploy-dev
```

## Post-Installation

### Verify Installation

```bash
# Check operator pod
kubectl get pods -n lazarus-system
kubectl logs -n lazarus-system -l app.kubernetes.io/name=lazarus-operator

# Verify CRD installation
kubectl get crd lazarusrestoretests.lazarus.io
kubectl explain lazarusrestoretest

# Check RBAC
kubectl get clusterrole lazarus-operator
kubectl get clusterrolebinding lazarus-operator
```

Expected output:
```
NAME                             READY   STATUS    RESTARTS   AGE
lazarus-operator-xxxxxxxxx-xxxxx 1/1     Running   0          30s
```

### Test Installation

Create a test resource:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: lazarus.io/v1alpha1
kind: LaziusRestoreTest
metadata:
  name: installation-test
  namespace: lazarus-system
spec:
  backupName: test-backup
  healthChecks:
    enabled: false  # Skip health checks for now
EOF

# Watch the test
kubectl get lazarusrestoretest installation-test -n lazarus-system -w
```

## Configuration

### Environment Variables

The operator supports configuration via environment variables:

```bash
# Log level
LAZARUS_LOG_LEVEL=INFO

# Operator namespace
LAZARUS_NAMESPACE=lazarus-system

# Velero namespace
LAZARUS_VELERO_NAMESPACE=velero

# Metrics
LAZARUS_ENABLE_METRICS=true
LAZARUS_METRICS_PORT=8080

# Notifications
LAZARUS_SLACK_WEBHOOK_URL=https://hooks.slack.com/...
LAZARUS_ENABLE_SLACK_NOTIFICATIONS=true
```

### ConfigMap

Edit the operator ConfigMap:

```bash
kubectl edit configmap lazarus-operator-config -n lazarus-system
```

## Upgrading

### Helm Upgrade

```bash
# Update repository
helm repo update

# Upgrade release
helm upgrade lazarus lazarus/lazarus \
  --namespace lazarus-system \
  --values values.yaml
```

### Rolling Back

```bash
# View history
helm history lazarus -n lazarus-system

# Rollback to previous version
helm rollback lazarus -n lazarus-system
```

## Uninstallation

### Helm Uninstall

```bash
# Uninstall operator
helm uninstall lazarus --namespace lazarus-system

# Delete namespace (optional)
kubectl delete namespace lazarus-system
```

### Manual Cleanup

```bash
# Delete all LaziusRestoreTest resources
kubectl delete lazarusrestoretests --all -A

# Delete operator resources
kubectl delete -f deploy/

# Delete CRD (this will delete all custom resources)
kubectl delete crd lazarusrestoretests.lazarus.io
```

## Troubleshooting

### Operator Not Starting

```bash
# Check pod status
kubectl describe pod -n lazarus-system -l app.kubernetes.io/name=lazarus-operator

# Check logs
kubectl logs -n lazarus-system -l app.kubernetes.io/name=lazarus-operator --tail=100

# Common issues:
# - RBAC permissions missing
# - Invalid configuration
# - Network connectivity to Kubernetes API
```

### CRD Installation Failed

```bash
# Verify CRD is installed
kubectl get crd lazarusrestoretests.lazarus.io

# Reinstall CRD
kubectl apply -f deploy/crd.yaml

# Check API resources
kubectl api-resources | grep lazarus
```

### RBAC Errors

```bash
# Verify RBAC resources
kubectl get clusterrole lazarus-operator
kubectl get clusterrolebinding lazarus-operator
kubectl get serviceaccount lazarus-operator -n lazarus-system

# Check operator can access Velero
kubectl auth can-i get backups --as=system:serviceaccount:lazarus-system:lazarus-operator -n velero
```

## Next Steps

- [Usage Guide](usage.md) - Create your first restore test
- [Configuration Reference](configuration.md) - Detailed configuration options
- [Health Checks](health-checks.md) - Configure validation checks
