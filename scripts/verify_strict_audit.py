#!/usr/bin/env python3
"""Validate the arithmetic, caps, and evidence paths in the strict audit registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "registry" / "strict_audit.yml"
ALLOWED_LEVELS = {"E1", "E2", "E3", "E4", "E5", "NA"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> int:
    payload: dict[str, Any] = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    _require(payload.get("schema_version") == 1, "strict audit schema_version must be 1")
    dimensions = payload.get("dimensions", [])
    _require(len(dimensions) == 11, "strict audit must contain exactly 11 dimensions")
    _require(len({item.get("id") for item in dimensions}) == 11, "strict audit dimension ids must be unique")
    _require(sum(int(item["maximum"]) for item in dimensions) == 100, "dimension maximums must total 100")

    for state in ("baseline", "current"):
        expected = int(payload[state]["score"])
        observed = sum(int(item[state]) for item in dimensions)
        _require(observed == expected, f"{state} dimension sum {observed} != declared score {expected}")
        applicable_caps = [
            int(item["maximum_score"]) for item in payload.get("caps", []) if bool(item.get(f"{state}_applies"))
        ]
        if applicable_caps:
            _require(expected <= min(applicable_caps), f"{state} score exceeds an applicable cap")

    for item in dimensions:
        _require(item.get("evidence_level") in ALLOWED_LEVELS, f"invalid evidence level for {item.get('id')}")
        _require(0 <= int(item["baseline"]) <= int(item["maximum"]), f"invalid baseline score for {item['id']}")
        _require(0 <= int(item["current"]) <= int(item["maximum"]), f"invalid current score for {item['id']}")
        for relative in item.get("evidence", []):
            _require((ROOT / relative).is_file(), f"missing strict-audit evidence path: {relative}")

    external = payload.get("external_evidence", {})
    _require(external, "external_evidence must be explicit")
    for name, value in external.items():
        _require(value in {0, "not_observed"}, f"unsupported external evidence claim: {name}={value}")

    print(
        f"strict audit: baseline={payload['baseline']['score']}/100; "
        f"current={payload['current']['score']}/100; dimensions={len(dimensions)}; caps=valid"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
