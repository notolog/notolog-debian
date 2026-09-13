# SPDX-FileCopyrightText: 2026 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT
"""
Notolog Editor - Debian Package Builder
Build scripts and packaging for the Notolog Editor Debian release.

File Details:
- Purpose: Verify speech worker dispatch before GUI initialization.

Repository: https://github.com/notolog/notolog-debian
App Repository: https://github.com/notolog/notolog-editor
Website: https://notolog.app

Author: Vadim Bakhrenkov
Copyright: 2025-2026 Vadim Bakhrenkov
License: MIT License

For detailed instructions and project information, please see the repository's README.md.
"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'runtime_hooks' / 'init.py'


class TestSpeechWorker(unittest.TestCase):
    def test_worker_runs_without_application_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = Path(directory) / 'notolog/modules/text_to_speech/native_worker.py'
            worker.parent.mkdir(parents=True)
            worker.write_text("import json, sys; print(json.dumps({'echo': sys.stdin.readline().strip()}))")
            code = ('import runpy, sys; sys._MEIPASS = sys.argv[1]; '
                    'hook = sys.argv[2]; sys.argv = ["notolog", "--tts-worker"]; '
                    'runpy.run_path(hook, run_name="__main__")')
            result = subprocess.run([sys.executable, '-I', '-c', code, directory, str(HOOK)],
                                    input='hello\n', text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {'echo': 'hello'})


if __name__ == '__main__':
    unittest.main()
