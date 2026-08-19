#!/usr/bin/env python3
"""Run a deterministic, full-width synthetic workflow and assert product invariants."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cutsignal.analysis.cut import CutAnalysisConfig
from cutsignal.analysis.state_space import ParticleFilterConfig
from cutsignal.io import write_jsonl
from cutsignal.pipeline import run_pipeline
from cutsignal.reporting.html import render_html_report
from cutsignal.synthetic import (
    demo_constraints,
    generate_daily_demo,
    generate_food_demo,
    generate_strength_demo,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/e2e"))
    parser.add_argument("--optimizer-seconds", type=float, default=3.0)
    parser.add_argument("--pareto-seconds", type=float, default=1.5)
    args = parser.parse_args()

    output: Path = args.output
    output.mkdir(parents=True, exist_ok=True)
    daily = generate_daily_demo()
    strength = generate_strength_demo(daily)
    foods = generate_food_demo()
    constraints = demo_constraints()
    data_dir = output / "data"
    write_jsonl(daily, data_dir / "daily.synthetic.jsonl")
    write_jsonl(strength, data_dir / "strength.synthetic.jsonl")
    write_jsonl(foods, data_dir / "foods.synthetic.jsonl")

    result = run_pipeline(
        daily,
        strength,
        foods,
        constraints,
        cut_config=CutAnalysisConfig(filter=ParticleFilterConfig(particles=750)),
        diet_time_limit_seconds=args.optimizer_seconds,
        pareto_time_limit_seconds=args.pareto_seconds,
    )
    report = render_html_report(result, output / "report.html")
    report_json = report.with_suffix(".json")
    html = report.read_text(encoding="utf-8")
    serialized = report_json.read_text(encoding="utf-8")

    assert len(result.cut.state_estimates) == 112
    assert len(result.cut.sensitivity) == 5
    assert result.cut.sensitivity_decision_stability >= 0.8
    assert len(result.strength.exercises) == 3
    assert len(result.strength.session_metrics) >= 40
    assert len(result.diet.daily) == 7
    assert min(result.diet.constraint_slack.values()) >= -1e-6
    assert result.diet.sensitivity[0].feasible
    assert result.diet.mip_gap is not None and result.diet.mip_gap <= 0.35
    assert result.diet_pareto
    assert result.integrated_decision.action == "validate_food_data"
    assert "source_id" not in html and "source_id" not in serialized
    assert "demo-000" not in html and "CutSignal synthetic generator" not in html

    summary = {
        "passed": True,
        "cut": {
            "days": result.cut.days,
            "state_count": len(result.cut.state_estimates),
            "sensitivity_count": len(result.cut.sensitivity),
            "change_point_count": len(result.cut.change_points),
            "decision": result.cut.decision.action,
            "decision_stability": result.cut.sensitivity_decision_stability,
        },
        "strength": {
            "exercise_count": len(result.strength.exercises),
            "session_metric_count": len(result.strength.session_metrics),
            "decision": result.strength.decision.action,
            "pareto_count": len(result.strength.pareto_frontier),
        },
        "diet": {
            "days": len(result.diet.daily),
            "status": result.diet.status,
            "mip_gap": result.diet.mip_gap,
            "minimum_slack": min(result.diet.constraint_slack.values()),
            "sensitivity_count": len(result.diet.sensitivity),
            "baseline_stress_feasible": result.diet.sensitivity[0].feasible,
            "pareto_count": len(result.diet_pareto),
        },
        "integration": {"decision": result.integrated_decision.action},
        "report": {
            "redacted": "source_id" not in html and "source_id" not in serialized,
            "html_sha256": _sha256(report),
            "json_sha256": _sha256(report_json),
        },
    }
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
