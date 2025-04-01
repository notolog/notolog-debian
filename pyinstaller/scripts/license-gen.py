# Debian Package Builder for Notolog Editor
# Build scripts and packaging for the Notolog Editor Debian release.
#
# Repository: https://github.com/notolog/notolog-debian
# License: MIT License
#
# SPDX-FileCopyrightText: 2025 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT

import os
import re
from pathlib import Path

# SPDX-compliant mapping per package
PACKAGE_LICENSE_MAP = {
    "PySide6_Essentials": "LGPL-3.0-or-later",
    "shiboken6": "LGPL-3.0-or-later",
    "cryptography": "Apache-2.0 AND BSD-3-Clause",
    "protobuf": "BSD-3-Clause",
    "packaging": "Apache-2.0 OR BSD-3-Clause",
    "click": "BSD-3-Clause",
    "MarkupSafe": "BSD-3-Clause",
    "Pygments": "BSD-2-Clause",
    "numpy": "BSD-3-Clause",
    "Markdown": "BSD-3-Clause",
    "Jinja2": "BSD-3-Clause",
    "emoji": "BSD-3-Clause",
    "flatbuffers": "Apache-2.0",
    "diskcache": "Apache-2.0",
    "poetry-core": "MIT",
    "build": "MIT",
    "coloredlogs": "MIT",
    "cffi": "MIT",
    "humanfriendly": "MIT",
    "iniconfig": "MIT",
    "pycparser": "BSD-3-Clause",
    "sympy": "BSD-3-Clause",
    "onnxruntime": "MIT",
    "onnxruntime-genai": "MIT",
    "qasync": "BSD-2-Clause",
    "pyproject_hooks": "MIT",
    "llama_cpp_python": "MIT",
    "pluggy": "MIT",
    "typing_extensions": "Python-2.0",
}

# Generic SPDX fallback license name mapping
GENERIC_LICENSE_MAP = {
    "MIT License": "MIT",
    "BSD License": "BSD-3-Clause",
    "Apache Software License": "Apache-2.0",
    "Apache License 2.0": "Apache-2.0",
    "Python Software Foundation License": "Python-2.0",
    "GNU General Public License (GPL)": "GPL-3.0-or-later",
    "GNU Lesser General Public License (LGPL)": "LGPL-3.0-or-later",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "ISC License": "ISC",
    "Public Domain": "CC0-1.0",
    "UNKNOWN": "UNKNOWN",
}

# Mapping of SPDX license identifiers to system license file paths
SYSTEM_LICENSE_PATH_MAP = {
    "Apache-2.0": "/usr/share/common-licenses/Apache-2.0",
    "LGPL-3.0-or-later": "/usr/share/common-licenses/GPL-3",
}

# Supported dual-license combinations (used to include both license texts if applicable)
DUAL_LICENSE_MAP = {
    "Apache-2.0 AND BSD-3-Clause": True,
    "Apache-2.0 OR BSD-3-Clause": True,
}

def normalize_license(pkg_name: str, raw_license: str) -> str:
    # Prefer specific per-package mapping (SPDX-compliant)
    if pkg_name in PACKAGE_LICENSE_MAP:
        return PACKAGE_LICENSE_MAP[pkg_name]
    # Fallback to generic mapping
    return GENERIC_LICENSE_MAP.get(raw_license.strip(), raw_license.strip())

def extract_copyright_block(license_file: Path) -> str:
    """
    Extracts the first copyright block from a license file,
    preserving multiline entries if present.

    Returns:
        String block for inclusion in debian/copyright
    """
    if not license_file.is_file():
        return []

    try:
        text = license_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Could not read license file: {license_file} — {e}")
        return []

    lines = text.strip().splitlines()
    collected = []
    started = False

    pattern = re.compile(r"^\s*(?:Copyright|©|\(c\))[:\s]*(.+)", re.IGNORECASE)

    for line in lines:
        stripped = line.strip()

        if not started and pattern.match(stripped):
            started = True

        if started:
            if not stripped:
                break  # End block on first blank line

            # Remove leading 'Copyright ...' from each line
            match = pattern.match(stripped)
            if match:
                cleaned_line = match.group(1)
            else:
                cleaned_line = stripped

            collected.append(cleaned_line)

    # Format the result: join all collected lines under one "Copyright:" block
    return "\n ".join(collected)

