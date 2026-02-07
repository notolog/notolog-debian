<!-- {"notolog.app": {"created": "2026-02-07 00:00:00.000000", "updated": "2026-02-07 00:00:00.000000"}} -->
# Contributing to Notolog Debian Package Builder

Thank you for your interest in contributing to the Notolog Debian package builder!

This repository contains the build scripts and Debian packaging files for [Notolog Editor](https://github.com/notolog/notolog-editor).

## How to Contribute

### Reporting Issues

- **Build issues**: Open an issue in this repository
- **Application bugs**: Report to [notolog-editor issues](https://github.com/notolog/notolog-editor/issues)

### Pull Requests

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Make your changes
4. Run quality checks:
   ```bash
   # Lint check
   reuse lint

   # Build test
   cd pyinstaller && ./build.sh

   # Package validation
   lintian --pedantic ../notolog_*.deb
   ```
5. Commit with clear messages
6. Push and open a Pull Request

### Areas for Contribution

- **Multi-architecture support**: ARM64 builds, testing on different platforms
- **CI/CD improvements**: GitHub Actions workflow enhancements
- **Documentation**: README updates, build guides
- **Packaging**: Debian policy compliance, lintian fixes

## Development Setup

```bash
# Clone the repository
git clone https://github.com/notolog/notolog-debian.git
cd notolog-debian

# Install build dependencies
sudo apt-get install build-essential debhelper devscripts lintian

# Install Python tools
pip install reuse pre-commit

# Set up pre-commit hooks
pre-commit install
```

## Code Style

- Shell scripts: Use `shellcheck` for linting
- Python: Follow PEP 8
- Debian files: Follow [Debian Policy](https://www.debian.org/doc/debian-policy/)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Main Application**: https://github.com/notolog/notolog-editor
**This Repository**: https://github.com/notolog/notolog-debian
