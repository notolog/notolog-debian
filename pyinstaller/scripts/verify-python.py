# SPDX-FileCopyrightText: 2026 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT
"""Check the interpreter that will be embedded in the standalone application."""

import sys

# Security baseline: https://discuss.python.org/t/109576
MINIMUM_VERSIONS = {
    (3, 11): (3, 11, 18),
    (3, 12): (3, 12, 16),
    (3, 13): (3, 13, 18),
    (3, 14): (3, 14, 10),
}


def main() -> int:
    minimum = MINIMUM_VERSIONS.get(sys.version_info[:2])
    if minimum is None or sys.version_info[3] != "final":
        print(
            "The builder accepts stable Python 3.11–3.14 interpreters.",
            file=sys.stderr,
        )
        return 1
    if sys.version_info[:3] < minimum:
        version = ".".join(map(str, minimum))
        branch = ".".join(map(str, minimum[:2]))
        print(
            f"Use Python {version} or a newer Python {branch} maintenance release.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
