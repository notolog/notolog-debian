#!/usr/bin/env bash
set -Eeuo pipefail

# Debian Package Builder for Notolog Editor
# SPDX-FileCopyrightText: 2025-2026 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -f "$PROJECT_ROOT/debian/control" ] || [ ! -d "$PROJECT_ROOT/pyinstaller" ]; then
    echo "Error: refusing to clean an unexpected project root: $PROJECT_ROOT" >&2
    exit 1
fi

rm -rf -- \
    "$PROJECT_ROOT/debian/.debhelper" \
    "$PROJECT_ROOT/debian/notolog" \
    "$PROJECT_ROOT/pyinstaller/build" \
    "$PROJECT_ROOT/pyinstaller/dist" \
    "$PROJECT_ROOT/pyinstaller/pyi-source" \
    "$PROJECT_ROOT/venv"

rm -f -- \
    "$PROJECT_ROOT/debian/debhelper-build-stamp" \
    "$PROJECT_ROOT/debian/files" \
    "$PROJECT_ROOT/debian/notolog.debhelper.log" \
    "$PROJECT_ROOT/debian/notolog.substvars" \
    "$PROJECT_ROOT/pyinstaller/embedded-glibc-version.txt" \
    "$PROJECT_ROOT/pyinstaller/package_config.toml" \
    "$PROJECT_ROOT/pyinstaller/version.txt"

echo "Build artifacts removed."
