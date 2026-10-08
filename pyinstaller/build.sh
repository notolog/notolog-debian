#!/usr/bin/env bash
set -Eeuo pipefail

# Debian Package Builder for Notolog Editor
# SPDX-FileCopyrightText: 2025-2026 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT

readonly PYINSTALLER_VERSION="6.22.3"
readonly PIP_VERSION="26.2.2"
readonly POETRY_CORE_VERSION="2.5.0"
readonly BUILD_VERSION="1.6.1"
readonly PIP_LICENSES_VERSION="5.5.5"
readonly PIP_AUDIT_VERSION="2.10.1"
readonly LLAMA_CPP_PYTHON_VERSION="0.3.36"
# Narrow exception for a transitive dependency that the application does not use.
# The source guard below prevents the exception from covering future API use.
readonly DISKCACHE_UNUSED_ADVISORY="PYSEC-2026-2447"
LLAMA_CPU_PROFILE="${LLAMA_CPU_PROFILE:-auto}"
readonly LLAMA_X86_BASE_CMAKE_ARGS="-DGGML_NATIVE=OFF -DGGML_SSE42=OFF -DGGML_AVX=OFF -DGGML_AVX2=OFF -DGGML_BMI2=OFF -DGGML_FMA=OFF"
readonly LLAMA_RUNTIME_CMAKE_ARGS="-DGGML_NATIVE=OFF -DGGML_BACKEND_DL=ON -DGGML_CPU_ALL_VARIANTS=ON -DBUILD_SHARED_LIBS=ON -DCMAKE_INSTALL_BINDIR=llama_cpp/lib"

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYI_DIR="$PROJECT_ROOT/pyinstaller"
SOURCE_DIR="$PROJECT_ROOT/src"
VENV_DIR="$PROJECT_ROOT/venv/notolog"
BUILD_DIR="$PYI_DIR/build"
SCRIPTS_DIR="$PYI_DIR/scripts"
PYTHON_BIN="${PYTHON_BIN:-python3}"
BOOTLOADER_CFLAGS="-O2 -fPIE -fstack-protector-strong -Wformat -Werror=format-security"
LLAMA_BUILD_JOBS="${CMAKE_BUILD_PARALLEL_LEVEL:-}"

if [ -z "$LLAMA_BUILD_JOBS" ]; then
    DETECTED_BUILD_JOBS="$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf '1')"
    case "$DETECTED_BUILD_JOBS" in
        ''|*[!0-9]*|0) DETECTED_BUILD_JOBS=1 ;;
    esac
    if [ "$DETECTED_BUILD_JOBS" -gt 4 ]; then
        LLAMA_BUILD_JOBS=4
    else
        LLAMA_BUILD_JOBS="$DETECTED_BUILD_JOBS"
    fi
fi
case "$LLAMA_BUILD_JOBS" in
    ''|*[!0-9]*|0)
        echo "Error: CMAKE_BUILD_PARALLEL_LEVEL must be a positive integer" >&2
        exit 1
        ;;
esac
readonly LLAMA_BUILD_JOBS

case "$(uname -m)" in
    x86_64|i?86) BOOTLOADER_CFLAGS+=" -fcf-protection=full" ;;
    aarch64|arm64) BOOTLOADER_CFLAGS+=" -mbranch-protection=standard" ;;
esac

if [ ! -f "$SOURCE_DIR/pyproject.toml" ] || [ ! -f "$PROJECT_ROOT/debian/control" ]; then
    echo "Error: incomplete builder checkout under $PROJECT_ROOT" >&2
    exit 1
fi

DEBIAN_SERIES="$(dpkg-parsechangelog -l"$PROJECT_ROOT/debian/changelog" --show-field Distribution)"
TARGET_SERIES="${TARGET_SERIES_OVERRIDE:-$DEBIAN_SERIES}"
TARGET_ARCHITECTURE="$(dpkg-architecture -qDEB_HOST_ARCH)"
case "$TARGET_SERIES" in
    jammy|noble|resolute) ;;
    *) echo "Error: unsupported Ubuntu compatibility baseline $TARGET_SERIES" >&2; exit 1 ;;
esac
case "$TARGET_ARCHITECTURE" in
    amd64|arm64) ;;
    *) echo "Error: unsupported target architecture $TARGET_ARCHITECTURE" >&2; exit 1 ;;
esac

if [ "$LLAMA_CPU_PROFILE" = "auto" ]; then
    case "$TARGET_ARCHITECTURE" in
        amd64) LLAMA_CPU_PROFILE="runtime" ;;
        arm64) LLAMA_CPU_PROFILE="portable" ;;
    esac
fi
readonly LLAMA_CPU_PROFILE

