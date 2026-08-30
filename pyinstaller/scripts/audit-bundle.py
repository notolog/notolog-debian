#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025-2026 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT

"""Fail a release build when its PyInstaller archive is unsafe or incompatible."""

from __future__ import annotations

import argparse
import importlib.metadata
import re
import shutil
import struct
import subprocess
import tempfile
import tomllib
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader

SERIES_GLIBC = {
    "jammy": (2, 35),
    "noble": (2, 39),
    "resolute": (2, 43),
}

ELF_MACHINES = {
    "amd64": 62,
    "arm64": 183,
}

FORBIDDEN_MEMBERS = (
    re.compile(r"(^|/)__pycache__(/|$)"),
    re.compile(r"\.(pyc|pyo)$"),
    re.compile(r"(^|/)direct_url\.json$"),
    re.compile(r"(^|/)(\.git|\.github|\.idea|\.vscode)(/|$)"),
    re.compile(r"^docs/"),
    re.compile(r"^onnxruntime/(datasets|tools)/"),
)

PYTHON_SOURCE = re.compile(r"\.py$")
RUNTIME_PYTHON_SOURCE = re.compile(
    r"^notolog/(?:lexemes/[a-z]{2}/[^/]+|"
    r"modules/[^/]+/(?:module_core|lexemes/[a-z]{2}/[^/]+))\.py$"
)
REQUIRED_MEMBERS = {
    "README.md",
    "package_config.toml",
    "notolog/lexemes/en/common.py",
    "notolog/lexemes/en/main_menu.py",
    "notolog/modules/default/module_core.py",
    "notolog/modules/llama_cpp/module_core.py",
    "notolog/modules/llama_cpp/lexemes/en/common.py",
    "notolog/modules/llama_cpp/lexemes/en/settings_dialog.py",
    "notolog/modules/ondevice_llm/module_core.py",
    "notolog/modules/ondevice_llm/lexemes/en/common.py",
    "notolog/modules/ondevice_llm/lexemes/en/settings_dialog.py",
    "notolog/modules/openai_api/module_core.py",
    "notolog/modules/openai_api/lexemes/en/common.py",
    "notolog/modules/openai_api/lexemes/en/settings_dialog.py",
}
REQUIRED_PYZ_MODULES = {
    "notolog.modules.default.module_core",
    "notolog.modules.llama_cpp.module_core",
    "notolog.modules.ondevice_llm.module_core",
    "notolog.modules.openai_api.module_core",
}

SENSITIVE_CONTENT = {
    "private key": re.compile(
        rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
    ),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9_]{20,}"),
    "developer path": re.compile(
        rb"(?i)(?:/home/[^/\x00]+/(?:workspace|projects|pycharmprojects)/"
        rb"|/Users/[^/\x00]+/(?:workspace|projects)/"
        rb"|[A-Z]:\\Users\\[^\\\x00]+\\)"
    ),
}

GLIBC_PATTERN = re.compile(r"GLIBC_(\d+)\.(\d+)")
COPYRIGHT_DISTRIBUTION = re.compile(
    r"bundled/python-(?:packages|libs)/([A-Za-z0-9_.-]+)"
)


