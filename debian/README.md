# Build Debian Package

This document provides instructions to build and maintain the Debian package for Notolog Editor.

## Requirements

Install the required system build dependencies:
```bash
sudo apt-get install build-essential devscripts debhelper lintian zlib1g-dev libegl1 libportaudio2
```

Python 3.14 is required to create the standalone executable. Python build
dependencies are installed into the builder-owned `venv/` directory.

## Building the Package

Clone or copy the matching Notolog source into `src/`, then run:
```bash
./pyinstaller/build.sh
```

The script builds and audits the PyInstaller executable before invoking
`dpkg-buildpackage -us -uc -b`. Set `PYTHON_BIN` when Python 3.14 is not the
default `python3` executable.

## Cleaning Build Artifacts and Cache

To remove only artifacts owned by this builder:
```bash
./pyinstaller/clean-build.sh
```

## Installing the Package

To install the generated package:
```bash
# Standard installation if the package is in the parent directory
sudo apt install ../notolog_X.Y.Z-REVISION_ARCH.deb
```

To uninstall:
```bash
# Using APT (preferred, handles dependencies cleanly)
sudo apt-get remove notolog

# Or, using dpkg directly (use with care - does not resolve dependencies)
sudo dpkg -r notolog
```

## Optional Checks

Inspect `.deb` contents (useful before upload):
```bash
dpkg-deb -c ../notolog_X.Y.Z_ARCH.deb
```

Lint your .deb for policy compliance:
```bash
lintian ../notolog_X.Y.Z_ARCH.deb
```

Retrieve version or metadata from `debian/changelog` programmatically:
```bash
# Extract current package version
VERSION=$(dpkg-parsechangelog --show-field Version)
echo "Packaging Notolog version $VERSION"
```

---
_This README.md file has been carefully crafted and edited using the Notolog Editor itself._
