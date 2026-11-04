# SPDX-FileCopyrightText: 2026 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT
"""Verify archive reuse without network requests, signing keys, or real binaries."""

import hashlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "launchpad_source", ROOT / ".github/scripts/launchpad-source.py"
)
SOURCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOURCE)
ARCHIVE = "https://api.launchpad.net/1.0/~fixture/+archive/ubuntu/ppa"
VERSION = "1.2.4-1ubuntu1~ppa1~ubuntu22.04.1"


class TestLaunchpadSource(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.checkout = self.root / "checkout"
        self.checkout.mkdir()
        self.source = {
            "pyproject.toml": b'[tool.poetry]\nversion = "1.2.4"\n',
            "README.md": b"Synthetic source.\n",
        }
        for name, data in self.source.items():
            (self.checkout / name).write_bytes(data)
        (self.checkout / ".gitignore").write_text("Fixture VCS metadata.\n")
        self.env = dict(
            os.environ,
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME="Fixture Author",
            GIT_AUTHOR_EMAIL="author@example.invalid",
            GIT_COMMITTER_NAME="Fixture Author",
            GIT_COMMITTER_EMAIL="author@example.invalid",
        )
        self.git("init", "-q")
        self.git("add", ".")
        self.git("-c", "commit.gpgsign=false", "commit", "-qm", "Synthetic source")
        self.output = self.root / "result"
        self.record = {
            "source_package_name": "notolog",
            "source_package_version": VERSION,
            "status": "Pending",
            "self_link": ARCHIVE + "/+sourcepub/123",
        }
        self.payload = self.archive()

    def git(self, *arguments):
        subprocess.run(
            ["git", "-C", str(self.checkout), *arguments],
            env=self.env,
            check=True,
            capture_output=True,
            timeout=10,
        )

    def archive(self, extra=None, version=b"1.2.4\n", executable=True):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w:xz") as archive:
            members = {f"src/{name}": value for name, value in self.source.items()}
            members["pyinstaller/version.txt"] = version
            members["pyinstaller/dist/notolog"] = (
                b"\x7fELF\x02\x01" + b"\x00" * 12 + b"\x3e\x00"
            )
            if extra:
                members.update(extra)
            for name, value in members.items():
                member = tarfile.TarInfo(name)
                member.size = len(value)
                member.mode = (
                    0o755 if executable and name.endswith("dist/notolog") else 0o644
                )
                archive.addfile(member, io.BytesIO(value))
        return data.getvalue()

    def prepare(self, *, checksum=None, size=None, records=None, files=None):
        original = {
            "url": "https://launchpad.net/fixture/notolog_1.2.4.orig.tar.xz",
            "size": len(self.payload) if size is None else size,
            "sha256": (
                hashlib.sha256(self.payload).hexdigest()
                if checksum is None
                else checksum
            ),
        }
        opener = SimpleNamespace(open=lambda *args, **kwargs: io.BytesIO(self.payload))
        with (
            patch.object(
                SOURCE,
                "publications",
                return_value=[self.record] if records is None else records,
            ),
            patch.object(
                SOURCE, "metadata", return_value=[original] if files is None else files
            ),
            patch.object(SOURCE, "build_opener", return_value=opener),
            patch.dict(os.environ, self.env),
        ):
            return SOURCE.prepare("fixture", "ppa", "1.2.4", self.checkout, self.output)

    def test_new_release_does_not_create_a_replacement_archive(self):
        self.assertFalse(self.prepare(records=[]))
        self.assertEqual((self.output / "accepted-versions.txt").read_text(), "")
        self.assertFalse((self.output / "notolog_1.2.4.orig.tar.xz").exists())

    def test_reuses_pending_source_and_records_registered_versions(self):
        self.assertTrue(self.prepare())
        self.assertEqual(
            (self.output / "notolog_1.2.4.orig.tar.xz").read_bytes(), self.payload
        )
        self.assertEqual(
            (self.output / "accepted-versions.txt").read_text(), VERSION + "\n"
        )
        self.assertTrue((self.output / "archive.json").is_file())

    def test_preserves_published_and_pending_versions(self):
        published = dict(
            self.record,
            source_package_version="1.2.4-1ubuntu1~ppa1~ubuntu24.04.1",
            status="Published",
        )
        self.assertTrue(self.prepare(records=[self.record, published]))
        self.assertEqual(
            len((self.output / "accepted-versions.txt").read_text().splitlines()), 2
        )

    def test_checksum_mismatch_removes_partial_download(self):
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.prepare(checksum="0" * 64)
        self.assertFalse((self.output / "notolog_1.2.4.orig.tar.xz").exists())
        self.assertFalse(list(self.output.glob("*.part")))

    def test_download_size_must_match_metadata(self):
        with self.assertRaisesRegex(ValueError, "size"):
            self.prepare(size=len(self.payload) + 1)

    def test_rejects_missing_original_archive(self):
        with self.assertRaisesRegex(ValueError, "no unique original"):
            self.prepare(files=[])

    def test_rejects_oversized_archive_before_download(self):
        with self.assertRaisesRegex(ValueError, "size or checksum"):
            self.prepare(size=SOURCE.MAX_ARCHIVE + 1)

    def test_rejects_changed_or_unexpected_application_files(self):
        self.payload = self.archive(
            extra={"src/README.md": b"Different release source.\n"}
        )
        with self.assertRaisesRegex(ValueError, "pinned application source"):
            self.prepare()

    def test_rejects_archive_path_traversal(self):
        self.payload = self.archive(extra={"../outside": b"Unexpected file.\n"})
        with self.assertRaises(tarfile.FilterError):
            self.prepare()
        self.assertFalse((self.output / "outside").exists())

    def test_rejects_wrong_executable_version(self):
        self.payload = self.archive(version=b"1.2.3\n")
        with self.assertRaisesRegex(ValueError, "executable version"):
            self.prepare()

    def test_rejects_non_executable_binary(self):
        self.payload = self.archive(executable=False)
        with self.assertRaisesRegex(ValueError, "amd64 ELF binary"):
            self.prepare()

    def test_rejects_packaging_inside_original_archive(self):
        self.payload = self.archive(
            extra={"debian/control": b"Unexpected packaging.\n"}
        )
        with self.assertRaisesRegex(ValueError, "Debian packaging"):
            self.prepare()

    def test_bounds_publication_history_and_checks_pagination_origin(self):
        with patch.object(
            SOURCE,
            "metadata",
            return_value={"entries": [], "next_collection_link": ARCHIVE + "?next"},
        ):
            with self.assertRaisesRegex(ValueError, "page limit"):
                SOURCE.publications(ARCHIVE)
        with patch.object(
            SOURCE,
            "metadata",
            return_value={
                "entries": [],
                "next_collection_link": "https://example.invalid",
            },
        ):
            with self.assertRaisesRegex(ValueError, "pagination URL"):
                SOURCE.publications(ARCHIVE)

    def test_unavailable_api_does_not_allow_a_new_archive(self):
        with patch.object(
            SOURCE, "metadata", side_effect=OSError("Synthetic network failure")
        ):
            with self.assertRaises(OSError):
                SOURCE.prepare("fixture", "ppa", "1.2.4", self.checkout, self.output)

    def test_rejects_untrusted_downloads_and_redirects(self):
        for url in (
            "http://launchpad.net/file",
            "https://example.invalid/file",
            "https://launchpad.net.example.invalid/file",
            "https://launchpadlibrarian.net.example.invalid/file",
            "file:///tmp/fixture",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                SOURCE.check_url(url)
        self.assertEqual(
            SOURCE.check_url("https://example.launchpadlibrarian.net/file"),
            "https://example.launchpadlibrarian.net/file",
        )


if __name__ == "__main__":
    unittest.main()
