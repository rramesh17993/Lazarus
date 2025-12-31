# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: security@example.com

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

Please include the following information:

- Type of issue (e.g. buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

## Security Best Practices

When deploying Lazarus:

### RBAC
- Use least-privilege RBAC policies
- Don't grant unnecessary permissions
- Review ClusterRole permissions regularly

### Secrets
- Store database credentials in Kubernetes Secrets
- Use secret rotation
- Don't commit secrets to version control

### Network
- Use NetworkPolicies to restrict operator access
- Isolate test namespaces
- Limit egress to necessary endpoints

### Container Security
- Operator runs as non-root user (UID 1000)
- Read-only root filesystem
- No privilege escalation
- Minimal base image (Python slim)

### Updates
- Keep operator updated to latest version
- Monitor security advisories
- Apply patches promptly

## Vulnerability Disclosure Process

1. **Report received**: Security team acknowledges receipt
2. **Assessment**: Team evaluates severity and impact
3. **Fix development**: Patch developed and tested
4. **Release**: Security release published
5. **Disclosure**: Public advisory after users can update

## Known Security Considerations

### Backup Data Access
The operator needs read access to Velero backups and ability to create restores. Ensure:
- Backup storage credentials are properly secured
- Test namespaces are isolated
- Cleanup removes sensitive data

### Database Credentials
Health checks may require database credentials. Ensure:
- Use Kubernetes Secrets for connection strings
- Rotate credentials regularly
- Limit secret access via RBAC

### Cleanup
Test resources are cleaned automatically but:
- Set appropriate TTLs
- Monitor for orphaned resources
- Verify cleanup completes

## Security Updates

Subscribe to security updates:
- Watch repository for security advisories
- Join mailing list: security-announce@example.com
- Check CHANGELOG.md for security fixes
