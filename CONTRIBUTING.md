# Contributing to Lazarus

First off, thank you for considering contributing to Lazarus! It's people like you that make this operator better for everyone.

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the maintainers.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce**
- **Expected vs actual behavior**
- **Environment details** (Kubernetes version, Velero version, etc.)
- **Logs** from the operator

Example:

```markdown
**Bug Description:**
Health checks fail when database uses custom port

**Steps to Reproduce:**
1. Create LaziusRestoreTest with PostgreSQL on port 5433
2. Observe connection timeout

**Expected:** Connection succeeds on custom port
**Actual:** Timeout after 30s

**Environment:**
- Kubernetes: v1.28.0
- Velero: v1.12.0
- Lazarus: v0.1.0

**Logs:**
```
[error logs here]
```
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When suggesting:

- **Use clear, descriptive title**
- **Provide detailed description** of the enhancement
- **Explain why** this would be useful
- **Include code examples** if applicable

### Pull Requests

1. **Fork** the repository
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** with clear commit messages
4. **Add tests** for new functionality
5. **Update documentation** if needed
6. **Run tests and linters**:
   ```bash
   make lint test
   ```
7. **Push to your fork** and submit a pull request

## Development Setup

### Prerequisites

- Python 3.11+
- Poetry
- Docker
- Kind (for local testing)

### Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/lazarus-operator.git
cd lazarus-operator

# Install dependencies
make dev

# Run pre-commit hooks
poetry run pre-commit install

# Run tests
make test
```

### Local Testing

```bash
# Create Kind cluster
make kind-setup

# Deploy operator
make deploy-dev

# View logs
make logs

# Cleanup
make kind-teardown
```

## Style Guide

### Python Code

We follow PEP 8 with some modifications:

- **Line length**: 100 characters
- **Type hints**: Required for all functions
- **Docstrings**: Google style for all public functions/classes

```python
def create_restore(backup_name: str, config: RestoreConfig) -> Restore:
    """Create a Velero restore from backup.

    Args:
        backup_name: Name of the backup to restore
        config: Restore configuration

    Returns:
        Created restore resource

    Raises:
        ValueError: If backup_name is empty
        ApiException: If Kubernetes API call fails
    """
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add support for MongoDB health checks
fix: resolve race condition in cleanup
docs: update installation guide
test: add tests for VeleroClient
refactor: simplify health check runner
chore: update dependencies
```

### Testing

- **Unit tests**: Test individual functions/classes
- **Integration tests**: Test component interactions
- **Coverage**: Maintain >80% code coverage

```python
@pytest.mark.asyncio
async def test_velero_client_create_restore():
    """Test creating a Velero restore."""
    # Arrange
    client = VeleroClient()
    config = VeleroRestoreConfig(...)
    
    # Act
    restore = await client.create_restore("test-restore", config)
    
    # Assert
    assert restore["metadata"]["name"] == "test-restore"
```

## Documentation

- **Code comments**: Explain *why*, not *what*
- **README**: Keep up-to-date with features
- **Docs**: Update relevant docs with changes
- **Examples**: Add examples for new features

## Review Process

1. **Automated checks**: Must pass CI/CD
2. **Code review**: At least one maintainer approval
3. **Documentation**: Must be updated if applicable
4. **Tests**: Must include tests for new features

## Release Process

Releases are automated via GitHub Actions:

1. Create tag: `git tag -a v0.2.0 -m "Release v0.2.0"`
2. Push tag: `git push origin v0.2.0`
3. GitHub Actions builds and publishes release

## Questions?

- **GitHub Issues**: For bugs and features
- **Discussions**: For questions and ideas
- **Email**: maintainer@example.com

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
