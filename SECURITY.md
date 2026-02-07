<!-- {"notolog.app": {"created": "2026-02-07 00:00:00.000000", "updated": "2026-02-07 00:00:00.000000"}} -->
# Security Policy

This document covers security for the **Debian package builder** repository.
For application security, see the [main application repository](https://github.com/notolog/notolog-editor/blob/main/SECURITY.md).

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.2.x   | :white_check_mark: |
| 1.1.x   | :white_check_mark: |
| < 1.1   | :x:                |

## Reporting a Vulnerability

### How to Report

**Do NOT open a public GitHub issue for security vulnerabilities.**

Report security vulnerabilities by:

1. Go to the [Security tab](https://github.com/notolog/notolog-debian/security) of this repository
2. Click "Report a vulnerability"
3. Provide detailed information about the vulnerability

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Resolution Target**: Within 30 days (depending on severity)

## Build Security

### GPG Signing

All packages uploaded to Launchpad PPA are GPG signed:

- Source packages are signed with maintainer's GPG key
- Use 4096-bit RSA keys
- Upload key to `keyserver.ubuntu.com`

### PIE Hardening

PyInstaller binaries are built with PIE (Position Independent Executable) hardening:

```bash
# Verify PIE on built binary
hardening-check pyinstaller/dist/notolog
```

## Acknowledgments

We thank all security researchers who responsibly disclose vulnerabilities.

---

*Last updated: February 2026*