case "$TARGET_ARCHITECTURE:$LLAMA_CPU_PROFILE" in
    amd64:runtime|arm64:runtime)
        LLAMA_CMAKE_ARGS="$LLAMA_RUNTIME_CMAKE_ARGS"
        ;;
    amd64:portable)
        LLAMA_CMAKE_ARGS="$LLAMA_X86_BASE_CMAKE_ARGS -DGGML_F16C=OFF"
        ;;
    amd64:f16c)
        if [ ! -r /proc/cpuinfo ] || ! grep -qw f16c /proc/cpuinfo; then
            echo "Error: the f16c profile requires F16C support on the build host" >&2
            exit 1
        fi
        LLAMA_CMAKE_ARGS="$LLAMA_X86_BASE_CMAKE_ARGS -DGGML_F16C=ON"
        ;;
    arm64:portable)
        LLAMA_CMAKE_ARGS="-DGGML_NATIVE=OFF"
        ;;
    arm64:f16c)
        echo "Error: the f16c profile is only valid for amd64 builds" >&2
        exit 1
        ;;
    *)
        echo "Error: unsupported llama.cpp CPU profile '$LLAMA_CPU_PROFILE' (expected auto, runtime, portable, or f16c)" >&2
        exit 1
        ;;
esac
readonly LLAMA_CMAKE_ARGS

echo "Auditing $TARGET_ARCHITECTURE bundle against the $TARGET_SERIES compatibility baseline..."
echo "Building llama.cpp with the '$LLAMA_CPU_PROFILE' CPU profile..."
echo "Using $LLAMA_BUILD_JOBS parallel job(s) for native compilation..."

"$PYTHON_BIN" "$SCRIPTS_DIR/verify-python.py"
"$PYI_DIR/clean-build.sh"

echo "Creating isolated build environment with $PYTHON_BIN..."
"$PYTHON_BIN" -m venv "$VENV_DIR"
VENV_PYTHON="$VENV_DIR/bin/python"

"$VENV_PYTHON" -m pip install --upgrade "pip==$PIP_VERSION"
"$VENV_PYTHON" -m pip install \
    "poetry-core==$POETRY_CORE_VERSION" \
    "build==$BUILD_VERSION" \
    "pip-licenses==$PIP_LICENSES_VERSION" \
    "pip-audit==$PIP_AUDIT_VERSION"

# Compile a native, hardened bootloader instead of using PyPI's generic binary.
env \
    CFLAGS="$BOOTLOADER_CFLAGS" \
    LDFLAGS="-Wl,-z,relro,-z,now -pie" \
    PYINSTALLER_COMPILE_BOOTLOADER=1 \
    "$VENV_PYTHON" -m pip install --no-cache-dir --no-binary=pyinstaller \
    "pyinstaller==$PYINSTALLER_VERSION"

"$VENV_PYTHON" "$SCRIPTS_DIR/pre-build.py"
APP_VERSION="$(tr -d '\n' < "$PYI_DIR/version.txt")"
DEBIAN_VERSION="$(dpkg-parsechangelog -l"$PROJECT_ROOT/debian/changelog" --show-field Version)"
DEBIAN_UPSTREAM_VERSION="${DEBIAN_VERSION#*:}"
DEBIAN_UPSTREAM_VERSION="${DEBIAN_UPSTREAM_VERSION%%-*}"
if [ "$APP_VERSION" != "$DEBIAN_UPSTREAM_VERSION" ]; then
    echo "Error: application version $APP_VERSION does not match Debian version $DEBIAN_VERSION" >&2
    exit 1
fi

# Use the selected, validated CPU profile without runner-specific optimization.
CMAKE_ARGS="$LLAMA_CMAKE_ARGS" \
    CMAKE_BUILD_PARALLEL_LEVEL="$LLAMA_BUILD_JOBS" \
    "$VENV_PYTHON" -m pip install --no-cache-dir --no-binary=llama-cpp-python \
    --only-binary=sounddevice,cffi,pycparser,PySide6-Essentials,shiboken6 \
    "${SOURCE_DIR}[llama,tts]" \
    "llama-cpp-python==$LLAMA_CPP_PYTHON_VERSION"

RESOLVED_LLAMA_CPP_VERSION="$(
    "$VENV_PYTHON" -c 'import importlib.metadata; print(importlib.metadata.version("llama-cpp-python"))'
)"
if [ "$RESOLVED_LLAMA_CPP_VERSION" != "$LLAMA_CPP_PYTHON_VERSION" ]; then
    echo "Error: expected llama-cpp-python $LLAMA_CPP_PYTHON_VERSION, installed $RESOLVED_LLAMA_CPP_VERSION" >&2
    exit 1
fi

