#!/usr/bin/env python3
"""Score only versioned, machine-verifiable repository gates."""

from __future__ import annotations

import json
import math
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
    branch_coverage = float(evidence.get("coverage", {}).get("percent_branches_covered", 0))

    def passed(*names: str) -> bool:
        return fingerprint_matches and all(bool(checks.get(name, {}).get("passed")) for name in names)

    cut = e2e.get("cut", {})
    strength = e2e.get("strength", {})
    diet = e2e.get("diet", {})
    diet_gap = diet.get("mip_gap")
    diet_gap_valid = (
        isinstance(diet_gap, (int, float))
        and not isinstance(diet_gap, bool)
        and math.isfinite(float(diet_gap))
        and float(diet_gap) >= 0
    )
    report = e2e.get("report", {})
    case_payload: dict[str, Any] = {}
    case_path = ARTIFACTS / "cases.json"
    if case_path.exists():
        case_payload = json.loads(case_path.read_text(encoding="utf-8"))

    items = [
        RubricItem(
            "Automated tests and branch coverage",
            16,
            passed("pytest_coverage") and coverage >= 90 and branch_coverage >= 80,
            (
                f"pytest={passed('pytest_coverage')}; combined coverage={coverage:.2f}%; "
                f"branch-only coverage={branch_coverage:.2f}%"
            ),
        ),
        RubricItem(
            "Trajectory posterior, sensitivity, and evidence gates",
            14,
            passed("e2e", "cases")
            and cut.get("state_count") == 112
            and cut.get("sensitivity_count") == 5
            and cut.get("rate_method") == "linked_particle_trajectories"
            and bool(cut.get("unstable_signal_was_gated"))
            and bool(case_payload.get("passed"))
            and len(case_payload.get("cases", [])) == 8,
            (
                f"states={cut.get('state_count')}; scenarios={cut.get('sensitivity_count')}; "
                f"method={cut.get('rate_method')}; cases={len(case_payload.get('cases', []))}"
            ),
        ),
        RubricItem(
            "Strength uncertainty and training-load evidence",
            10,
            passed("e2e")
            and int(strength.get("exercise_count", 0)) >= 3
            and int(strength.get("session_metric_count", 0)) >= 40
            and int(strength.get("weekly_summary_count", 0)) >= 8
            and strength.get("shrinkage_method") == "uncertainty_weighted_empirical_bayes",
            (
                f"exercises={strength.get('exercise_count')}; sessions={strength.get('session_metric_count')}; "
                f"weeks={strength.get('weekly_summary_count')}; method={strength.get('shrinkage_method')}"
            ),
        ),
        RubricItem(
            "Robust diet MILP and independent validation",
            14,
            passed("e2e")
            and diet.get("days") == 7
            and bool(diet.get("baseline_stress_feasible"))
            and bool(diet.get("independent_validation"))
            and float(diet.get("minimum_slack", -1)) >= -1e-6
            and diet_gap_valid
            and int(diet.get("sensitivity_count", 0)) == 5
            and int(diet.get("pareto_count", 0)) >= 1,
            (
                f"status={diet.get('status')}; gap={diet.get('mip_gap')}; "
                f"independent_validation={diet.get('independent_validation')}"
            ),
        ),
        RubricItem(
            "Device-independent adapters and bounded inputs",
            8,
            passed("pytest_coverage")
            and all(
                (ROOT / relative).is_file()
                for relative in [
                    "src/cutsignal/importers/apple_health.py",
                    "src/cutsignal/importers/generic.py",
                    "src/cutsignal/importers/strength.py",
                    "src/cutsignal/importers/food.py",
                    "src/cutsignal/input_safety.py",
                ]
            ),
            "Apple Health, generic daily, strength, food, and shared input-limit paths are tested",
        ),
        RubricItem(
            "Privacy profiles and public-tree audit",
            10,
            fingerprint_matches
            and bool(evidence.get("privacy", {}).get("passed"))
            and bool(report.get("private_profile_labeled"))
            and bool(report.get("share_safe_minimized"))
            and (ROOT / "SECURITY.md").is_file(),
            (
                f"tree_audit={evidence.get('privacy', {}).get('passed')}; "
                f"private_labeled={report.get('private_profile_labeled')}; "
                f"share_safe_minimized={report.get('share_safe_minimized')}"
            ),
        ),
        RubricItem(
            "Static analysis and formatting",
            8,
            passed("ruff_check", "ruff_format", "mypy"),
            "Ruff lint, Ruff format check, and strict mypy",
        ),
        RubricItem(
            "CLI, casebook, and local UI startup",
            5,
            passed("cli", "ui", "cases"),
            "CLI help, eight cases, and Streamlit application-test startup",
        ),
        RubricItem(
            "Build and isolated-install reproducibility",
            10,
            passed("wheel", "fresh_install", "pip_check", "dependency_audit", "public_api")
            and any((ARTIFACTS / "dist").glob("cutsignal-*.whl"))
            and any((ARTIFACTS / "dist").glob("cutsignal-*.tar.gz")),
            "sdist+wheel, temporary-venv install, packaged resources, API import, pip check, and pip-audit",
        ),
        RubricItem(
            "Documentation, sources, and evidence-bound claims",
            5,
            fingerprint_matches
            and bool(evidence.get("documentation", {}).get("passed"))
            and passed("claims", "strict_audit", "docs_links"),
            (
                f"documentation={evidence.get('documentation', {}).get('passed')}; "
                f"claims={passed('claims')}; strict_audit={passed('strict_audit')}; "
                f"links={passed('docs_links')}"
            ),
        ),
    ]
    score = sum(item.points for item in items if item.passed)
    payload: dict[str, Any] = {
        "schema_version": 2,
        "checkout_fingerprint": current,
        "verification_fingerprint_matches": fingerprint_matches,
        "score": score,
        "maximum": 100,
        "all_gates_passed": score == 100,
        "rubric": [asdict(item) for item in items],
        "scope_note": (
            "100 means all versioned repository engineering gates passed for this checkout. It is not "
            "clinical accuracy, external validation, deployment approval, adoption, or impact."
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
