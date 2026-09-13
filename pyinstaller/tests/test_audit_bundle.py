# SPDX-FileCopyrightText: 2026 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT
"""
Notolog Editor - Debian Package Builder
Build scripts and packaging for the Notolog Editor Debian release.

File Details:
- Purpose: Audit the launcher compatibility gate without building a frozen app.

Repository: https://github.com/notolog/notolog-debian
App Repository: https://github.com/notolog/notolog-editor
Website: https://notolog.app

Author: Vadim Bakhrenkov
Copyright: 2025-2026 Vadim Bakhrenkov
License: MIT License

For detailed instructions and project information, please see the repository's README.md.
"""

import contextlib
import importlib.util
import io
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'audit-bundle.py'
spec = importlib.util.spec_from_file_location('audit_bundle', SCRIPT)
audit = importlib.util.module_from_spec(spec)
# These tests use a controlled archive, so PyInstaller need not be installed.
reader_module = types.ModuleType('PyInstaller.archive.readers')
reader_module.CArchiveReader = Mock()
with patch.dict(sys.modules, {'PyInstaller.archive.readers': reader_module}):
    spec.loader.exec_module(audit)


class TestLauncherGlibc(unittest.TestCase):
    def test_audio_bundle_excludes_system_and_unused_libraries(self):
        for member in ('PySide6/QtMultimedia.abi3.so', 'PySide6/Qt/lib/libQt6Multimedia.so.6',
                       'libavcodec.so.61', 'libavformat.so.61', 'libswresample.so.5',
                       'libportaudio.so.2'):
            with self.subTest(member=member):
                self.assertTrue(any(pattern.search(member) for pattern in audit.FORBIDDEN_MEMBERS))
        self.assertFalse(any(pattern.search('_sounddevice.py') for pattern in audit.FORBIDDEN_MEMBERS))

    def run_audit(self, version, *, members=None, launcher_payload=b'',
                  forbidden_build_roots=()):
        members = members or {}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / 'notolog'
            header = bytearray(64)
            header[:6] = b'\x7fELF\x02\x01'
            struct.pack_into('<H', header, 18, audit.ELF_MACHINES['amd64'])
            binary.write_bytes(header + launcher_payload)
            copyright_file = root / 'copyright'
            copyright_file.write_text('Files: bundled/python-packages/pyinstaller/*\n')
            output_file = root / 'glibc.txt'
            archive = Mock(toc={name: ('x',) for name in members})
            archive.extract.side_effect = members.__getitem__
            argv = ['audit-bundle.py', str(binary), '--target-series', 'jammy',
                    '--expected-architecture', 'amd64', '--copyright', str(copyright_file),
                    '--glibc-output', str(output_file)]
            for build_root in forbidden_build_roots:
                argv.extend(('--forbidden-build-root', build_root))
            with (patch.object(sys, 'argv', argv),
                  patch.object(audit, 'CArchiveReader', return_value=archive),
                  patch.object(audit, 'REQUIRED_MEMBERS', set()),
                  patch.object(audit, 'REQUIRED_PYZ_MODULES', set()),
                  patch.object(audit.shutil, 'which', return_value='/usr/bin/readelf'),
                  patch.object(audit.importlib.metadata, 'packages_distributions', return_value={}),
                  patch.object(audit, 'required_glibc_file', return_value=version) as launcher_check,
                  contextlib.redirect_stdout(io.StringIO()) as stdout):
                result = audit.main()
            launcher_check.assert_called_once_with('/usr/bin/readelf', binary)
            return result, stdout.getvalue(), output_file.read_text() if output_file.exists() else None

    def test_rejects_launcher_newer_than_target(self):
        result, output, dependency = self.run_audit((2, 39))
        self.assertEqual(result, 1)
        self.assertIn('exceeds jammy', output)
        self.assertIsNone(dependency)

    def test_dependency_includes_launcher_requirement(self):
        result, _, dependency = self.run_audit((2, 35))
        self.assertEqual(result, 0)
        self.assertEqual(dependency, '2.35\n')

    def test_rejects_sensitive_content_in_dependency_member(self):
        result, output, _ = self.run_audit(
            (2, 35),
            members={'dependency/data.txt': b'AKIAABCDEFGHIJKLMNOP'},
        )
        self.assertEqual(result, 1)
        self.assertIn('AWS access key found in archive member: dependency/data.txt', output)

    def test_rejects_build_path_in_dependency_member(self):
        result, output, _ = self.run_audit(
            (2, 35),
            members={'dependency/data.txt': b'/srv/notolog-build/src/file.py'},
            forbidden_build_roots=('/srv/notolog-build',),
        )
        self.assertEqual(result, 1)
        self.assertIn('build path found in archive member: dependency/data.txt', output)

    def test_rejects_user_home_path_in_project_member(self):
        result, output, _ = self.run_audit(
            (2, 35),
            members={'notolog/config.py': b'/home/example/private/config'},
        )
        self.assertEqual(result, 1)
        self.assertIn('user home path found in archive member: notolog/config.py', output)

    def test_rejects_sensitive_content_in_launcher(self):
        result, output, _ = self.run_audit(
            (2, 35),
            launcher_payload=b'ghp_abcdefghijklmnopqrstuvwxyz',
        )
        self.assertEqual(result, 1)
        self.assertIn('GitHub token found in main executable', output)

    def test_rejects_openai_key_in_dependency_member(self):
        result, output, _ = self.run_audit(
            (2, 35),
            members={'dependency/data.txt': b'sk-proj-abcdefghijklmnopqrstuvwxyz'},
        )
        self.assertEqual(result, 1)
        self.assertIn('OpenAI API key found in archive member: dependency/data.txt', output)

    def test_rejects_private_key_in_dependency_member(self):
        result, output, _ = self.run_audit(
            (2, 35),
            members={
                'dependency/data.txt': (
                    b'-----BEGIN OPENSSH PRIVATE KEY-----\n'
                    + b'A' * 120
                    + b'\n-----END OPENSSH PRIVATE KEY-----'
                )
            },
        )
        self.assertEqual(result, 1)
        self.assertIn('private key found in archive member: dependency/data.txt', output)

    def test_accepts_clean_dependency_member(self):
        result, output, dependency = self.run_audit(
            (2, 35),
            members={'dependency/data.txt': b'normal runtime data'},
        )
        self.assertEqual(result, 0)
        self.assertIn('Bundle audit passed', output)
        self.assertEqual(dependency, '2.35\n')


if __name__ == '__main__':
    unittest.main()
