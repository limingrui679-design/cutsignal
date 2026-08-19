#!/usr/bin/env python3
"""Score only machine-verifiable gates from the current checkout evidence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from verify_project import ARTIFACTS, ROOT, checkout_fingerprint


@dataclass(frozen=True)
class RubricItem:
    name: str
    points: int
    passed: bool
    evidence: str


def main() -> int:
    verification_path = ARTIFACTS / "verification.json"
    if not verification_path.exists():
        raise SystemExit("run scripts/verify_project.py first")
    evidence: dict[str, Any] = json.loads(verification_path.read_text(encoding="utf-8"))
    current = checkout_fingerprint()
    fingerprint_matches = evidence.get("checkout_fingerprint") == current
    checks = evidence.get("checks", {})
    e2e = evidence.get("e2e", {})
    coverage = float(evidence.get("coverage", {}).get("percent_covered", 0))

    def passed(*names: str) -> bool:
        return fingerprint_matches and all(bool(checks.get(name, {}).get("passed")) for name in names)

    cut = e2e.get("cut", {})
    strength = e2e.get("strength", {})
    diet = e2e.get("diet", {})
    report = e2e.get("report", {})
    required_adapters = [
        ROOT / "src/cutsignal/importers/apple_health.py",
        ROOT / "src/cutsignal/importers/generic.py",
        ROOT / "src/cutsignal/importers/strength.py",
        ROOT / "src/cutsignal/importers/food.py",
    ]
    items = [
        RubricItem(
            "Automated core tests and branch coverage",
            20,
            passed("pytest_coverage") and coverage >= 90,
            f"pytest={passed('pytest_coverage')}; core coverage={coverage:.2f}%",
        ),
        RubricItem(
            "CutSignal uncertainty and sensitivity",
            12,
            passed("e2e")
            and cut.get("state_count") == 112
            and cut.get("sensitivity_count") == 5
            and float(cut.get("decision_stability", 0)) >= 0.8,
            (
                f"states={cut.get('state_count')}; scenarios={cut.get('sensitivity_count')}; "
                f"stability={cut.get('decision_stability')}"
            ),
        ),
        RubricItem(
            "LeanGuard repeated-session evidence",
            8,
            passed("e2e")
            and int(strength.get("exercise_count", 0)) >= 3
            and int(strength.get("session_metric_count", 0)) >= 40
            and int(strength.get("pareto_count", 0)) >= 1,
            f"exercises={strength.get('exercise_count')}; sessions={strength.get('session_metric_count')}",
        ),
        RubricItem(
            "BudgetCut robust weekly MILP",
            15,
            passed("e2e")
            and diet.get("days") == 7
            and bool(diet.get("baseline_stress_feasible"))
            and float(diet.get("minimum_slack", -1)) >= -1e-6
            and diet.get("mip_gap") is not None
            and float(diet["mip_gap"]) <= 0.35
            and int(diet.get("sensitivity_count", 0)) == 5
            and int(diet.get("pareto_count", 0)) >= 1,
            f"status={diet.get('status')}; gap={diet.get('mip_gap')}; min_slack={diet.get('minimum_slack')}",
        ),
        RubricItem(
            "Device-independent inputs and provenance",
            10,
            passed("pytest_coverage")
            and all(path.is_file() for path in required_adapters)
            and (ROOT / "docs/DEVICE_ADAPTERS.md").is_file(),
            "Apple Health, generic daily CSV, strength CSV, and food adapters tested",
        ),
        RubricItem(
            "Privacy and report redaction",
            10,
            fingerprint_matches
            and bool(evidence.get("privacy", {}).get("passed"))
            and bool(report.get("redacted"))
            and (ROOT / "SECURITY.md").is_file(),
            f"tree_audit={evidence.get('privacy', {}).get('passed')}; report_redacted={report.get('redacted')}",
        ),
        RubricItem(
            "Static analysis and formatting",
            10,
            passed("ruff_check", "ruff_format", "mypy"),
            "Ruff lint, Ruff format check, and strict mypy",
        ),
        RubricItem(
            "CLI and local UI startup",
            5,
            passed("cli", "ui"),
            "CLI help and Streamlit application-test startup",
        ),
        RubricItem(
            "Installable wheel",
            5,
            passed("wheel") and any((ARTIFACTS / "dist").glob("cutsignal-*.whl")),
            "PEP 517 wheel build",
        ),
        RubricItem(
            "Documentation and source registry",
            5,
            fingerprint_matches and bool(evidence.get("documentation", {}).get("passed")),
            "architecture, methods, adapters, sources, privacy, limitations, validation, contribution, security",
        ),
    ]
    score = sum(item.points for item in items if item.passed)
    payload = {
        "schema_version": 1,
        "checkout_fingerprint": current,
        "verification_fingerprint_matches": fingerprint_matches,
        "score": score,
        "maximum": 100,
        "all_gates_passed": score == 100,
        "rubric": [asdict(item) for item in items],
        "scope_note": (
            "100 means all repository engineering gates passed; it is not clinical accuracy or deployment approval."
        ),
    }
    score_path = ARTIFACTS / "score.json"
    score_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    markdown = ["# CutSignal verification score", "", f"**{score}/100**", ""]
    markdown.extend(
        f"- {'PASS' if item.passed else 'FAIL'} — {item.name} ({item.points}): {item.evidence}" for item in items
    )
    markdown.extend(["", payload["scope_note"], ""])
    (ARTIFACTS / "SCORECARD.md").write_text("\n".join(markdown), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if score == 100 else 1


if __name__ == "__main__":
    raise SystemExit(main())
