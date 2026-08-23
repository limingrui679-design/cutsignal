#!/usr/bin/env python3
"""Validate the independent deep-audit rubric, benchmark mix, and evidence paths."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "registry" / "deep_audit.yml"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> int:
    payload: dict[str, Any] = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    _require(payload.get("schema_version") == 1, "deep audit schema_version must be 1")
    _require(payload.get("rubric_origin") == "independently_defined_for_this_audit", "rubric origin missing")
    dimensions = payload.get("dimensions", [])
    _require(len(dimensions) == 12, "deep audit must contain exactly 12 dimensions")
    _require(len({item.get("id") for item in dimensions}) == 12, "deep audit dimension ids must be unique")
    _require(sum(int(item["maximum"]) for item in dimensions) == 100, "dimension maximums must total 100")
    for state in ("baseline", "current"):
        declared = int(payload[state]["score"])
        observed = sum(int(item[state]) for item in dimensions)
        _require(observed == declared, f"{state} score {observed} != declared {declared}")
        caps = [int(item["maximum_score"]) for item in payload.get("caps", []) if item.get(f"{state}_applies")]
        if caps:
            _require(declared <= min(caps), f"{state} score exceeds an applicable cap")
    for item in dimensions:
        maximum = int(item["maximum"])
        _require(0 <= int(item["baseline"]) <= maximum, f"invalid baseline score for {item['id']}")
        _require(0 <= int(item["current"]) <= maximum, f"invalid current score for {item['id']}")
        for relative in item.get("evidence", []):
            _require((ROOT / relative).is_file(), f"missing dimension evidence: {relative}")

    benchmark = payload.get("benchmark_review", {})
    _require(benchmark.get("accessed") == "2026-08-24", "benchmark access date is missing")
    projects = benchmark.get("projects", [])
    _require(len(projects) == 12, "benchmark registry must contain 12 projects")
    counts = Counter(item.get("category") for item in projects)
    _require(counts == {"direct": 4, "adjacent": 5, "exemplar": 3}, f"invalid benchmark mix: {counts}")
    for item in projects:
        _require(all(item.get(field) for field in ("name", "reference", "url")), "incomplete benchmark record")

    findings = payload.get("findings", [])
    _require(len({item.get("id") for item in findings}) == len(findings), "finding ids must be unique")
    closed_status = "fixed_and_full_regression_verified"
    open_blockers = [
        item for item in findings if item.get("priority") in {"P0", "P1"} and item.get("status") != closed_status
    ]
    _require(not open_blockers, f"unresolved P0/P1 findings: {[item.get('id') for item in open_blockers]}")
    for item in findings:
        for relative in item.get("evidence", []):
            _require((ROOT / relative).is_file(), f"missing finding evidence: {relative}")

    external = payload.get("external_evidence", {})
    _require(external, "external evidence boundary must be explicit")
    for name, value in external.items():
        _require(value in {0, "not_observed"}, f"unsupported external evidence claim: {name}={value}")
    print(
        f"deep audit: baseline={payload['baseline']['score']}/100; "
        f"current={payload['current']['score']}/100; benchmarks={dict(counts)}; "
        f"findings={len(findings)}; open_P0_P1=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
