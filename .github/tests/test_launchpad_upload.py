# SPDX-FileCopyrightText: 2026 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT
"""Exercise PPA transfer recovery with synthetic files and mocked commands."""

import os
import io
from pathlib import Path
import re
import subprocess
import tempfile
import tarfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/launchpad.yaml"
VERSIONS = [
    "1.2.4-1ubuntu1~ppa1~ubuntu22.04.1",
    "1.2.4-1ubuntu1~ppa1~ubuntu24.04.1",
    "1.2.4-1ubuntu1~ppa1~ubuntu26.04.1",
]
COMMAND = """#!/usr/bin/env bash
set -eu
command_name="${0##*/}"
printf '%s %s\\n' "$command_name" "$*" >> "$COMMAND_LOG"
case "$command_name" in
  gpg) exit "$GPG_STATUS" ;;
  sleep) exit 0 ;;
  timeout)
    if [ "$TIMEOUT_STATUS" -ne 0 ]; then
      exit "$TIMEOUT_STATUS"
    fi
    shift 3
    exec "$@"
    ;;
  dput)
    counter="$STATE_DIR/${2##*/}.count"
    count=0
    if [ -f "$counter" ]; then
      read -r count < "$counter"
    fi
    count=$((count + 1))
    printf '%s\\n' "$count" > "$counter"
    case "$2" in
      *ubuntu24.04.1*)
        if [ "$count" -le "$DPUT_FAILURES" ]; then
          exit 73
        fi
        ;;
    esac
    ;;
esac
"""


def workflow_script(name):
    workflow = WORKFLOW.read_text()
    step = re.search(
        r"^      - name: " + re.escape(name) + r"\n(.*?)(?=^      - name:|\Z)",
        workflow,
        re.M | re.S,
    )
    script = re.search(r"^        run: \|\n((?:          .*\n|\n)+)", step[1], re.M)
    return "\n".join(line[10:] for line in script[1].splitlines())


