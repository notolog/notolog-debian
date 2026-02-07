# Debian Package Builder for Notolog Editor
# Build scripts and packaging for the Notolog Editor Debian release.
#
# Repository: https://github.com/notolog/notolog-debian
# License: MIT License
#
# SPDX-FileCopyrightText: 2025 Vadim Bakhrenkov
# SPDX-License-Identifier: MIT

import re
from datetime import datetime
from pathlib import Path

# Config
current_dir = Path(__file__).resolve().parent
builder_dir = current_dir.parent
project_root = builder_dir.parent

markdown_file = project_root / "src" / "CHANGELOG.md"
debian_changelog_file = builder_dir / "debian" / "changelog"

# Info
package_name = "notolog"
maintainer = "Notolog <dev@notolog.app>"
urgency = "medium"
"""
* unstable: 🧪 For development and testing (most common for new/first packages)
* testing: For packages waiting to migrate to stable; updated automatically
* stable: For release-ready, production packages
* experimental: For packages not ready for general use or that might break things
"""
status = "unstable"

# Read Markdown changelog
with open(markdown_file, encoding="utf-8") as f:
    content = f.read()

# Extract latest version block
match = re.search(
    r"## \[(?P<version>[^\]]+)\] - (?P<date>\d{4}-\d{2}-\d{2})\n(?P<changes>.*?)(?=\n## |\Z)",
    content,
    re.DOTALL,
)

if not match:
    raise ValueError("No valid version block found in CHANGELOG.md")

version = match.group("version")
date = match.group("date")
changes = match.group("changes").strip()

# Format changes as Debian changelog bullets
lines = []
for line in changes.splitlines():
    stripped = line.strip()
    if stripped.startswith("- "):
        lines.append("  * " + stripped[2:])
    elif stripped.startswith("###"):
        lines.append("")  # Add blank line before section titles
    elif stripped:
        lines.append("    " + stripped)

# Format Debian changelog entry
date_obj = datetime.strptime(date, "%Y-%m-%d")
debian_timestamp = date_obj.strftime("%a, %d %b %Y %H:%M:%S +0000")

formatted_lines = "\n".join(line.rstrip() for line in lines)
entry = (
    f"{package_name} ({version}) {status}; urgency={urgency}\n"
    f"{formatted_lines}\n\n"
    f" -- {maintainer}  {debian_timestamp}"
)

# Combine with existing
if not debian_changelog_file.exists():
    new_content = entry.strip()
else:
    old_content = debian_changelog_file.read_text(encoding="utf-8")
    new_content = entry.strip() + "\n\n" + old_content

# Write back to file
debian_changelog_file.write_text(new_content, encoding="utf-8")
print(f"Debian changelog updated with version {version}")