def canonical_distribution(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def elf_machine(data: bytes) -> int | None:
    if len(data) < 20 or data[:4] != b"\x7fELF":
        return None
    byte_order = "<" if data[5] == 1 else ">"
    return struct.unpack(f"{byte_order}H", data[18:20])[0]


def required_glibc(readelf: str, data: bytes) -> tuple[int, int]:
    with tempfile.NamedTemporaryFile() as file:
        file.write(data)
        file.flush()
        result = subprocess.run(
            [readelf, "--wide", "--version-info", file.name],
            check=False,
            capture_output=True,
            text=True,
        )
    if result.returncode != 0:
        raise RuntimeError(f"readelf failed: {result.stderr.strip()}")
    versions = [
        tuple(map(int, match)) for match in GLIBC_PATTERN.findall(result.stdout)
    ]
    return max(versions, default=(0, 0))


def iter_payloads(archive: CArchiveReader):
    for name, entry in archive.toc.items():
        typecode = entry[-1]
        if typecode == "z":
            pyz = archive.open_embedded_archive(name)
            for module_name in pyz.toc:
                data = pyz.extract(module_name, raw=True)
                if data is not None:
                    yield f"{name}:{module_name}", data, "module"
            continue
        yield name, archive.extract(name), typecode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    parser.add_argument("--target-series", required=True, choices=sorted(SERIES_GLIBC))
    parser.add_argument(
        "--expected-architecture", required=True, choices=sorted(ELF_MACHINES)
    )
    parser.add_argument("--copyright", required=True, type=Path)
    parser.add_argument("--glibc-output", required=True, type=Path)
    args = parser.parse_args()

    readelf = shutil.which("readelf")
    if readelf is None:
        parser.error("readelf is required to audit embedded ELF files")

    archive = CArchiveReader(str(args.binary))
    failures: list[str] = []
    members: set[str] = set()
    pyz_modules: set[str] = set()
    package_config_data: bytes | None = None
    bundled_imports: set[str] = set()
    max_glibc = (0, 0)
    with args.binary.open("rb") as binary:
        main_machine = elf_machine(binary.read(64))

    expected_machine = ELF_MACHINES[args.expected_architecture]
    if main_machine is None:
        failures.append("main executable is not an ELF binary")
    elif main_machine != expected_machine:
        failures.append(
            f"main executable does not match {args.expected_architecture}: "
            f"ELF machine {main_machine}"
        )

    for name, data, typecode in iter_payloads(archive):
        members.add(name)
        if name == "package_config.toml":
            package_config_data = data
        if typecode == "module":
            module_name = name.partition(":")[2]
            pyz_modules.add(module_name)
            bundled_imports.add(module_name.partition(".")[0])
        else:
            member_root = name.partition("/")[0].partition(".")[0]
            if member_root:
                bundled_imports.add(member_root)
        if any(pattern.search(name) for pattern in FORBIDDEN_MEMBERS):
            failures.append(f"forbidden archive member: {name}")
        if PYTHON_SOURCE.search(name) and not RUNTIME_PYTHON_SOURCE.fullmatch(name):
            failures.append(f"forbidden Python source member: {name}")

        module_name = name.partition(":")[2] if typecode == "module" else ""
        project_member = (
            name.startswith(("notolog/", "notolog-"))
            or name == "package_config.toml"
            or module_name == "notolog"
            or module_name.startswith("notolog.")
        )
        if project_member:
            for label, pattern in SENSITIVE_CONTENT.items():
                if pattern.search(data):
                    failures.append(f"{label} found in archive member: {name}")

        if typecode != "b":
            continue
        machine = elf_machine(data)
        if machine is None:
            continue
        if main_machine is not None and machine != main_machine:
            failures.append(f"foreign-architecture ELF member: {name}")
        max_glibc = max(max_glibc, required_glibc(readelf, data))

    for name in sorted(REQUIRED_MEMBERS - members):
        failures.append(f"required runtime member missing: {name}")
    for name in sorted(REQUIRED_PYZ_MODULES - pyz_modules):
        failures.append(f"required embedded Python module missing: {name}")

    if package_config_data is not None:
        try:
            package_config = tomllib.loads(package_config_data.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
            failures.append(f"invalid package_config.toml: {error}")
        else:
            if package_config.get("package", {}).get("type") != "bin":
                failures.append('package_config.toml must set package.type to "bin"')

    distribution_map = importlib.metadata.packages_distributions()
    bundled_distributions = {
        canonical_distribution(distribution)
        for imported_name in bundled_imports
        for distribution in distribution_map.get(imported_name, ())
        if canonical_distribution(distribution) != "notolog"
    }
    # The bootloader is linked into the executable and has no importable module.
    bundled_distributions.add("pyinstaller")
    copyright_text = args.copyright.read_text(encoding="utf-8")
    covered_distributions = {
        canonical_distribution(name)
        for name in COPYRIGHT_DISTRIBUTION.findall(copyright_text)
    }
    for distribution in sorted(bundled_distributions - covered_distributions):
        failures.append(
            f"bundled distribution missing from debian/copyright: {distribution}"
        )

    supported_glibc = SERIES_GLIBC[args.target_series]
    if max_glibc > supported_glibc:
        failures.append(
            f"embedded GLIBC_{max_glibc[0]}.{max_glibc[1]} exceeds "
            f"{args.target_series} GLIBC_{supported_glibc[0]}.{supported_glibc[1]}"
        )

    if failures:
        for failure in failures[:50]:
            print(f"ERROR: {failure}")
        if len(failures) > 50:
            print(f"ERROR: {len(failures) - 50} additional failures omitted")
        return 1

    version = f"{max_glibc[0]}.{max_glibc[1]}"
    args.glibc_output.write_text(f"{version}\n", encoding="utf-8")
    print(
        f"Bundle audit passed: {args.target_series}, GLIBC_{version}, {len(archive.toc)} members"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
