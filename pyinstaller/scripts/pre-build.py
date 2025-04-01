# Debian Package Builder for Notolog Editor
# Build scripts and packaging for the Notolog Editor Debian release.
#
# Repository: https://github.com/notolog/notolog-debian
# License: MIT License
#
# SPDX-FileCopyrightText: 2025 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT

import os
import tomli
import tomli_w

file_path = os.path.join(os.path.dirname(__file__), "..", "..", "src", "pyproject.toml")
dependency_key = "tomli"
# Modify the package
version_constraint = "^2.0.1"
replacement = "^2.0.1,<=2.0.1"
# Add a new package
new_key = "llama-cpp-python"
new_value = "^0.3.8"

# Load TOML (read-only)
with open(file_path, "rb") as f:
    data = tomli.load(f)

# Safely navigate and update nested structure
tool = data.setdefault("tool", {})
poetry = tool.setdefault("poetry", {})
dependencies = poetry.setdefault("dependencies", {})

# Update version constraint
if dependency_key in dependencies and dependencies[dependency_key] == version_constraint:
    dependencies[dependency_key] = replacement

# Add a new dependency
dependencies[new_key] = new_value

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
