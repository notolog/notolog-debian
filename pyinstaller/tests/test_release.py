# SPDX-FileCopyrightText: 2026 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT
"""Verify release source selection with isolated Git repositories."""

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


WORKFLOWS = Path(__file__).resolve().parents[2] / '.github' / 'workflows'
VERSION_KEYS = {'build.yaml': 'UPSTREAM_VERSION', 'launchpad.yaml': 'PACKAGE_VERSION'}


class TestReleaseSource(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.origin = self.root / 'origin'
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
                        GIT_AUTHOR_NAME='Fixture Author', GIT_AUTHOR_EMAIL='author@example.invalid',
                        GIT_COMMITTER_NAME='Fixture Author', GIT_COMMITTER_EMAIL='author@example.invalid')
        self.git('init', str(self.origin))
        self.git('-C', str(self.origin), '-c', 'commit.gpgsign=false',
                 'commit', '--allow-empty', '-m', 'Initial fixture')
        self.commit = self.git('-C', str(self.origin), 'rev-parse', 'HEAD').strip()
        self.git('clone', str(self.origin), str(self.root / 'src'))
        debian = self.root / 'debian'
        debian.mkdir()
        (debian / 'changelog').write_text(
            'notolog (1.2.4-1ubuntu1) resolute; urgency=medium\n\n'
            '  * Fixture release.\n\n'
            ' -- Package Maintainer <maintainer@example.invalid>  '
            'Sat, 10 Oct 2026 00:00:00 +0000\n', encoding='utf-8')

    def git(self, *args):
        return subprocess.run(['git', *args], env=self.env, check=True,
                              text=True, capture_output=True, timeout=10).stdout

    def verify(self, *, version='v1.2.4', commit=None, success=False, error=None):
        for filename, version_key in VERSION_KEYS.items():
            with self.subTest(workflow=filename):
                workflow = (WORKFLOWS / filename).read_text(encoding='utf-8')
                match = re.search(
                    r'^      - name: Verify application release commit\n'
                    r'        run: \|\n((?:          .*\n|\n)+)', workflow, re.M)
                self.assertIsNotNone(match)
                script = '\n'.join(line[10:] for line in match[1].splitlines())
                env = dict(self.env, APP_RELEASE_COMMIT=self.commit if commit is None else commit)
                env[version_key] = version
                result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script],
                                        cwd=self.root, env=env, text=True,
                                        capture_output=True, timeout=10)
                if success:
                    self.assertEqual(result.returncode, 0, result.stderr)
                else:
                    self.assertNotEqual(result.returncode, 0)
                if error:
                    self.assertIn(error, result.stderr)

    def test_accepts_matching_lightweight_tag(self):
        self.git('-C', str(self.origin), 'tag', 'v1.2.4')
        self.verify(success=True)

    def test_accepts_matching_annotated_tag(self):
        self.git('-C', str(self.origin), '-c', 'tag.gpgsign=false',
                 'tag', '-a', 'v1.2.4', '-m', 'Fixture release')
        self.verify(success=True)

    def test_rejects_wrong_package_version(self):
        self.verify(version='v1.2.3', error='does not match the Debian package version')

    def test_rejects_wrong_pinned_commit(self):
        self.verify(commit='0' * 40, error='does not match the pinned source')

    def test_rejects_missing_release_tag(self):
        self.verify(error="couldn't find remote ref refs/tags/v1.2.4")

    def test_rejects_tag_on_different_commit(self):
        self.git('-C', str(self.origin), '-c', 'commit.gpgsign=false',
                 'commit', '--allow-empty', '-m', 'Different fixture')
        self.git('-C', str(self.origin), 'tag', 'v1.2.4')
        self.verify(error='Selected application release tag does not match the pinned source')

    def test_rejects_changed_checkout(self):
        self.git('-C', str(self.origin), 'tag', 'v1.2.4')
        self.git('-C', str(self.root / 'src'), '-c', 'commit.gpgsign=false',
                 'commit', '--allow-empty', '-m', 'Changed fixture checkout')
        self.verify(error='Application release commit does not match the pinned source')


if __name__ == '__main__':
    unittest.main()
