#!/usr/bin/env python3
"""Verify that all beta release identifiers agree."""

from __future__ import annotations

import re
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TAG = "v0.1.0-beta.1"
PYTHON_VERSION = "0.1.0b1"
DEBIAN_VERSION = "0.1.0~beta1-1"
APPSTREAM_VERSION = "0.1.0-beta.1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


with (ROOT / "pyproject.toml").open("rb") as handle:
    project = tomllib.load(handle)["project"]

require(
    project["version"] == PYTHON_VERSION,
    f"Python version mismatch: {project['version']} != {PYTHON_VERSION}",
)

build_deb = (ROOT / "scripts" / "build-deb.sh").read_text(encoding="utf-8")
require(
    f"TROIKA_D_LITE_DEB_VERSION:-{DEBIAN_VERSION}" in build_deb,
    "Default Debian release version is not aligned with the beta identity.",
)

verify_deb = (ROOT / "scripts" / "verify-deb.sh").read_text(encoding="utf-8")
require(
    DEBIAN_VERSION in verify_deb,
    "Debian verifier does not enforce the beta package version.",
)

root = ET.parse(
    ROOT / "data" / "io.github.scientifica007.TroikaDLite.metainfo.xml"
).getroot()
versions = {
    release.attrib.get("version")
    for release in root.findall("./releases/release")
}
require(
    APPSTREAM_VERSION in versions,
    f"AppStream release missing: {APPSTREAM_VERSION}",
)

release_notes = (
    ROOT / "docs" / "RELEASE-NOTES-v0.1.0-beta.1.md"
).read_text(encoding="utf-8")
require(TAG in release_notes, f"Release notes do not identify {TAG}")

l8 = (ROOT / "docs" / "L8-BETA-RELEASE.md").read_text(encoding="utf-8")
for value in (TAG, PYTHON_VERSION, DEBIAN_VERSION, APPSTREAM_VERSION):
    require(value in l8, f"L8 release document missing identity: {value}")

readme = (ROOT / "README.md").read_text(encoding="utf-8")
require(TAG in readme, f"README does not identify the candidate {TAG}")

critical = "\n".join(
    [
        (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
        build_deb,
        (ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        ),
    ]
)
require(
    not re.search(r"0\.1\.0a0|0\.1\.0~alpha0", critical),
    "Stale alpha release identity remains in release-critical files.",
)

print("Release metadata alignment: PASS")
print(f"tag={TAG}")
print(f"python={PYTHON_VERSION}")
print(f"debian={DEBIAN_VERSION}")
print(f"appstream={APPSTREAM_VERSION}")