def parse_pip_licenses(file_path):
    entries = []
    parsing = False

    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Start table parsing
            if line.startswith("| Name") and "License" in line:
                parsing = True
                continue

            if parsing and line.startswith("|") and not line.startswith("|----"):
                parts = [p.strip() for p in line.strip("|").split("|")]

                if len(parts) < 5:
                    continue

                name = parts[0]
                license_raw = parts[2]
                author = parts[3] if parts[3] else "Unknown"
                copyright_block = author  # Use author name as fallback if no explicit copyright is found
                license_file_path = parts[4]

                # Skip unknown entries
                if not name or not license_raw or license_raw.upper() == "UNKNOWN":
                    continue

                if license_file_path and os.path.isfile(license_file_path):
                    copyright_block = extract_copyright_block(Path(license_file_path))

                license_spdx = normalize_license(name, license_raw)

                license_block = f"""Files: bundled/python-packages/{name}
Copyright: {copyright_block}
License: {license_spdx}
License-Text:
"""

                # Case 1: system license reference (e.g., Apache-2.0)
                if license_spdx in SYSTEM_LICENSE_PATH_MAP:
                    license_system_path = SYSTEM_LICENSE_PATH_MAP[license_spdx]
                    license_block += f" {license_system_path}\n"
                    license_file_path = None  # Prevent further license file reading

                # Case 2: custom license file available
                elif license_file_path and os.path.isfile(license_file_path):
                    try:
                        license_text = Path(license_file_path).read_text(encoding="utf-8").strip()
                        if license_text:
                            indented_text = " " + license_text.replace("\n", "\n ")
                            license_block += f"{indented_text}\n"
                    except Exception as e:
                        print(f"Could not read license file for {name}: {e}")

                # Case 3: dual license (e.g., Apache + BSD)
                if license_spdx in DUAL_LICENSE_MAP:
                    apache_path = SYSTEM_LICENSE_PATH_MAP.get("Apache-2.0")
                    license_block += f"\n The full text of the Apache-2.0 license can be found at:\n {apache_path}\n"

                    # Ensure license_file_path is still valid before replacing
                    if license_file_path:
                        bsd_license_file = Path(license_file_path).with_name("LICENSE.BSD")
                        if bsd_license_file.exists():
                            try:
                                bsd_text = bsd_license_file.read_text(encoding="utf-8").strip()
                                if bsd_text:
                                    indented_bsd = " " + bsd_text.replace("\n", "\n ")
                                    license_block += f"\n The full BSD license text follows:\n\n{indented_bsd}\n"
                            except Exception as e:
                                print(f"Could not read BSD license file for {name}: {e}")

                entries.append(license_block)

    return entries

def generate_copyright():
    base_header = """Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: Notolog
Source: https://notolog.app
"""

    current_dir = Path(__file__).resolve().parent
    builder_dir = current_dir.parent
    project_root = builder_dir.parent

    base_path = project_root / "debian" / "copyright"
    generated_path = builder_dir / "build" / "copyright-generated"
    license_report_path = builder_dir / "build" / "reports" / "pip-licenses.md"

    entries = parse_pip_licenses(license_report_path)
    result = "\n".join(entries)

    generated_path.write_text(result, encoding="utf-8")
    print("pip license file generated.")

    append_generated_copyright(base_path, generated_path)

def append_generated_copyright(base_path, generated_path):
    base_content = base_path.read_text(encoding="utf-8").strip()
    generated_content = generated_path.read_text(encoding="utf-8").strip()
    combined = base_content + "\n\n# === AUTO-GENERATED LICENSES ===\n\n" + generated_content + "\n"
    base_path.write_text(combined, encoding="utf-8")
    print(f"{base_path} updated with generated license entries.")

if __name__ == "__main__":
    generate_copyright()

