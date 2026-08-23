#!/usr/bin/env python3
"""Validate source roles, versions, license boundaries, and local evidence."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/registry/sources.yml"
REQUIRED_FIELDS = {
    "id",
    "role",
    "bundled",
    "version_or_snapshot",
    "license_or_terms",
    "caveat",
    "evidence",
}


def main() -> int:
    payload = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    errors: list[str] = []
    raw_sources = payload.get("sources") if isinstance(payload, dict) else None
    sources = raw_sources if isinstance(raw_sources, list) else []
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        errors.append("unsupported source-registry schema")
    if not isinstance(payload, dict) or not payload.get("accessed"):
        errors.append("missing registry access date")
    if len(sources) < 5:
        errors.append("at least five declared sources are required")

    ids: set[str] = set()
    for raw in sources:
        if not isinstance(raw, dict):
            errors.append("source is not a mapping")
            continue
        source_id = str(raw.get("id", ""))
        missing = REQUIRED_FIELDS.difference(raw)
        if missing:
            errors.append(f"{source_id or '<missing-id>'}: missing {sorted(missing)}")
        if not source_id or source_id in ids:
            errors.append(f"missing or duplicate source id: {source_id!r}")
        ids.add(source_id)
        if not isinstance(raw.get("bundled"), bool):
            errors.append(f"{source_id}: bundled must be boolean")
        homepage = raw.get("homepage")
        if homepage is not None:
            parsed = urlsplit(str(homepage))
            if parsed.scheme != "https" or not parsed.netloc:
                errors.append(f"{source_id}: homepage must be an absolute HTTPS URL")
        evidence = raw.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{source_id}: evidence list is empty")
        else:
            for relative in evidence:
                if not (ROOT / str(relative)).is_file():
                    errors.append(f"{source_id}: missing evidence path {relative}")
        if len(str(raw.get("caveat", ""))) < 20:
            errors.append(f"{source_id}: caveat is too short")

    result = {
        "schema_version": 1,
        "passed": not errors,
        "source_count": len(sources),
        "bundled_count": sum(bool(item.get("bundled")) for item in sources if isinstance(item, dict)),
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
