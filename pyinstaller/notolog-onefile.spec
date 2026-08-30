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
# Invoke through build.sh so dependencies, native hardening, auditing, and packaging
# use the same release process in local and CI builds.

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

# Paths
pyinstaller_path = os.path.dirname(sys.argv[0])
app_root = os.path.abspath(os.path.join(pyinstaller_path, '..', 'src'))
version_file_path = os.path.abspath(os.path.join(pyinstaller_path, 'version.txt'))
icon_file = os.path.join(app_root, 'notolog/assets/notolog-logo.png')

# Data and binary collection. Python modules belong in PyInstaller's PYZ
# archive; only runtime assets should be copied as plain files.
datas = collect_data_files('notolog')
# Lexemes are loaded from their source files at runtime rather than imported.
datas += collect_data_files(
    'notolog',
    include_py_files=True,
    includes=['lexemes/*/*.py'],
)
# AI modules are imported from the PYZ archive, but runtime discovery and
# translated settings load these source paths from disk.
datas += collect_data_files(
    'notolog',
    include_py_files=True,
    includes=[
        'modules/*/module_core.py',
        'modules/*/lexemes/*/*.py',
    ],
)
datas.append((os.path.join(app_root, 'README.md'), '.'))
binaries = []
hiddenimports = collect_submodules('notolog')

# Include version.txt in the PyInstaller bundle (placed at app root)
datas.append((version_file_path, '.'))

# Collect extra data and submodules
datas += collect_data_files('emoji')
datas += collect_data_files('onnxruntime', excludes=['datasets/**', 'tools/**'])
datas += collect_data_files('onnxruntime_genai')
datas += collect_data_files('jinja2')
datas += collect_data_files('diskcache')
# Collect llama.cpp Python bindings and native CPU backends for this architecture.
datas += collect_data_files(
    'llama_cpp',
    excludes=['server/**'],
)
llama_binaries = collect_dynamic_libs('llama_cpp')
if os.environ.get('NOTOLOG_LLAMA_CPU_PROFILE') == 'runtime':
    backend_names = {Path(source).name for source, _ in llama_binaries}
    if not any(name.startswith('libggml-cpu-') for name in backend_names):
        raise RuntimeError('llama.cpp runtime CPU backends were not collected')
binaries += llama_binaries
hiddenimports += collect_submodules(
    'llama_cpp',
    filter=lambda name: not name.startswith('llama_cpp.server'),
)

# Tomli's optional mypyc runtime is a generated top-level extension. Pure
# Python and architectures without that wheel simply have no matching file.
tomli_spec = __import__('tomli').__spec__
if tomli_spec and tomli_spec.origin:
    site_packages = Path(tomli_spec.origin).parent.parent
    binaries += [(str(path), '.') for path in site_packages.glob('*__mypyc*.so')]

hiddenimports += collect_submodules(
    'onnxruntime_genai',
    filter=lambda name: '.models.builders' not in name,
)
hiddenimports += collect_submodules('jinja2')
hiddenimports += collect_submodules('diskcache')
hiddenimports += collect_submodules('uuid')

# This auto-generated config file tells the app it's running from a bundled binary
package_config_file_path = os.path.join(pyinstaller_path, "package_config.toml")
with open(package_config_file_path, "w") as f:
    f.write('# This file is auto-generated.\n[package]\ntype = "bin"')
datas.append((package_config_file_path, '.'))

# Exclude test modules if a dependency imports them conditionally.
excludes = [
    'tests',
    'test',
    'pytest',
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='notolog',
    debug=False,
    bootloader_ignore_signals=False,
    # Some wheel-provided shared libraries are not safe to strip. Debian still
    # strips the outer executable during packaging.
    strip=False,
    upx=False,
    upx_exclude=[],  # List of binaries to exclude from UPX compression
    console=True,  # Set to False for GUI app (hides console window on Windows)
    disable_windowed_traceback=False,
    argv_emulation=False,  # macOS only — emulate argv[0] behavior
    target_arch=None,
    codesign_identity=None,  # macOS code signing (None disables it)
    entitlements_file=None,  # macOS sandbox entitlements (optional)
    runtime_tmpdir=None,
    # Used only on Windows (.ico), ignored on Linux/macOS
    icon=icon_file if sys.platform == 'win32' else None,
    version=version_file_path,  # optional
)
