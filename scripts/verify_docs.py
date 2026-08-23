#!/usr/bin/env python3
"""Validate repository-local Markdown links and image assets."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".venv", "artifacts", "__pycache__"}
LINK_PATTERN = re.compile(r"\]\((?P<target><[^>]+>|[^)\s]+)")
IMAGE_SUFFIXES = {".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}


def main() -> int:
    errors: list[str] = []
    documents = sorted(
        path for path in ROOT.rglob("*.md") if not EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts)
    )
    links_checked = 0
    images_checked = 0
    for document in documents:
        content = document.read_text(encoding="utf-8")
        for match in LINK_PATTERN.finditer(content):
            raw_target = match.group("target").strip("<>")
            parsed = urlsplit(raw_target)
            if parsed.scheme or raw_target.startswith("#"):
                continue
            links_checked += 1
            relative_target = unquote(raw_target.split("#", 1)[0])
            target = (document.parent / relative_target).resolve()
            try:
                target.relative_to(ROOT)
            except ValueError:
                errors.append(f"{document.relative_to(ROOT)}: link escapes repository: {raw_target}")
                continue
            if not target.exists():
                errors.append(f"{document.relative_to(ROOT)}: missing target: {raw_target}")
                continue
            if target.suffix.casefold() in IMAGE_SUFFIXES:
                images_checked += 1
                if not target.is_file() or target.stat().st_size < 100:
                    errors.append(f"{document.relative_to(ROOT)}: invalid image asset: {raw_target}")

    result = {
        "schema_version": 1,
        "passed": not errors,
        "documents_checked": len(documents),
        "local_links_checked": links_checked,
        "images_checked": images_checked,
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
