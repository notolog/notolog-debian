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

   # Build test (run from the repository root)
   ./pyinstaller/build.sh

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
sudo apt-get install build-essential zlib1g-dev debhelper devscripts lintian libegl1 libportaudio2

# Install Python tools
pip install reuse pre-commit

# Set up pre-commit hooks
pre-commit install
```

### Testing an application revision

On an Ubuntu 22.04 amd64 build host, populate `src/` from a Git revision so
untracked application files cannot enter the package:

```bash
APP_REPOSITORY=/absolute/path/to/notolog-editor
test ! -e src
mkdir src
git -C "$APP_REPOSITORY" archive --format=tar v1.2.3 | tar -x -C src
TARGET_SERIES_OVERRIDE=jammy ./pyinstaller/build.sh
```

Use `main` instead of `v1.2.3` to test the latest committed main branch. To test
tracked working-tree changes as well, apply them before building:

```bash
git -C "$APP_REPOSITORY" diff --binary HEAD -- |
  git apply --directory=src -
TARGET_SERIES_OVERRIDE=jammy ./pyinstaller/build.sh
```

The application version must match the upstream portion of `debian/changelog`.

Inspect the generated package before installation:

```bash
PACKAGE_PATH="../notolog_1.2.3-1ubuntu1_$(dpkg-architecture -qDEB_HOST_ARCH).deb"
dpkg-deb --info "$PACKAGE_PATH"
dpkg-deb --contents "$PACKAGE_PATH"
lintian --pedantic "$PACKAGE_PATH"
sudo apt install "$PACKAGE_PATH"
```

### Creating a release tag

After reviewing the release commit and completing a Launchpad dry run:

```bash
git switch main
git status --short
git tag -s v1.2.3-1ubuntu1 -m "Release v1.2.3-1ubuntu1"
git push origin main
git push origin v1.2.3-1ubuntu1
```

Do not move a published tag. Increment the Debian revision for a replacement
package.

## Code Style

- Shell scripts: Use `shellcheck` for linting
- Python: Follow PEP 8
- Debian files: Follow [Debian Policy](https://www.debian.org/doc/debian-policy/)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Main Application**: https://github.com/notolog/notolog-editor
**This Repository**: https://github.com/notolog/notolog-debian