LLAMA_LIBRARY_DIR="$VENV_DIR/lib/python$("$VENV_PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')/site-packages/llama_cpp/lib"
if [ "$LLAMA_CPU_PROFILE" = "runtime" ]; then
    case "$TARGET_ARCHITECTURE" in
        amd64) REQUIRED_CPU_BACKEND="libggml-cpu-x64.so" ;;
        arm64) REQUIRED_CPU_BACKEND="libggml-cpu-armv8.0_1.so" ;;
    esac
    if [ ! -f "$LLAMA_LIBRARY_DIR/$REQUIRED_CPU_BACKEND" ]; then
        echo "Error: llama.cpp runtime CPU backends were not installed" >&2
        exit 1
    fi
fi
"$VENV_PYTHON" -m pip check
"$VENV_PYTHON" "$SCRIPTS_DIR/verify-modules.py"

# The advisory exception is valid only while Notolog does not use diskcache or
# llama-cpp-python's pickle-based LlamaDiskCache implementation.
if grep -R -n --include='*.py' -E \
        '(^|[^[:alnum:]_])(diskcache|LlamaDiskCache)([^[:alnum:]_]|$)' \
        "$SOURCE_DIR/notolog"; then
    echo "Error: diskcache use invalidates security advisory exception $DISKCACHE_UNUSED_ADVISORY" >&2
    exit 1
fi

mkdir -p "$BUILD_DIR/reports"
"$VENV_PYTHON" --version > "$BUILD_DIR/python_version.txt"
"$VENV_PYTHON" -m PyInstaller --version > "$BUILD_DIR/pyinstaller_version.txt"

printf '%s\n' "$APP_VERSION" > "$BUILD_DIR/app_version.txt"
printf '%s\n' "$LLAMA_CPU_PROFILE" > "$BUILD_DIR/llama_cpu_profile.txt"
printf '%s\n' "$LLAMA_CMAKE_ARGS" > "$BUILD_DIR/llama_cmake_args.txt"
"$VENV_PYTHON" -m pip list --format=freeze > "$BUILD_DIR/reports/build-requirements.txt"
cp "$SOURCE_DIR/pyproject.toml" "$BUILD_DIR/pyproject.toml"
"$VENV_DIR/bin/pip-licenses" --format=markdown --with-license-file --with-authors \
    > "$BUILD_DIR/reports/pip-licenses.md"
"$VENV_DIR/bin/pip-licenses" --format=markdown --with-authors \
    > "$BUILD_DIR/reports/dependency-licenses.md"
# All other dependency advisories fail the build.
"$VENV_DIR/bin/pip-audit" \
    --ignore-vuln "$DISKCACHE_UNUSED_ADVISORY" \
    --format cyclonedx-json \
    --output "$BUILD_DIR/reports/notolog-${APP_VERSION}.cdx.json"

cd "$PYI_DIR"
NOTOLOG_LLAMA_CPU_PROFILE="$LLAMA_CPU_PROFILE" \
    "$VENV_PYTHON" -m PyInstaller --clean --noconfirm notolog-onefile.spec

"$VENV_PYTHON" "$SCRIPTS_DIR/audit-bundle.py" \
    "$PYI_DIR/dist/notolog" \
    --target-series "$TARGET_SERIES" \
    --expected-architecture "$TARGET_ARCHITECTURE" \
    --forbidden-build-root "$PROJECT_ROOT" \
    --copyright "$PROJECT_ROOT/debian/copyright" \
    --glibc-output "$PYI_DIR/embedded-glibc-version.txt"

env \
    NOTOLOG_VERIFY_FROZEN_MODULES=1 \
    QT_QPA_PLATFORM=offscreen \
    "$PYI_DIR/dist/notolog"

"$VENV_PYTHON" "$SCRIPTS_DIR/verify-speech-worker.py" "$PYI_DIR/dist/notolog"
"$VENV_PYTHON" "$SCRIPTS_DIR/verify-version.py" "$PYI_DIR/dist/notolog" "$APP_VERSION"

# A GUI smoke test must remain alive after constructing the main window.
SMOKE_CONFIG_DIR="$BUILD_DIR/smoke-config"
SMOKE_DATA_DIR="$BUILD_DIR/smoke-data"
mkdir -p "$SMOKE_CONFIG_DIR" "$SMOKE_DATA_DIR"
smoke_status=0
timeout --signal=TERM 15s env \
    XDG_CONFIG_HOME="$SMOKE_CONFIG_DIR" \
    XDG_DATA_HOME="$SMOKE_DATA_DIR" \
    QT_QPA_PLATFORM=offscreen \
    "$PYI_DIR/dist/notolog" || smoke_status=$?
if [ "$smoke_status" -ne 124 ]; then
    echo "Error: GUI smoke test exited with status $smoke_status" >&2
    exit 1
