#!/usr/bin/env python3
"""Validate method-reference provenance and non-transfer boundaries."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/registry/method_references.yml"
DOCUMENT = ROOT / "docs/REFERENCES.md"
REQUIRED_FIELDS = {"id", "area", "citation", "url", "use_in_cutsignal", "does_not_establish"}


def main() -> int:
    errors: list[str] = []
    payload = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    document = DOCUMENT.read_text(encoding="utf-8")
    raw_references = payload.get("references") if isinstance(payload, dict) else None
    references = raw_references if isinstance(raw_references, list) else []
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        errors.append("unsupported method-reference schema")
    if not isinstance(payload, dict) or not payload.get("accessed"):
        errors.append("missing access date")
    if len(references) < 8:
        errors.append("at least eight method references are required")

    ids: set[str] = set()
    for raw in references:
        if not isinstance(raw, dict):
            errors.append("reference is not a mapping")
            continue
        missing = REQUIRED_FIELDS.difference(raw)
        reference_id = str(raw.get("id", ""))
        if missing:
            errors.append(f"{reference_id or '<missing-id>'}: missing {sorted(missing)}")
        if not reference_id or reference_id in ids:
            errors.append(f"missing or duplicate reference id: {reference_id!r}")
        ids.add(reference_id)
        parsed = urlsplit(str(raw.get("url", "")))
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"{reference_id}: URL must be an absolute HTTPS URL")
        if f"`{reference_id}`" not in document:
            errors.append(f"{reference_id}: missing from docs/REFERENCES.md")
        if len(str(raw.get("does_not_establish", ""))) < 30:
            errors.append(f"{reference_id}: evidence boundary is too short")

    result = {
        "schema_version": 1,
        "passed": not errors,
        "reference_count": len(references),
        "areas": sorted({str(item.get("area")) for item in references if isinstance(item, dict)}),
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
