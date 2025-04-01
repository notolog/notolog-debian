#!/bin/bash

# Debian Package Builder for Notolog Editor
# Build scripts and packaging for the Notolog Editor Debian release.
#
# Repository: https://github.com/notolog/notolog-debian
# License: MIT License
#
# SPDX-FileCopyrightText: 2025 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT

# Check if the script is run as root or use sudo
SUDO=""
if [ "$(whoami)" != "root" ]; then
    SUDO=sudo
fi

# Clean apt cache
echo "Cleaning APT cache..."
$SUDO apt-get clean || {
    echo "Error: Failed to clean APT cache."
    exit 1
}

# Resolve project root
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "Project root: $PROJECT_ROOT"

# Clean cached Python files
echo "Removing Python cache files..."
$SUDO find "$PROJECT_ROOT" -name "*.pyc" -delete
$SUDO find "$PROJECT_ROOT" -name "__pycache__" -delete

# Clean previous build
echo "Cleaning dpkg build artifacts..."
cd "$PROJECT_ROOT"
$SUDO dpkg-buildpackage -T clean || {
    echo "Error: Failed to clean build artifacts."
    exit 1
}

# PyInstaller paths
PYI_DIR="$PROJECT_ROOT/pyinstaller"
PYI_SOURCE_DIR="$PYI_DIR/pyi-source"

# Virtual environment
VENV_DIR="$PROJECT_ROOT/venv"

# Generated files
BUILD_DIR="$PYI_DIR/build"
DIST_DIR="$PYI_DIR/dist"
PACKAGE_CONFIG_FILE="$PYI_DIR/package_config.toml"
VERSION_FILE="$PYI_DIR/version.txt"

# Move to the PyInstaller dir
cd "$PYI_DIR"

# Remove build and dist directories
for DIR in "$BUILD_DIR" "$DIST_DIR"; do
    if [ -d "$DIR" ]; then
        echo "Removing $DIR..."
        $SUDO rm -rf "$DIR" || {
            echo "Failed to remove $DIR"
            exit 1
        }
        echo "$DIR removed."
    fi
done

# Delete virtual environment
if [ -d "$VENV_DIR" ]; then
    echo "Deleting virtual environment: $VENV_DIR"
    rm -rf "$VENV_DIR"
else
    echo "Virtual environment not found at $VENV_DIR"
fi

# Delete PyInstaller source
if [ -d "$PYI_SOURCE_DIR" ]; then
    echo "Deleting PyInstaller source: $PYI_SOURCE_DIR"
    rm -rf "$PYI_SOURCE_DIR"
else
    echo "PyInstaller source not found at $PYI_SOURCE_DIR"
fi

# Delete generated package config file
if [ -f "$PACKAGE_CONFIG_FILE" ]; then
    echo "Deleting: $PACKAGE_CONFIG_FILE"
    rm "$PACKAGE_CONFIG_FILE"
else
    echo "Package config file not found."
fi

# Delete generated version file
if [ -f "$VERSION_FILE" ]; then
    echo "Deleting: $VERSION_FILE"
    rm "$VERSION_FILE"
else
    echo "Version file not found."
fi

# Revert auto-generated license information
#if git checkout $PROJECT_ROOT/debian/copyright; then
#    echo "Reverted auto-generated lines in $PROJECT_ROOT/debian/copyright file."
#else
#    echo "Error occurred while reverting changes in $PROJECT_ROOT/debian/copyright file."
#    exit 1
#fi

echo "Clean-up complete."

exit 0