fi
if [ ! -f "$SMOKE_CONFIG_DIR/Notolog/notolog_editor_bin.conf" ]; then
    echo "Error: bundled app did not create its package-specific settings file" >&2
    exit 1
fi
if [ -e "$SMOKE_CONFIG_DIR/Notolog/notolog_editor.conf" ]; then
    echo "Error: bundled app wrote to the development settings file" >&2
    exit 1
fi

HARDENING_OPTIONS=()
CONTROL_FLOW_PROPERTY=""
case "$TARGET_ARCHITECTURE" in
    amd64)
        # Branch protection is ARM-specific and older Ubuntu hardening-check
        # releases neither test it nor accept the opt-out flag.
        if grep -q -- '--nobranchprotection' < <(hardening-check --help 2>&1); then
            HARDENING_OPTIONS+=(--nobranchprotection)
        fi
        CONTROL_FLOW_PROPERTY="x86 feature: IBT, SHSTK"
        ;;
    arm64)
        # hardening-check's control-flow test is x86-specific. The bootloader
        # is compiled with ARM branch protection above, but a mixed-link
        # executable cannot safely claim BTI unless every input supports it.
        if grep -q -- '--nocfprotection' < <(hardening-check --help 2>&1); then
            HARDENING_OPTIONS+=(--nocfprotection)
        fi
        ;;
esac

check_hardening() {
    local binary_path="$1"
    hardening-check "${HARDENING_OPTIONS[@]}" "$binary_path"
    if [ -n "$CONTROL_FLOW_PROPERTY" ] && \
            ! grep -Fq -- "$CONTROL_FLOW_PROPERTY" < <(LC_ALL=C readelf --notes "$binary_path"); then
        echo "Error: missing architecture control-flow property: $CONTROL_FLOW_PROPERTY" >&2
        return 1
    fi
}

check_hardening "$PYI_DIR/dist/notolog"

if [ "${SKIP_DEB_BUILD:-false}" = "true" ]; then
    echo "PyInstaller binary ready at $PYI_DIR/dist/notolog"
else
    cd "$PROJECT_ROOT"
    dpkg-buildpackage -us -uc -b

    PACKAGE_PATH="$PROJECT_ROOT/../notolog_${DEBIAN_VERSION#*:}_${TARGET_ARCHITECTURE}.deb"
    PACKAGE_ROOT="$BUILD_DIR/package-root"
    PACKAGE_CONFIG_DIR="$BUILD_DIR/package-smoke-config"
    PACKAGE_DATA_DIR="$BUILD_DIR/package-smoke-data"
    mkdir -p "$PACKAGE_ROOT" "$PACKAGE_CONFIG_DIR" "$PACKAGE_DATA_DIR"
    dpkg-deb --extract "$PACKAGE_PATH" "$PACKAGE_ROOT"
    PACKAGED_BINARY="$PACKAGE_ROOT/usr/bin/notolog"

    "$VENV_PYTHON" "$SCRIPTS_DIR/audit-bundle.py" \
        "$PACKAGED_BINARY" \
        --target-series "$TARGET_SERIES" \
        --expected-architecture "$TARGET_ARCHITECTURE" \
        --forbidden-build-root "$PROJECT_ROOT" \
        --copyright "$PROJECT_ROOT/debian/copyright" \
        --glibc-output "$PYI_DIR/embedded-glibc-version.txt"
    check_hardening "$PACKAGED_BINARY"
    "$VENV_PYTHON" "$SCRIPTS_DIR/verify-speech-worker.py" "$PACKAGED_BINARY"
    "$VENV_PYTHON" "$SCRIPTS_DIR/verify-version.py" "$PACKAGED_BINARY" "$APP_VERSION"

    env \
        NOTOLOG_VERIFY_FROZEN_MODULES=1 \
        QT_QPA_PLATFORM=offscreen \
        "$PACKAGED_BINARY"

    package_smoke_status=0
    timeout --signal=TERM 15s env \
        XDG_CONFIG_HOME="$PACKAGE_CONFIG_DIR" \
        XDG_DATA_HOME="$PACKAGE_DATA_DIR" \
        QT_QPA_PLATFORM=offscreen \
        "$PACKAGED_BINARY" || package_smoke_status=$?
    if [ "$package_smoke_status" -ne 124 ]; then
        echo "Error: packaged GUI smoke test exited with status $package_smoke_status" >&2
        exit 1
    fi
    if [ ! -f "$PACKAGE_CONFIG_DIR/Notolog/notolog_editor_bin.conf" ]; then
        echo "Error: packaged app did not create its package-specific settings file" >&2
        exit 1
    fi
    if [ -e "$PACKAGE_CONFIG_DIR/Notolog/notolog_editor.conf" ]; then
        echo "Error: packaged app wrote to the development settings file" >&2
        exit 1
    fi
fi
