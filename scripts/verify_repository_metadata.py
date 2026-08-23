#!/usr/bin/env python3
"""Require one verified public-repository identity across metadata and support surfaces."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/limingrui679-design/cutsignal"


def main() -> int:
    errors: list[str] = []
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    citation: dict[str, Any] = yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    issue_config: dict[str, Any] = yaml.safe_load(
        (ROOT / ".github/ISSUE_TEMPLATE/config.yml").read_text(encoding="utf-8")
    )

    expected_urls = {
        "Homepage": REPOSITORY,
        "Repository": REPOSITORY,
        "Issues": f"{REPOSITORY}/issues",
        "Documentation": f"{REPOSITORY}/tree/main/docs",
    }
    project_urls = pyproject.get("project", {}).get("urls", {})
    for label, expected in expected_urls.items():
        if project_urls.get(label) != expected:
            errors.append(f"pyproject {label} URL does not match {expected}")
    if citation.get("repository-code") != REPOSITORY:
        errors.append("CITATION.cff repository-code does not match the public repository")

    required_text = {
        "README.md": [
            f"git clone {REPOSITORY}.git",
            f"{REPOSITORY}/actions/workflows/ci.yml",
            f"{REPOSITORY}/actions/workflows/security.yml",
        ],
        "SECURITY.md": [f"{REPOSITORY}/security/advisories/new"],
        "SUPPORT.md": [f"{REPOSITORY}/issues/new/choose", f"{REPOSITORY}/security/advisories/new"],
    }
    for relative, fragments in required_text.items():
        document = (ROOT / relative).read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in document:
                errors.append(f"{relative} is missing {fragment}")

    contact_urls = {str(item.get("url")) for item in issue_config.get("contact_links", []) if isinstance(item, dict)}
    for expected in (f"{REPOSITORY}/security/advisories/new", f"{REPOSITORY}/blob/main/SUPPORT.md"):
        if expected not in contact_urls:
            errors.append(f"issue-template contacts are missing {expected}")
    if issue_config.get("blank_issues_enabled") is not False:
        errors.append("blank GitHub issues must be disabled in favor of the typed templates")

    result = {
        "schema_version": 1,
        "passed": not errors,
        "repository": REPOSITORY,
        "surfaces_checked": 6,
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
