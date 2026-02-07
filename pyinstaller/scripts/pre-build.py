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

This script patches the pyproject.toml to ensure compatibility with PyInstaller:
- Pins tomli to version 2.0.1 to avoid import errors in PyInstaller bundles.
- Generates version.txt for the build process.
"""

import os
import tomli
import tomli_w

file_path = os.path.join(os.path.dirname(__file__), "..", "..", "src", "pyproject.toml")

# Load TOML (read-only)
with open(file_path, "rb") as f:
    data = tomli.load(f)

# Safely navigate and update nested structure
tool = data.setdefault("tool", {})
poetry = tool.setdefault("poetry", {})
dependencies = poetry.setdefault("dependencies", {})

# Patch tomli to exact version 2.0.1 to avoid mypyc-compiled 2.4.0+
# which causes "ModuleNotFoundError: No module named '...__mypyc'" in PyInstaller
TOMLI_PINNED_VERSION = "=2.0.1"
if "tomli" in dependencies:
    original_version = dependencies["tomli"]
    if original_version != TOMLI_PINNED_VERSION:
        dependencies["tomli"] = TOMLI_PINNED_VERSION
        print(f"Patched tomli: {original_version} -> {TOMLI_PINNED_VERSION}")
    else:
        print(f"tomli already pinned to {TOMLI_PINNED_VERSION}")
else:
    dependencies["tomli"] = TOMLI_PINNED_VERSION
    print(f"Added tomli {TOMLI_PINNED_VERSION}")

# Save TOML back
with open(file_path, "wb") as f:
    tomli_w.dump(data, f)

# Generate version.txt from pyproject.toml
version = poetry.get("version")
if version:
    version_txt_path = os.path.join(os.path.dirname(__file__), "..", "version.txt")
    with open(version_txt_path, "w") as f:
        f.write(f"{version}\n")
    print(f"version.txt written with version: {version}")
else:
    print("No version found in pyproject.toml!")
