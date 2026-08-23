#!/usr/bin/env python3
"""Validate that every public capability claim is bound to repository evidence."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_MATURITY = {"implemented_and_locally_tested", "not_established"}


def main() -> int:
    registry = ROOT / "data/registry/claims.yml"
    payload = yaml.safe_load(registry.read_text(encoding="utf-8"))
    errors: list[str] = []
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        errors.append("unsupported claims schema")
        claims: list[object] = []
    else:
        raw_claims = payload.get("claims")
        claims = raw_claims if isinstance(raw_claims, list) else []
        if not claims:
            errors.append("claims list is empty")
    ids: set[str] = set()
    for raw in claims:
        if not isinstance(raw, dict):
            errors.append("claim is not a mapping")
            continue
        claim_id = str(raw.get("id", ""))
        if not claim_id or claim_id in ids:
            errors.append(f"missing or duplicate claim id: {claim_id!r}")
        ids.add(claim_id)
        if raw.get("maturity") not in ALLOWED_MATURITY:
            errors.append(f"{claim_id}: unsupported maturity")
        evidence = raw.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{claim_id}: missing evidence")
            continue
        for relative in evidence:
            path = ROOT / str(relative)
            if not path.is_file():
                errors.append(f"{claim_id}: evidence path missing: {relative}")
        exclusions = raw.get("does_not_establish")
        if not isinstance(exclusions, list) or not exclusions:
            errors.append(f"{claim_id}: missing evidence boundary")

    result = {
        "schema_version": 1,
        "passed": not errors,
        "claim_count": len(claims),
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
