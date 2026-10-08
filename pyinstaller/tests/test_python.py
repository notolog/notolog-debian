# SPDX-FileCopyrightText: 2026 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT
"""Verify the bundled interpreter's compatibility and security baseline."""

from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CHECK = runpy.run_path(str(ROOT / 'scripts' / 'verify-python.py'))['main']


class TestPythonVersion(unittest.TestCase):
    def test_rejects_unsupported_interpreters(self):
        for version in [(3, 10, 22), (3, 15, 2), (4, 0, 0)]:
            with self.subTest(version=version), patch('sys.version_info', (*version, 'final', 0)):
                output = StringIO()
                with redirect_stderr(output):
                    self.assertEqual(CHECK(), 1)
                self.assertIn('Python 3.11–3.14', output.getvalue())

    def test_rejects_unpatched_interpreters(self):
        for version, minimum in [((3, 11, 17), '3.11.18'), ((3, 12, 15), '3.12.16'),
                                 ((3, 13, 17), '3.13.18'), ((3, 14, 4), '3.14.10'),
                                 ((3, 14, 9), '3.14.10')]:
            with self.subTest(version=version), patch('sys.version_info', (*version, 'final', 0)):
                output = StringIO()
                with redirect_stderr(output):
                    self.assertEqual(CHECK(), 1)
                self.assertIn(f'Python {minimum}', output.getvalue())

    def test_accepts_patched_builder_interpreters(self):
        for version in [(3, 11, 18), (3, 11, 19), (3, 12, 16), (3, 12, 17),
                        (3, 13, 18), (3, 13, 19), (3, 14, 10), (3, 14, 11)]:
            with self.subTest(version=version), patch('sys.version_info', (*version, 'final', 0)):
                self.assertEqual(CHECK(), 0)

    def test_rejects_prerelease_interpreters(self):
        for version in [(3, 11, 18), (3, 12, 16), (3, 13, 18), (3, 14, 10)]:
            with self.subTest(version=version), patch('sys.version_info', (*version, 'candidate', 1)):
                with redirect_stderr(StringIO()):
                    self.assertEqual(CHECK(), 1)

    def test_checks_interpreter_before_cleaning_artifacts(self):
        script = (ROOT / 'build.sh').read_text()
        self.assertLess(script.index('"$SCRIPTS_DIR/verify-python.py"'),
                        script.index('"$PYI_DIR/clean-build.sh"'))


if __name__ == '__main__':
    unittest.main()
