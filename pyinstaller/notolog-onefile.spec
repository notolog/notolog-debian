# -*- mode: python ; coding: utf-8 -*-
# notolog-onefile.spec
#
# Debian PyInstaller build script for Notolog Editor (onefile mode).
#
# Repository: https://github.com/notolog/notolog-debian
# License: MIT License
#
# SPDX-FileCopyrightText: 2025-2026 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT
#
# 🛠 Build Commands:
#
# 1. Using the .spec file:
#    pyinstaller --clean --noconfirm notolog-onefile.spec
#
# 2. Equivalent CLI example:
#    pyinstaller --onefile --noconfirm --name=notolog --collect-all=notolog notolog/app.py \
#        --add-data="notolog:notolog" \
#        --add-data="docs/*:docs" \
#        --add-data="CHANGELOG.md:." \
#        --add-data="CODE_OF_CONDUCT.md:." \
#        --add-data="CONTRIBUTING.md:." \
#        --add-data="LICENSE:." \
#        --add-data="README.md:." \
#        --add-data="SECURITY.md:." \
#        --add-data="ThirdPartyNotices.md:." \
#        --exclude-module="__pycache__" --exclude-module="*.pyc" \
#        --add-data="../envs/notolog-new/lib/python3.11/site-packages/emoji:emoji"
#
# 3. Clean-up tip:
#    find . -name "*.pyc" -delete && find . -name "__pycache__" -delete
#
# Use 'app_root' if running this script from within the PyInstaller directory.

import os
import sys
import sysconfig
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# Paths
site_packages_path = sysconfig.get_path('purelib')
pyinstaller_path = os.path.dirname(sys.argv[0])
app_root = os.path.abspath(os.path.join(pyinstaller_path, '..', 'src'))
version_file_path = os.path.abspath(os.path.join(pyinstaller_path, 'version.txt'))
icon_file = os.path.join(app_root, 'notolog/assets/notolog-logo.png')
runtime_tmpdir = '/usr/lib/notolog/runtime'

# Data and binary collection
datas = [
    (os.path.join(app_root, 'docs', '*'), 'docs'),
    (os.path.join(app_root, 'notolog'), 'notolog'),
    (os.path.join(app_root, 'CHANGELOG.md'), '.'),
    (os.path.join(app_root, 'CODE_OF_CONDUCT.md'), '.'),
    (os.path.join(app_root, 'CONTRIBUTING.md'), '.'),
    (os.path.join(app_root, 'LICENSE'), '.'),
    (os.path.join(app_root, 'README.md'), '.'),
    (os.path.join(app_root, 'SECURITY.md'), '.'),
    (os.path.join(app_root, 'ThirdPartyNotices.md'), '.'),
]
binaries = []
hiddenimports = []

# Include debian/copyright and LICENSES too for clarity
datas.append((os.path.join(app_root, '..', 'debian', 'copyright'), 'debian'))
datas.append((os.path.join(app_root, '..', 'debian', 'LICENSES', '*'), 'debian/LICENSES'))

# Include version.txt in the PyInstaller bundle (placed at app root)
datas.append((version_file_path, '.'))

# Collect everything from notolog
tmp_ret = collect_all('notolog')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# Collect extra data and submodules
datas += collect_data_files('emoji')
datas += collect_data_files('onnxruntime')
datas += collect_data_files('onnxruntime_genai')
datas += collect_data_files('jinja2')
datas += collect_data_files('diskcache')
# Use site-packages path to locate non-standard llama_cpp package
datas.append((os.path.join(site_packages_path, 'llama_cpp'), 'llama_cpp/'))

hiddenimports += collect_submodules('numpy')
hiddenimports += collect_submodules('onnxruntime_genai')
hiddenimports += collect_submodules('jinja2')
hiddenimports += collect_submodules('diskcache')
hiddenimports += collect_submodules('uuid')

# This auto-generated config file tells the app it's running from a bundled binary
package_config_file_path = os.path.join(pyinstaller_path, "package_config.toml")
with open(package_config_file_path, "w") as f:
    f.write('# This file is auto-generated.\n[package]\ntype = "bin"')
datas.append((package_config_file_path, '.'))

# Exclude common temporary or compiled Python files
# These patterns exclude bytecode and cache from the final binary
excludes = [
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '.pytest_cache',
    '.mypy_cache',
    '.tox',
    'tests',
    'test',
    '*_test',
    '*_tests',
]

# Build Phases

a = Analysis(
    [os.path.join(app_root, 'notolog', 'app.py')],
    pathex=[app_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    # Path to custom PyInstaller hooks
    hookspath=[os.path.join(pyinstaller_path, 'hooks')],
    # Runtime hook(s) executed before app starts
    runtime_hooks=[os.path.join(pyinstaller_path, 'runtime_hooks', 'init.py')],
    excludes=excludes,
    noarchive=False,
    optimize=1,  # Bytecode optimization level (0: none, 1: .pyo-style)
    strip=False,  # Do not strip symbols during analysis phase
)

# Create the PYZ (Python Bytecode) archive
pyz = PYZ(a.pure)

# Exclude known system libraries from being bundled (present in Debian/Ubuntu)
system_lib_prefixes = (
    'libX', 'libcairo', 'libgdk', 'libgtk', 'libatk', 'libz', 'libstdc++', 'libgcc', 'libglib', 'libssl',
    'libsqlite', 'liblzma', 'libbz2', 'libpng', 'libfreetype', 'libxcb', 'libpango', 'libXrender',
    'libexpat', 'libffi', 'libsystemd', 'libcom_err', 'libcrypto', 'libmount', 'libcap', 'libgomp',
    'libreadline', 'libatspi', 'libblkid', 'libbrotlicommon', 'libbrotlidec', 'libbsd', 'libdatrie',
    'libdbus', 'libepoxy', 'libfontconfig', 'libfribidi', 'libgcrypt', 'libgio', 'libgmodule', 'libgobject',
    'libgpg', 'libgraphite2', 'libgssapi', 'libgthread', 'libharfbuzz', 'libjpeg', 'libk5crypto',
    'libkeyutils', 'libkrb5', 'liblz4', 'libmd', 'libpcre2', 'libpixman', 'libpng16', 'libselinux', 'libsqlite3',
    'libsystemd', 'libthai', 'libtinfo', 'libxkbcommon', 'libuuid',
)

# Exclude system-provided libraries from the PyInstaller build
a.binaries = TOC([
    b for b in a.binaries
    if not any(os.path.basename(b[0]).startswith(pfx) for pfx in system_lib_prefixes)
])

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='notolog',
    debug=False,
    bootloader_ignore_signals=False,
    # Strip symbols from executable (useful for release builds)
    strip=True,
    upx=True,  # Compress the binary using UPX if available
    upx_exclude=[],  # List of binaries to exclude from UPX compression
    console=True,  # Set to False for GUI app (hides console window on Windows)
    disable_windowed_traceback=False,
    argv_emulation=False,  # macOS only — emulate argv[0] behavior
    target_arch='x86_64',  # Optional unless cross-compiling
    codesign_identity=None,  # macOS code signing (None disables it)
    entitlements_file=None,  # macOS sandbox entitlements (optional)
    runtime_tmpdir=runtime_tmpdir,  # Runtime unpack directory
    # Used only on Windows (.ico), ignored on Linux/macOS
    icon=icon_file if sys.platform == 'win32' else None,
    version=version_file_path,  # optional
)
