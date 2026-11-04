#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT
"""Reuse the immutable upstream archive already accepted by a public PPA."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_METADATA = 2 * 1024 * 1024
MAX_ARCHIVE = 2 * 1024**3
MAX_EXTRACTED = 4 * 1024**3
MAX_MEMBERS = 20000
MAX_PAGES = 10


def check_url(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.port not in (None, 443)
        or not (
            parsed.hostname
            in ("api.launchpad.net", "launchpad.net", "launchpadlibrarian.net")
            or (parsed.hostname or "").endswith(".launchpadlibrarian.net")
        )
    ):
        raise ValueError("Untrusted Launchpad download URL")
    return url


class Redirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return super().redirect_request(
            request, fp, code, msg, headers, check_url(newurl)
        )


def download(url, path, limit, expected_size=None, expected_hash=None):
    digest = hashlib.sha256()
    size = 0
    deadline = time.monotonic() + 600
    request = Request(check_url(url), headers={"User-Agent": "AppVerification/1.0"})
    partial = path.with_name(path.name + ".part")
    try:
        with build_opener(Redirects()).open(
            request, timeout=30
        ) as response, partial.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > limit or time.monotonic() > deadline:
                    raise ValueError(
                        "Launchpad download exceeds its size or time limit"
                    )
                output.write(chunk)
                digest.update(chunk)
        if expected_size is not None and size != expected_size:
            raise ValueError("Accepted archive size does not match Launchpad metadata")
        if expected_hash is not None and digest.hexdigest() != expected_hash:
            raise ValueError(
                "Accepted archive checksum does not match Launchpad metadata"
            )
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)


def metadata(url):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "metadata.json"
        download(url, path, MAX_METADATA)
        return json.loads(path.read_bytes())


def publications(archive):
    url = (
        archive
        + "?"
        + urlencode(
            {
                "ws.op": "getPublishedSources",
                "source_name": "notolog",
                "exact_match": "true",
                "ws.size": "100",
            }
        )
    )
    records = []
    for _ in range(MAX_PAGES):
        if not url.startswith(archive + "?"):
            raise ValueError("Unexpected Launchpad pagination URL")
        page = metadata(url)
        if not isinstance(page, dict) or not isinstance(page.get("entries"), list):
            raise ValueError("Invalid Launchpad publication response")
        records.extend(page["entries"])
        url = page.get("next_collection_link")
        if not url:
            return records
    raise ValueError("Launchpad publication history exceeds its page limit")


def extract(archive, destination):
    with tarfile.open(archive) as source:
        members = []
        total = 0
        for member in source:
            total += member.size
            if total > MAX_EXTRACTED or len(members) >= MAX_MEMBERS:
                raise ValueError("Accepted archive exceeds extraction limits")
            members.append(member)
        source.extractall(destination, members=members, filter="data")


def source_files(root):
    result = {}
    for directory, directories, files in os.walk(root, followlinks=False):
        for name in directories + files:
            path = Path(directory) / name
            if path.is_symlink():
                result[path.relative_to(root)] = ("link", os.readlink(path))
            elif path.is_file():
                with path.open("rb") as source:
                    digest = hashlib.file_digest(source, "sha256").hexdigest()
                result[path.relative_to(root)] = (
                    "file",
                    digest,
                    bool(path.stat().st_mode & 0o111),
                )
    return result


def verify_source(upstream, checkout, version):
    # Match the original tar command's VCS exclusions without maintaining a second list.
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        expected = root / "expected"
        expected.mkdir()
        with (root / "source.tar").open("wb") as output:
            subprocess.run(
                ["git", "-C", str(checkout), "archive", "HEAD"],
                stdout=output,
                stderr=subprocess.PIPE,
                check=True,
                timeout=60,
            )
        subprocess.run(
            [
                "tar",
                "--extract",
                "--file",
                str(root / "source.tar"),
                "--exclude-vcs",
                "--no-same-owner",
                "--directory",
                str(expected),
            ],
            capture_output=True,
            check=True,
            timeout=60,
        )
        if source_files(expected) != source_files(upstream / "src"):
            raise ValueError(
                "Accepted archive does not match the pinned application source"
            )
    if (upstream / "pyinstaller/version.txt").read_text().strip() != version:
        raise ValueError(
            "Accepted executable version does not match the selected release"
        )
    binary = upstream / "pyinstaller/dist/notolog"
    with binary.open("rb") as source:
        header = source.read(20)
    if (
        header[:6] != b"\x7fELF\x02\x01"
        or header[18:20] != b"\x3e\x00"
        or not binary.stat().st_mode & 0o111
    ):
        raise ValueError(
            "Accepted archive does not contain an executable amd64 ELF binary"
        )


def prepare(owner, ppa, version, checkout, destination):
    if not all(re.fullmatch(r"[a-z0-9][a-z0-9+.-]*", value) for value in (owner, ppa)):
        raise ValueError("A valid Launchpad owner and PPA name are required")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("Invalid upstream version")
    destination.mkdir()
    archive = f"https://api.launchpad.net/1.0/~{owner}/+archive/ubuntu/{ppa}"
    records = [
        record
        for record in publications(archive)
        if record["source_package_name"] == "notolog"
        and record["source_package_version"].split("-", 1)[0] == version
    ]
    versions = sorted({record["source_package_version"] for record in records})
    if any(not re.fullmatch(r"[0-9A-Za-z.+~:-]+", item) for item in versions):
        raise ValueError("Invalid accepted package version")
    (destination / "accepted-versions.txt").write_text(
        "".join(item + "\n" for item in versions)
    )
    if not records:
        return False
    publication = records[0]["self_link"]
    if not publication.startswith(archive + "/+sourcepub/"):
        raise ValueError("Unexpected Launchpad publication URL")
    files = metadata(
        publication
        + "?"
        + urlencode({"ws.op": "sourceFileUrls", "include_meta": "true"})
    )
    filename = f"notolog_{version}.orig.tar.xz"
    matches = [
        item
        for item in files
        if urlsplit(item["url"]).path.rsplit("/", 1)[-1] == filename
    ]
    if len(matches) != 1:
        raise ValueError(
            "Accepted source has no unique original archive; refusing to rebuild it"
        )
    original = matches[0]
    size = original["size"]
    if (
        not isinstance(size, int)
        or not 0 < size <= MAX_ARCHIVE
        or not re.fullmatch(r"[0-9a-f]{64}", original["sha256"])
    ):
        raise ValueError("Invalid accepted archive size or checksum")
    path = destination / filename
    download(original["url"], path, MAX_ARCHIVE, size, original["sha256"])
    upstream = destination / "upstream"
    extract(path, upstream)
    if (upstream / "debian").exists():
        raise ValueError("Original archive unexpectedly contains Debian packaging")
    verify_source(upstream, checkout, version)
    (destination / "archive.json").write_text(json.dumps(original, indent=2) + "\n")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--ppa", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--github-output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        reused = prepare(
            arguments.owner,
            arguments.ppa,
            arguments.version,
            arguments.source,
            arguments.output,
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        tarfile.TarError,
        subprocess.SubprocessError,
    ):
        raise SystemExit(
            "Cannot verify the PPA source archive; refusing to build or upload a replacement"
        ) from None
    with arguments.github_output.open("a") as output:
        output.write(f"reuse={str(reused).lower()}\n")
    print(
        "Reusing the accepted upstream archive."
        if reused
        else "No accepted upstream archive found."
    )


if __name__ == "__main__":
    main()
