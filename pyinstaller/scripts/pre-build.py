# Debian Package Builder for Notolog Editor
# Build scripts and packaging for the Notolog Editor Debian release.
#
# Repository: https://github.com/notolog/notolog-debian
# License: MIT License
#
# SPDX-FileCopyrightText: 2025-2026 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT

"""
Pre-build script for Notolog Debian package.

This script reads the project metadata and generates version.txt for the build.
"""

import os
import tomllib

file_path = os.path.join(os.path.dirname(__file__), "..", "..", "src", "pyproject.toml")

# Load TOML (read-only)
with open(file_path, "rb") as f:
    data = tomllib.load(f)

poetry = data.get("tool", {}).get("poetry", {})

# Generate version.txt from pyproject.toml
version = poetry.get("version")
if version:
    version_txt_path = os.path.join(os.path.dirname(__file__), "..", "version.txt")
    with open(version_txt_path, "w") as f:
        f.write(f"{version}\n")
    print(f"version.txt written with version: {version}")
else:
    print("No version found in pyproject.toml!")
