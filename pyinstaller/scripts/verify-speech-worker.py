# SPDX-FileCopyrightText: 2026 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT
"""
Notolog Editor - Debian Package Builder
Build scripts and packaging for the Notolog Editor Debian release.

File Details:
- Purpose: Verify the packaged speech protocol without models or audio playback.

Repository: https://github.com/notolog/notolog-debian
App Repository: https://github.com/notolog/notolog-editor
Website: https://notolog.app

Author: Vadim Bakhrenkov
Copyright: 2025-2026 Vadim Bakhrenkov
License: MIT License

For detailed instructions and project information, please see the repository's README.md.
"""

import json
import subprocess
import sys


def main():
    result = subprocess.run(
        [sys.argv[1], "--tts-worker"],
        input=json.dumps({"library": "/nonexistent/notolog-tts-test.so"}) + "\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError("Frozen speech worker exited unexpectedly")
    event = json.loads(result.stdout)
    if not isinstance(event.get("error"), str) or not event["error"]:
        raise RuntimeError("Frozen speech worker did not return a protocol error")
    print("Frozen speech worker protocol verified")


if __name__ == "__main__":
    main()
