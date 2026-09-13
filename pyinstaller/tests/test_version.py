# SPDX-FileCopyrightText: 2026 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT
"""
Notolog Editor - Debian Package Builder
Build scripts and packaging for the Notolog Editor Debian release.

File Details:
- Purpose: Test executable version checks used by release builds.

Repository: https://github.com/notolog/notolog-debian
App Repository: https://github.com/notolog/notolog-editor
Website: https://notolog.app

Author: Vadim Bakhrenkov
Copyright: 2025-2026 Vadim Bakhrenkov
License: MIT License

For detailed instructions and project information, please see the repository's README.md.
"""

import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'verify-version.py'
SPEC = importlib.util.spec_from_file_location('verify_version', SCRIPT)
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


class TestExecutableVersion(unittest.TestCase):
    def test_version_requires_successful_exact_output(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / 'notolog'
            for output, status, accepted in [
                ('Notolog 1.2.3', 0, True),
                ('Notolog 1.2.2', 0, False),
                ('Notolog 1.2.3', 1, False),
                ('', 0, False),
                ('Notolog 1.2.3 unexpected', 0, False),
            ]:
                with self.subTest(output=output, status=status):
                    binary.write_text('#!/bin/sh\n[ "$1" = "--version" ] || exit 2\n'
                                      '[ "$QT_QPA_PLATFORM" = "offscreen" ] || exit 3\n'
                                      '[ "$XDG_CONFIG_HOME" != "$XDG_DATA_HOME" ] || exit 4\n'
                                      f"printf '%s\\n' '{output}'\nexit {status}\n")
                    binary.chmod(0o700)
                    if accepted:
                        VERIFIER.verify_version(binary, '1.2.3')
                    else:
                        with self.assertRaises(RuntimeError):
                            VERIFIER.verify_version(binary, '1.2.3')


if __name__ == '__main__':
    unittest.main()
