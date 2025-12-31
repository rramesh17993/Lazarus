# Lazarus: Automated Backup Recovery Validation Operator

<div align="center">

![Lazarus Logo](docs/images/logo.png)

**Never trust a backup you haven't tested.**

[![CI](https://github.com/yourusername/lazarus-operator/actions/workflows/ci.yaml/badge.svg)](https://github.com/yourusername/lazarus-operator/actions)
[![Coverage](https://codecov.io/gh/yourusername/lazarus-operator/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/lazarus-operator)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Kubernetes](https://img.shields.io/badge/kubernetes-1.25+-blue.svg)](https://kubernetes.io/)

</div>

## Overview

**Lazarus** is a production-grade Kubernetes operator that automatically validates backup recovery by creating isolated test restores, running health checks, and measuring recovery metrics (RTO/RPO). Built with [Kopf](https://kopf.readthedocs.io/) and designed to integrate seamlessly with [Velero](https://velero.io/).

### The Problem

Organizations invest heavily in backup infrastructure, but **most backups are never tested until disaster strikes**. When that happens, teams discover:

- Backups are corrupted or incomplete
- Recovery procedures don't work as documented
- RTO/RPO SLAs are wildly inaccurate
- No one knows how to actually restore

**Result:** Extended downtime, data loss, angry customers, and career-limiting events.

### The Solution

Lazarus **automatically tests every backup** by:

1. **Detecting** Velero backup completion
2. **Creating** isolated test restores in temporary namespaces
3. **Validating** resources with configurable health checks (database queries, HTTP endpoints, custom tests)
4. **Measuring** actual RTO/RPO metrics
5. **Alerting** on failures via Slack/PagerDuty
6. **Cleaning up** test resources automatically

## Features

- **Fully Automated** - Zero manual intervention required
- **Velero Integration** - Native support for Velero backups and restores
- **Health Checks** - Database, HTTP, and custom validation
- **Prometheus Metrics** - Production-ready observability
- **Smart Notifications** - Slack alerts on failures
- **Isolated Testing** - Test namespaces with configurable TTL
- **Fast & Efficient** - Parallel health checks, async operations
- **Secure** - Non-root containers, RBAC policies, secret handling
- **Helm Chart** - Production-ready deployment
- **Portfolio-Ready** - Clean code, comprehensive tests, excellent documentation

## 🚀 Quick Start

### Prerequisites

- Kubernetes 1.25+
- Velero installed and configured
- Helm 3.x

### Installation

```bash
# Add Helm repository
helm repo add lazarus https://yourusername.github.io/lazarus-operator
helm repo update

# Install operator
helm install lazarus lazarus/lazarus \
  --namespace lazarus-system \
  --create-namespace \
  --set config.velero.namespace=velero

# Verify installation
kubectl get pods -n lazarus-system
kubectl get crds | grep lazarus
```

### Create Your First Test

```bash
# Create a simple restore test
cat <<EOF | kubectl apply -f -
apiVersion: lazarus.io/v1alpha1
kind: LaziusRestoreTest
metadata:
  name: my-first-test
  namespace: lazarus-system
spec:
  backupName: my-app-backup-20251231
  healthChecks:
    enabled: true
    http:
      enabled: true
      endpoints:
        - name: app-health
          url: http://my-app:8080/health
          expectedStatus: 200
EOF

# Watch progress
kubectl get lazarusrestoretests -n lazarus-system -w
kubectl describe lazarusrestoretest my-first-test -n lazarus-system
```

## Documentation

- **[Installation Guide](docs/installation.md)** - Detailed setup instructions
- **[Usage Guide](docs/usage.md)** - Creating and managing restore tests
- **[Configuration Reference](docs/configuration.md)** - All configuration options
- **[Health Checks](docs/health-checks.md)** - Database, HTTP, and custom checks
- **[Metrics & Monitoring](docs/metrics.md)** - Prometheus integration
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions
- **[Architecture](docs/architecture.md)** - Design and implementation details
- **[Development](docs/development.md)** - Contributing guide

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Kubernetes Cluster                    │
└─────────────────────────────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
   ┌──────────────────┐    ┌──────────────────┐
   │   Velero         │    │  Lazarus         │
   │   (Backups)      │    │  (Operator)      │
   └────────┬─────────┘    └────────┬─────────┘
            │                       │
   Backup Completed            Creates Test
            │                       │
            └───────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    Restore      Health Checks   Metrics
    Resources    (DB/HTTP/Custom) (Prometheus)
```

## Key Metrics

Lazarus exposes production-ready Prometheus metrics:

```promql
# Test success rate (last 24h)
sum(rate(lazarus_restore_tests_total{result="success"}[24h])) 
/ sum(rate(lazarus_restore_tests_total[24h]))

# Average RTO by backup
avg(lazarus_recovery_time_objective_seconds) by (backup_name)

# Failed tests requiring attention
lazarus_restore_tests_total{result="failure"}
```

## 🎯 Use Cases

### 1. **Automated Backup Validation**
Test every backup immediately after creation to catch corruption early.

### 2. **Compliance & Auditing**
Demonstrate backup recoverability for SOC2, HIPAA, PCI-DSS audits.

### 3. **RTO/RPO Validation**
Measure actual recovery times vs. SLA commitments.

### 4. **Disaster Recovery Testing**
Run weekly/monthly DR drills automatically without manual effort.

### 5. **Pre-Production Validation**
Test backups before promoting to production.

## 🛠️ Technology Stack

- **Python 3.11+** - Modern, type-safe Python
- **Kopf** - Kubernetes operator framework
- **Kubernetes Client** - Official Python client
- **Prometheus Client** - Metrics and monitoring
- **AsyncIO** - Concurrent operations
- **Pydantic** - Configuration validation
- **StructLog** - Structured logging
- **Poetry** - Dependency management
- **Pytest** - Comprehensive testing
- **Black/Ruff** - Code formatting and linting
- **MyPy** - Static type checking

## 🧪 Testing

```bash
# Run unit tests
make test

# Run with coverage
make test-coverage

# Run linters
make lint

# Format code
make format

# Run all checks
make test lint
```

## 📈 Roadmap

- [x] Core operator functionality
- [x] Database health checks (PostgreSQL, MySQL, MongoDB)
- [x] HTTP endpoint validation
- [x] Prometheus metrics
- [x] Slack notifications
- [x] Helm chart
- [ ] Custom pod-based health checks
- [ ] Policy-based scheduled testing
- [ ] Multi-cluster support
- [ ] Advanced data validation (checksums, row counts)
- [ ] PagerDuty integration
- [ ] Grafana dashboard templates
- [ ] Cost tracking per test

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[Velero](https://velero.io/)** - Kubernetes backup and restore
- **[Kopf](https://kopf.readthedocs.io/)** - Kubernetes operator framework
- Inspired by the need for reliable disaster recovery in production systems

## 📧 Contact

- **Author:** Rajesh Ramesh
- **Email:** rramesh17993@gmail.com
- **GitHub:** [@rramesh17993](https://github.com/rramesh17993)
- **LinkedIn:** [Your Profile](https://linkedin.com/in/rajesh-ramesh)

---

<div align="center">

**⭐ Star this repo if you find it useful! ⭐**

Built with ❤️ for SREs, Platform Engineers, and anyone who cares about reliable backups.

</div>
