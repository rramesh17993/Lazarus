#!/bin/bash
set -e

# Lazarus Operator - Quick Start Script
# This script helps you get started with Lazarus in minutes

echo "Lazarus Operator - Quick Start"
echo "=================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

command -v kubectl >/dev/null 2>&1 || { echo "ERROR: kubectl is required but not installed. Aborting." >&2; exit 1; }
command -v helm >/dev/null 2>&1 || { echo "ERROR: helm is required but not installed. Aborting." >&2; exit 1; }

echo "Prerequisites check passed"
echo ""

# Check if Velero is installed
echo "Checking for Velero installation..."
if kubectl get namespace velero >/dev/null 2>&1; then
    echo "Velero namespace found"
else
    echo "WARNING: Velero not found. Please install Velero first:"
    echo "   https://velero.io/docs/main/basic-install/"
    exit 1
fi

# Check if cluster is accessible
echo "Verifying cluster access..."
kubectl cluster-info >/dev/null 2>&1 || { echo "ERROR: Cannot access Kubernetes cluster. Check your kubeconfig." >&2; exit 1; }
echo "Cluster access verified"
echo ""

# Install using kubectl (raw manifests)
echo "Installing Lazarus operator..."
echo ""

# Create namespace
kubectl apply -f deploy/namespace.yaml

# Install CRD
kubectl apply -f deploy/crd.yaml

# Setup RBAC
kubectl apply -f deploy/rbac.yaml

# Create ConfigMap
kubectl apply -f deploy/configmap.yaml

# Deploy operator
kubectl apply -f deploy/deployment.yaml

# Create service
kubectl apply -f deploy/service.yaml

echo ""
echo "Waiting for operator to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=lazarus-operator -n lazarus-system --timeout=120s

echo ""
echo "Lazarus operator installed successfully!"
echo ""

# Show status
echo "Current status:"
kubectl get pods -n lazarus-system
echo ""

# Show next steps
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "==========="
echo ""
echo "1. View operator logs:"
echo "   kubectl logs -n lazarus-system -l app.kubernetes.io/name=lazarus-operator -f"
echo ""
echo "2. Create your first restore test:"
echo "   kubectl apply -f examples/simple-restore-test.yaml"
echo ""
echo "3. Watch test progress:"
echo "   kubectl get lazarusrestoretests -A -w"
echo ""
echo "4. View detailed status:"
echo "   kubectl describe lazarusrestoretest <test-name> -n lazarus-system"
echo ""
echo "5. Access metrics:"
echo "   kubectl port-forward -n lazarus-system svc/lazarus-operator-metrics 8080:8080"
echo "   curl http://localhost:8080/metrics"
echo ""
echo "Documentation: ./docs/"
echo "Examples: ./examples/"
echo "Issues: https://github.com/yourusername/lazarus-operator/issues"
echo ""
echo "Happy backup testing!"
