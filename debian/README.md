<!-- {"notolog.app": {"created": "2025-04-01 00:00:00.000000", "updated": "2025-02-07 00:00:00.000000"}} -->
# Build Debian Package

This document provides instructions to build and maintain the Debian package for Notolog Editor.

## Requirements

Install the required build dependencies:
```bash
sudo apt-get install build-essential devscripts fakeroot debhelper
```

## Building the Package

Run the following command to build the Debian package:
```bash
dpkg-buildpackage -us -uc
```

For production or CI builds, use:

```bash
dpkg-buildpackage -rfakeroot -us -uc -b
```

* -rfakeroot: simulates root ownership during packaging, ensuring correct file metadata in .deb without needing real root.
* -b: builds only the binary package (skips source tarball, .dsc, etc.).

To specify a custom output directory for the built `.deb` files (instead of the default ../), modify `debian/rules` to include:
```makefile
# Specify a custom output directory for the built `.deb` files
override_dh_builddeb:
    mkdir -p debian/build
    dh_builddeb --destdir=debian/build
```

For production builds, use the `-b` option to build only the binary package. This skips source-related files (e.g., .dsc, .tar.gz), which are not required for binary distributions:
```bash
dpkg-buildpackage -us -uc -b
```

## Cleaning Build Artifacts and Cache

To clean up build files and APT cache:
```bash
dpkg-buildpackage -T clean
sudo apt-get clean
# Optional: remove unused packages and update lists
sudo apt-get autoremove
sudo apt-get update
```

## Installing the Package

To install the generated package:
```bash
# Standard installation if the package is in the parent directory
dpkg -i ../notolog_X.Y.Z_amd64.deb

# Or, if using a custom output directory
dpkg -i debian/build/notolog_X.Y.Z_amd64.deb
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
dpkg-deb -c ../notolog_X.Y.Z_amd64.deb
```

Lint your .deb for policy compliance:
```bash
lintian -i ../notolog_X.Y.Z_amd64.deb
```

Retrieve version or metadata from `debian/changelog` programmatically:
```bash
# Extract current package version
VERSION=$(dpkg-parsechangelog --show-field Version)
echo "Packaging Notolog version $VERSION"
```

---
_This README.md file has been carefully crafted and edited using the Notolog Editor itself._
