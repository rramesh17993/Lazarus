# Changelog

All notable changes to Lazarus operator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Custom pod-based health checks
- Policy-based scheduled testing
- Multi-cluster support
- PagerDuty integration
- Grafana dashboard templates

## [0.1.0] - 2025-12-31

### Added
- Initial release of Lazarus operator
- Core operator functionality with Kopf
- Integration with Velero backups and restores
- LaziusRestoreTest Custom Resource Definition
- Database health checks (PostgreSQL, MySQL, MongoDB)
- HTTP endpoint health checks
- Prometheus metrics export
- Slack notification support
- Automatic cleanup with configurable TTL
- RTO/RPO measurement and tracking
- Helm chart for deployment
- Comprehensive documentation
- Unit and integration tests
- CI/CD pipeline with GitHub Actions

### Features
- **Automated Testing**: Automatically creates test restores for Velero backups
- **Health Validation**: Configurable health checks for restored resources
- **Metrics**: Production-ready Prometheus metrics
- **Notifications**: Slack alerts on test failures
- **Isolated Testing**: Test namespaces with automatic cleanup
- **Observability**: Structured logging and Kubernetes events
- **Security**: RBAC policies, non-root containers, secret handling

### Documentation
- Installation guide
- Usage guide with examples
- Configuration reference
- Health checks documentation
- Metrics and monitoring guide
- Troubleshooting guide
- Architecture documentation
- Contributing guidelines

[Unreleased]: https://github.com/yourusername/lazarus-operator/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/lazarus-operator/releases/tag/v0.1.0
