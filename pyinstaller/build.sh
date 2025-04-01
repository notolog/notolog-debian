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

# Application name
APP_NAME="Notolog"

# Check if the app is installed
if command -v notolog &>/dev/null; then
    echo "App is installed: $APP_NAME"

    # Stop running instances of the app
    echo "Stopping any running instances of $APP_NAME..."
    $SUDO pkill -f "^.*notolog" || echo "No running process found for $APP_NAME."

    # Uninstall the app
    echo "Uninstalling $APP_NAME..."
    $SUDO apt-get remove --purge -y notolog || {
        echo "Error: Failed to remove $APP_NAME."
    }
else
    echo "App is not installed: $APP_NAME"
fi

# Resolve project root
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "Project root: $PROJECT_ROOT"

# PyInstaller paths
PYI_DIR="$PROJECT_ROOT/pyinstaller"
PYI_SOURCE_DIR="$PYI_DIR/pyi-source"

# App source code
SOURCE_DIR="$PROJECT_ROOT/src"

# Virtual environment
VENV_DIR="$PROJECT_ROOT/venv"

# Generated files
BUILD_DIR="$PYI_DIR/build"
DIST_DIR="$PYI_DIR/dist"
PACKAGE_CONFIG_FILE="$PYI_DIR/package_config.toml"
VERSION_FILE="$PYI_DIR/version.txt"

# Path to supporting utility scripts
SCRIPTS_DIR="$PYI_DIR/scripts"

# Run clean-up script if available
if [ -f "$PYI_DIR/clean-build.sh" ]; then
    "$PYI_DIR/clean-build.sh"
else
    echo "clean-build.sh not found, skipping clean step."
fi

# Move to the PyInstaller dir
cd "$PYI_DIR"

# Create pyinstaller virtual environment
echo "Creating Python environment..."

python3 -m venv "$VENV_DIR/notolog"

# Activate the pyinstaller environment
echo "Activating Python environment..."

source "$VENV_DIR/notolog/bin/activate" || {
    echo "Error: Failed to activate Python environment."
    exit 1
}

# Upgrade pip
if pip install pip --upgrade; then
    echo "Upgraded pip version."
else
    echo "Error occurred when upgrading pip package."
    exit 1
fi

# Install build tools
if pip install poetry-core build tomli tomli_w; then
    echo "Installed build tools."
else
    echo "Error occurred when installing build packages."
    exit 1
fi

# Run pre-build script
if python3 "$SCRIPTS_DIR/pre-build.py"; then
    echo "Pre-build script completed."
else
    echo "Error occurred while running the pre-build script."
    exit 1
fi

# Install the app with all dependencies
if pip install "$SOURCE_DIR"; then
    echo "Installed the app."
else
    echo "Error occurred when installing the app package."
    exit 1
fi

# Check llama-cpp installation
if python3 -c "from llama_cpp import Llama; print('Llama OK')" >/dev/null 2>&1; then
    echo "Llama load successful."
else
    echo "Llama load failed."
    exit 1
fi

# Remove the installed app while retaining its dependencies
if pip uninstall -y notolog; then
    echo "The Notolog package was removed."
else
    echo "An error occurred while removing the Notolog package."
    exit 1
fi

# Save build metadata
if mkdir -p "$BUILD_DIR"; then
    echo "Created build directory."
else
    echo "Error occurred while creating build directory."
    exit 1
fi

# Save Python version
if python3 --version > $BUILD_DIR/python_version.txt; then
    echo "Saved Python version."
else
    echo "Error occurred while saving Python version."
    exit 1
fi

# Extract and save app version
if APP_VERSION=$(grep '^version *= *"' $SOURCE_DIR/pyproject.toml | cut -d '"' -f2); then
    echo "$APP_VERSION" > $BUILD_DIR/app_version.txt
    echo "Saved app version: $APP_VERSION"
else
    echo "Error occurred while extracting app version."
    exit 1
fi

# Save pip requirements
if pip freeze > "$BUILD_DIR/build_requirements_ver${APP_VERSION}.txt"; then
    echo "Saved pip freeze output."
else
    echo "Error occurred while saving pip requirements."
    exit 1
fi

# Copy pyproject.toml
if cp "$SOURCE_DIR/pyproject.toml" "$BUILD_DIR/pyproject.toml"; then
    echo "Copied pyproject.toml to build directory."
else
    echo "Error occurred while copying pyproject.toml."
    exit 1
fi

# License tools
if pip install pip-licenses; then
    echo "pip-licenses installed."
else
    echo "An error occurred while installing pip-licenses."
    exit 1
fi

# Generate pip license report
if mkdir -p build/reports \
    && pip-licenses --format=markdown --with-license-file --with-authors > build/reports/pip-licenses.md; then
    echo "pip license report generated."
else
    echo "An error occurred while generating the pip license report."
    exit 1
fi

# Run license generation script
#if python3 "$SCRIPTS_DIR/license-gen.py"; then
#    echo "License generation script completed successfully."
#else
#    echo "An error occurred while running the license generation script."
#    exit 1
#fi

# Remove the installed app's build dependencies
if pip uninstall -y poetry-core build pip-licenses; then
    echo "Build-related pip packages were removed."
else
    echo "An error occurred while removing build-related pip packages."
    exit 1
fi

# Clean cached Python files (in packages)
echo "Removing Python cache files..."
$SUDO find "$PROJECT_ROOT" -name "*.pyc" -delete
$SUDO find "$PROJECT_ROOT" -name "__pycache__" -delete

# Ensure required packages are installed before proceeding
# sudo apt-get install build-essential zlib1g-dev gcc clang

# Clone PyInstaller into dedicated directory
echo "Cloning PyInstaller into $PYI_SOURCE_DIR..."
if git clone https://github.com/pyinstaller/pyinstaller.git "$PYI_SOURCE_DIR"; then
    echo "PyInstaller cloned."
else
    echo "Failed to clone PyInstaller."
    exit 1
fi

# Go to the bootloader build directory
cd "$PYI_SOURCE_DIR/bootloader" || { echo "Failed to enter bootloader directory"; exit 1; }

# Clean up old builds
echo "Cleaning previous builds..."
rm -rf build dist

# Enable PIE hardening
echo "Setting hardening flags..."
export CFLAGS="-fPIE"
export LDFLAGS="-pie"

# Build the bootloader
echo " Building PyInstaller bootloader..."
python3 ./waf all

# Install PyInstaller from source root
cd "$PYI_SOURCE_DIR" || { echo "Failed to enter PyInstaller source root"; exit 1; }
echo "Installing PyInstaller from source..."
if pip install .; then
    echo "PyInstaller installed with PIE hardening."
else
    echo "PyInstaller installation failed."
    exit 1
fi

# Return to main PyInstaller directory
cd "$PYI_DIR" && echo "Returned to: $(pwd)"

# Build one-file installer
if pyinstaller --clean --noconfirm notolog-onefile.spec && deactivate; then
    echo "One-file installer was built."
else
    echo "Error occurred when building installer."
    exit 1
fi

# Build deb package
echo "Building deb package..."
# Move to the project root
cd "$PROJECT_ROOT"
if sudo dpkg-buildpackage -rfakeroot -us -uc -b; then
    echo "Deb package was built successfully."
else
    echo "Error occurred when building deb package."
    exit 1
fi

exit 0