class TestPpaUpload(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.package = self.root / "source-package"
        self.package.mkdir()
        self.log = self.root / "commands.log"
        for name in ("gpg", "dput", "timeout", "sleep"):
            path = self.bin / name
            path.write_text(COMMAND)
            path.chmod(0o755)
        self.files = {}
        for version in VERSIONS:
            for suffix in (".dsc", "_source.changes"):
                path = self.package / f"notolog_{version}{suffix}"
                path.write_text("Synthetic signed-package fixture.\n")
                self.files[path] = path.read_bytes()
        (self.package / "versions.txt").write_text(
            "".join(
                f"{series}={version}\n"
                for series, version in zip(("jammy", "noble", "resolute"), VERSIONS)
            )
        )
        self.env = dict(
            os.environ,
            PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
            COMMAND_LOG=str(self.log),
            STATE_DIR=str(self.root),
            GPG_STATUS="0",
            DPUT_FAILURES="0",
            TIMEOUT_STATUS="0",
        )

    def run_upload(self, **settings):
        result = subprocess.run(
            [
                "bash",
                "-e",
                "-u",
                "-o",
                "pipefail",
                "-c",
                workflow_script("Upload to PPA"),
            ],
            cwd=self.root,
            env=dict(self.env, **settings),
            text=True,
            capture_output=True,
            timeout=10,
        )
        for path, data in self.files.items():
            self.assertEqual(path.read_bytes(), data)
        self.commands = self.log.read_text().splitlines() if self.log.exists() else []
        return result

    def uploads(self, version):
        return [
            line
            for line in self.commands
            if line.startswith("dput ") and version in line
        ]

    def test_success_verifies_each_signed_file_and_uploads_each_series_once(self):
        result = self.run_upload()
        self.assertEqual(result.returncode, 0, result.stderr)
        for version in VERSIONS:
            self.assertEqual(len(self.uploads(version)), 1)
            for suffix in (".dsc", "_source.changes"):
                self.assertIn(
                    f"gpg --batch --verify source-package/notolog_{version}{suffix}",
                    self.commands,
                )
        self.assertFalse(any(line.startswith("sleep ") for line in self.commands))
        transfers = [line for line in self.commands if line.startswith("timeout ")]
        self.assertEqual(len(transfers), 3)
        self.assertTrue(
            all(
                line.startswith("timeout --signal=TERM --kill-after=30s 1200s dput ")
                for line in transfers
            )
        )
        self.assertFalse(
            any("--unchecked" in line or "--force" in line for line in self.commands)
        )

    def test_retries_failed_series_without_replaying_successful_series(self):
        result = self.run_upload(DPUT_FAILURES="2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [len(self.uploads(version)) for version in VERSIONS], [1, 3, 1]
        )
        self.assertEqual(
            [line for line in self.commands if line.startswith("sleep ")],
            ["sleep 15", "sleep 30"],
        )

    def test_permanent_failure_stops_after_three_attempts(self):
        result = self.run_upload(DPUT_FAILURES="99")
        self.assertEqual(result.returncode, 73)
        self.assertEqual(
            [len(self.uploads(version)) for version in VERSIONS], [1, 3, 0]
        )
        self.assertIn("retain the source artifact", result.stderr)

    def test_invalid_signature_prevents_any_transfer(self):
        result = self.run_upload(GPG_STATUS="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(
            any(line.startswith(("timeout ", "dput ")) for line in self.commands)
        )
        self.assertIn("Signature verification failed", result.stderr)

    def test_timeouts_are_bounded_and_remain_failures(self):
        result = self.run_upload(TIMEOUT_STATUS="124")
        self.assertEqual(result.returncode, 124)
        self.assertEqual(
            len([line for line in self.commands if line.startswith("timeout ")]), 3
        )
        self.assertFalse(any(line.startswith("dput ") for line in self.commands))

    def test_preserves_signed_bundle_before_publication(self):
        workflow = WORKFLOW.read_text()
        self.assertLess(
            workflow.index("- name: Preserve source artifacts"),
            workflow.index("- name: Upload to PPA"),
        )
        self.assertIn(
            "always() && hashFiles('source-package/*_source.changes') != ''", workflow
        )
        self.assertIn("          path: source-package/", workflow)
        self.assertIn("          passive_ftp = 1", workflow)
        self.assertIn("          allow_unsigned_uploads = 0", workflow)


class TestPpaPackaging(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.runner = self.root / "runner"
        self.runner.mkdir()
        self.project = self.root / "project"
        self.project.mkdir()
        debian = self.project / "debian"
        debian.mkdir()
        (debian / "control").write_text(
            "Source: notolog\n\nPackage: notolog\nArchitecture: amd64 arm64\n"
        )
        (debian / "changelog").write_text(
            "notolog (1.2.4-1ubuntu1) resolute; urgency=medium\n\n  * Synthetic package.\n\n"
            " -- Fixture Maintainer <maintainer@example.invalid>  Sat, 10 Oct 2026 00:00:00 +0000\n"
        )
        reuse = self.runner / "ppa-source"
        upstream = reuse / "upstream/pyinstaller/dist"
        upstream.mkdir(parents=True)
        (upstream / "notolog").write_bytes(b"Synthetic executable; never run.\n")
        self.archive = reuse / "notolog_1.2.4.orig.tar.xz"
        with tarfile.open(self.archive, "w:xz") as archive:
            value = b"Synthetic executable; never run.\n"
            member = tarfile.TarInfo("pyinstaller/dist/notolog")
            member.size = len(value)
            archive.addfile(member, io.BytesIO(value))
        self.original = self.archive.read_bytes()
        self.accepted = reuse / "accepted-versions.txt"
        self.accepted.write_text(VERSIONS[0] + "\n")
        (reuse / "archive.json").write_text("{}\n")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        build = self.bin / "dpkg-buildpackage"
        build.write_text("""#!/usr/bin/env bash
set -eu
version="$(dpkg-parsechangelog --show-field Version)"
for suffix in .debian.tar.xz .dsc _source.changes _source.buildinfo; do
  printf 'Synthetic source metadata.\\n' > "../notolog_${version}${suffix}"
done
""")
        build.chmod(0o755)

    def package(self):
        environment = dict(
            os.environ,
            PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
            RUNNER_TEMP=str(self.runner),
            TARGET_SERIES_LIST="jammy noble resolute",
            PPA_REVISION="1",
            DRY_RUN="true",
            SOURCE_DATE_EPOCH="0",
        )
        return subprocess.run(
            [
                "bash",
                "-e",
                "-u",
                "-o",
                "pipefail",
                "-c",
                workflow_script("Build source package"),
            ],
            cwd=self.project,
            env=environment,
            text=True,
            capture_output=True,
            timeout=20,
        )

    def test_all_reuses_original_and_packages_only_missing_series(self):
        result = self.package()
        self.assertEqual(result.returncode, 0, result.stderr)
        package = self.project / "source-package"
        self.assertEqual(
            (package / "notolog_1.2.4.orig.tar.xz").read_bytes(), self.original
        )
        self.assertEqual(self.archive.read_bytes(), self.original)
        self.assertEqual(
            (package / "versions.txt").read_text().splitlines(),
            [f"noble={VERSIONS[1]}", f"resolute={VERSIONS[2]}"],
        )
        self.assertFalse((package / f"notolog_{VERSIONS[0]}.dsc").exists())
        for version in VERSIONS[1:]:
            self.assertTrue((package / f"notolog_{version}.dsc").is_file())

    def test_all_registered_versions_produce_no_uploads(self):
        self.accepted.write_text("\n".join(VERSIONS) + "\n")
        result = self.package()
        self.assertEqual(result.returncode, 0, result.stderr)
        package = self.project / "source-package"
        self.assertEqual((package / "versions.txt").read_text(), "")
        self.assertFalse(list(package.glob("*_source.changes")))
        self.assertIn("nothing to upload", result.stdout)


if __name__ == "__main__":
    unittest.main()
