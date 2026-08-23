#!/usr/bin/env python3
"""Require one project version across package, metadata, citation, and changelog."""

from __future__ import annotations

import json
import re
import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version
from pathlib import Path

import yaml

from cutsignal import __version__

ROOT = Path(__file__).resolve().parents[1]
RELEASE_HEADING = re.compile(r"^## \[(?P<version>\d+\.\d+\.\d+)] - \d{4}-\d{2}-\d{2}$", re.MULTILINE)


def main() -> int:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = RELEASE_HEADING.search(changelog)
    values: dict[str, str | None] = {
        "pyproject": str(pyproject["project"]["version"]),
        "package": __version__,
        "citation": str(citation.get("version")) if isinstance(citation, dict) else None,
        "latest_changelog_release": match.group("version") if match else None,
    }
    try:
        values["installed_distribution"] = distribution_version("cutsignal")
    except PackageNotFoundError:
        values["installed_distribution"] = None
    errors = [f"{name}={value!r}" for name, value in values.items() if value != values["pyproject"]]
    result = {
        "schema_version": 1,
        "passed": not errors,
        "expected": values["pyproject"],
        "versions": values,
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
