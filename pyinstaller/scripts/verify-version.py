# SPDX-FileCopyrightText: 2026 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT
"""
Notolog Editor - Debian Package Builder
Build scripts and packaging for the Notolog Editor Debian release.

File Details:
- Purpose: Verify the executable reports the version being packaged.

Repository: https://github.com/notolog/notolog-debian
App Repository: https://github.com/notolog/notolog-editor
Website: https://notolog.app

Author: Vadim Bakhrenkov
Copyright: 2025-2026 Vadim Bakhrenkov
License: MIT License

For detailed instructions and project information, please see the repository's README.md.
"""

import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def verify_version(binary, expected_version):
    with tempfile.TemporaryDirectory(prefix="notolog-version-") as directory:
        env = dict(
            os.environ,
            QT_QPA_PLATFORM="offscreen",
            XDG_CONFIG_HOME=str(Path(directory) / "config"),
            XDG_DATA_HOME=str(Path(directory) / "data"),
        )
        result = subprocess.run(
            [str(Path(binary).resolve()), "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
    expected = f"Notolog {expected_version}"
    if result.returncode != 0 or result.stdout.strip() != expected:
        raise RuntimeError(
            f"Expected {expected!r}; executable returned "
            f"{result.stdout.strip()!r} (exit {result.returncode})"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Verify the executable reports the version being packaged."
    )
    parser.add_argument("binary")
    parser.add_argument("expected_version")
    args = parser.parse_args()
    verify_version(args.binary, args.expected_version)
    print(f"Executable version {args.expected_version} verified")


if __name__ == "__main__":
    main()
