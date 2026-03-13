# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | Yes       |
| < 1.0   | No        |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** open a public GitHub issue
2. Email the maintainers or use [GitHub Security Advisories](https://github.com/vukhanhtruong/flux/security/advisories/new)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will acknowledge receipt within 48 hours and aim to release a fix within 7 days for critical issues.

## Security Practices

- All SQL uses parameterized queries (never string interpolation)
- Secrets are loaded from environment variables, never hardcoded
- Docker container runs as non-root user
- CI includes pip-audit and Trivy security scanning
- Config files are written with restrictive permissions (0600)
- Financial data stays on your infrastructure (self-hosted)
