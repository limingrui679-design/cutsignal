"""Executable, evidence-bounded casebook for product and method verification."""

from __future__ import annotations

import math
import tempfile
import time
from datetime import date, timedelta
from importlib.resources import files
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

from cutsignal.analysis.cut import CutAnalysisConfig, analyze_cut
from cutsignal.analysis.state_space import ParticleFilterConfig
from cutsignal.analysis.strength import StrengthAnalysisConfig, analyze_strength
from cutsignal.exceptions import CutSignalError
from cutsignal.importers.apple_health import import_apple_health
from cutsignal.models import SourceRef, StrengthSet
from cutsignal.optimization.diet import optimize_weekly_plan
from cutsignal.synthetic import (
    demo_constraints,
    generate_daily_demo,
    generate_food_demo,
    generate_strength_demo,
)

CASE_PARTICLES = 500
CASE_RANDOM_SEED = 20260820


class CaseSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    domain: Literal["fat_loss", "strength", "food_optimization", "data_engineering"]
    evidence_type: Literal["deterministic_synthetic_fixture"]
    decision_question: str
    capabilities: list[str]
    expected_gate: str
    limitations: str


class CaseRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    passed: bool
    evidence_type: str
    configuration: dict[str, object]
    assertions: dict[str, bool]
    observed: dict[str, object]
    duration_seconds: float
    limitations: str


def list_cases() -> list[CaseSpec]:
    """Load and validate the packaged case catalog."""
    resource = files("cutsignal").joinpath("resources/cases.yml")
    payload = yaml.safe_load(resource.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("unsupported case catalog schema")
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list):
        raise ValueError("case catalog must contain a cases list")
    cases = [CaseSpec.model_validate(item) for item in raw_cases]
    if len({item.id for item in cases}) != len(cases):
        raise ValueError("case ids must be unique")
    return cases


def get_case(case_id: str) -> CaseSpec:
    for case in list_cases():
        if case.id == case_id:
            return case
    available = ", ".join(item.id for item in list_cases())
    raise ValueError(f"unknown case {case_id!r}; available: {available}")


def _cut_config() -> CutAnalysisConfig:
    return CutAnalysisConfig(filter=ParticleFilterConfig(particles=CASE_PARTICLES, random_seed=CASE_RANDOM_SEED))


def _fatigue_sets() -> list[StrengthSet]:
    start = date(2026, 1, 1)
    source = SourceRef(provider="CutSignal synthetic casebook", record_type="strength-fatigue")
    rows: list[StrengthSet] = []
    for session in range(12):
        load = 105 - session * 1.8
        rpe = min(10.0, 7.0 + session * 0.25)
        set_count = 4 if session < 9 else 2
        for set_number in range(set_count):
            rows.append(
                StrengthSet(
                    date=start + timedelta(days=session * 4),
                    exercise="Synthetic Back Squat",
                    weight_kg=load - set_number,
                    reps=5,
                    rpe=rpe,
                    source=source,
                )
            )
    return rows


def _apple_overlap_case() -> tuple[float | None, set[str]]:
    document = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
  <Record type="HKQuantityTypeIdentifierStepCount" sourceName="Synthetic Phone" device="Phone"
    unit="count" value="6000" startDate="2026-01-01 08:00:00 +0000" endDate="2026-01-01 20:00:00 +0000"/>
  <Record type="HKQuantityTypeIdentifierStepCount" sourceName="Synthetic Watch" device="Watch"
    unit="count" value="8000" startDate="2026-01-01 08:00:00 +0000" endDate="2026-01-01 20:00:00 +0000"/>
</HealthData>
"""
    with tempfile.TemporaryDirectory(prefix="cutsignal-case-") as directory:
        source = Path(directory) / "synthetic-health.xml"
        source.write_text(document, encoding="utf-8")
        observation = import_apple_health(source)[0]
    return observation.steps, observation.quality_flags


def run_case(
    case_id: str,
    *,
    optimizer_seconds: float = 2.0,
) -> CaseRunResult:
    """Execute one deterministic case and expose every assertion."""
    spec = get_case(case_id)
    started = time.monotonic()
    assertions: dict[str, bool]
    observed: dict[str, object]
    configuration: dict[str, object]

    if case_id == "plateau-sensitivity-gate":
        configuration = {"particles": CASE_PARTICLES, "random_seed": CASE_RANDOM_SEED}
        cut_result = analyze_cut(generate_daily_demo(), _cut_config())
        assertions = {
            "linked_particle_rate": cut_result.rate_posterior_method == "linked_particle_trajectories",
            "five_sensitivity_scenarios": len(cut_result.sensitivity) == 5,
            "fixture_is_sensitivity_unstable": cut_result.sensitivity_decision_stability < 0.8,
            "unstable_signal_downgrades": cut_result.decision.action == "continue_observing",
        }
        observed = {
            "decision": cut_result.decision.action,
            "sensitivity_stability": cut_result.sensitivity_decision_stability,
            "plateau_probability": cut_result.plateau_probability,
        }
    elif case_id == "missing-intake-abstain":
        configuration = {"particles": CASE_PARTICLES, "random_seed": CASE_RANDOM_SEED}
        daily = [
            item.model_copy(update={"energy_intake_kcal": None}) if index % 2 == 0 else item
            for index, item in enumerate(generate_daily_demo())
        ]
        missing_result = analyze_cut(daily, _cut_config())
        assertions = {
            "coverage_below_gate": missing_result.intake_completeness < 0.75,
            "abstains": missing_result.decision.action == "collect_more_data",
        }
        observed = {
            "decision": missing_result.decision.action,
            "intake_completeness": missing_result.intake_completeness,
        }
    elif case_id == "water-spike-resilience":
        configuration = {"particles": CASE_PARTICLES, "random_seed": CASE_RANDOM_SEED}
        daily = generate_daily_demo()
        baseline = analyze_cut(daily, _cut_config())
        shocked = [
            item.model_copy(update={"weight_kg": item.weight_kg + 3.5 if item.weight_kg is not None else None})
            if index == 100
            else item
            for index, item in enumerate(daily)
        ]
        stressed = analyze_cut(shocked, _cut_config())
        rate_shift = abs(stressed.latest_trend_kg_per_week - baseline.latest_trend_kg_per_week)
        assertions = {
            "action_unchanged": stressed.decision.action == baseline.decision.action,
            "bounded_rate_shift": rate_shift < 0.15,
        }
        observed = {
            "baseline_action": baseline.decision.action,
            "stressed_action": stressed.decision.action,
            "absolute_rate_shift_kg_per_week": rate_shift,
        }
    elif case_id == "strength-fatigue-gate":
        strength_config = StrengthAnalysisConfig(
            min_sessions_per_exercise=4,
            hierarchy_prior_sessions=0.5,
            material_decline_pct_per_week=-0.2,
        )
        configuration = strength_config.model_dump(mode="json")
        fatigue_result = analyze_strength(
            _fatigue_sets(),
            config=strength_config,
        )
        exercise = fatigue_result.exercises[0]
        assertions = {
            "fatigue_signal": exercise.fatigue_signal,
            "high_decline_probability": exercise.decline_probability >= 0.80,
            "recovery_first": fatigue_result.decision.action == "review_recovery",
        }
        observed = {
            "decision": fatigue_result.decision.action,
            "decline_probability": exercise.decline_probability,
            "volume_change_pct": exercise.volume_change_pct,
            "rpe_change": exercise.rpe_change,
        }
    elif case_id == "stable-strength-cut":
        strength_config = StrengthAnalysisConfig()
        configuration = strength_config.model_dump(mode="json")
        daily = generate_daily_demo()
        stable_result = analyze_strength(generate_strength_demo(daily), daily, strength_config)
        assertions = {
            "weekly_training_summary": bool(stable_result.weekly_summaries),
            "no_high_probability_decline": all(item.decline_probability < 0.80 for item in stable_result.exercises),
            "stable_gate": stable_result.decision.action == "stable",
        }
        observed = {
            "decision": stable_result.decision.action,
            "exercise_count": len(stable_result.exercises),
            "week_count": len(stable_result.weekly_summaries),
        }
    elif case_id == "budget-shock":
        configuration = {"optimizer_time_limit_seconds": optimizer_seconds}
        budget_result = optimize_weekly_plan(
            generate_food_demo(),
            demo_constraints(),
            time_limit_seconds=optimizer_seconds,
        )
        assertions = {
            "independent_validation": budget_result.independent_validation.feasible,
            "modeled_bounds_feasible": budget_result.sensitivity[0].feasible,
            "stronger_shock_visible": any(not item.feasible for item in budget_result.sensitivity[1:]),
            "mip_gap_disclosed": budget_result.mip_gap is not None,
            "mip_gap_finite_nonnegative": (
                budget_result.mip_gap is not None
                and math.isfinite(budget_result.mip_gap)
                and budget_result.mip_gap >= 0
            ),
        }
        observed = {
            "solver_status": budget_result.status,
            "mip_gap": budget_result.mip_gap,
            "failed_stress_scenarios": [item.scenario for item in budget_result.sensitivity if not item.feasible],
        }
    elif case_id == "vegetarian-allergen-plan":
        foods = generate_food_demo()
        constraints = demo_constraints().model_copy(
            update={
                "days": 3,
                "max_days_per_food": 3,
                "required_tags": {"vegetarian"},
                "excluded_allergens": {"soy"},
                "min_unique_foods": 5,
                "budget_max_per_day": 17,
                "protein_min_g": 100,
            }
        )
        configuration = {
            "optimizer_time_limit_seconds": optimizer_seconds,
            "constraints": constraints.model_dump(mode="json"),
        }
        vegetarian_result = optimize_weekly_plan(
            foods,
            constraints,
            time_limit_seconds=optimizer_seconds,
        )
        selected = {entry.food_id for entry in vegetarian_result.entries}
        food_lookup = {food.food_id: food for food in foods}
        assertions = {
            "independent_validation": vegetarian_result.independent_validation.feasible,
            "soy_excluded": all("soy" not in food_lookup[food_id].allergens for food_id in selected),
            "vegetarian_only": all("vegetarian" in food_lookup[food_id].tags for food_id in selected),
            "mip_gap_disclosed": vegetarian_result.mip_gap is not None,
            "mip_gap_finite_nonnegative": (
                vegetarian_result.mip_gap is not None
                and math.isfinite(vegetarian_result.mip_gap)
                and vegetarian_result.mip_gap >= 0
            ),
        }
        observed = {
            "solver_status": vegetarian_result.status,
            "mip_gap": vegetarian_result.mip_gap,
            "selected_food_count": len(selected),
        }
    elif case_id == "device-overlap-reconciliation":
        configuration = {"reconciliation_rule": "maximum_source_day_total"}
        steps, flags = _apple_overlap_case()
        assertions = {
            "not_blindly_summed": steps == 8_000,
            "reconciliation_flag": "steps_multi_source_reconciled" in flags,
        }
        observed = {"steps": steps, "quality_flags": sorted(flags)}
    else:  # pragma: no cover - catalog and dispatch are validated together
        raise ValueError(f"case {case_id!r} has no executable implementation")

    return CaseRunResult(
        case_id=case_id,
        passed=all(assertions.values()),
        evidence_type=spec.evidence_type,
        configuration=configuration,
        assertions=assertions,
        observed=observed,
        duration_seconds=round(time.monotonic() - started, 3),
        limitations=spec.limitations,
    )


def verify_cases(
    *,
    optimizer_seconds: float = 2.0,
) -> list[CaseRunResult]:
    """Execute every catalog case and retain expected domain failures as evidence."""
    results: list[CaseRunResult] = []
    for case in list_cases():
        started = time.monotonic()
        try:
            results.append(run_case(case.id, optimizer_seconds=optimizer_seconds))
        except CutSignalError as exc:
            results.append(
                CaseRunResult(
                    case_id=case.id,
                    passed=False,
                    evidence_type=case.evidence_type,
                    configuration={"optimizer_time_limit_seconds": optimizer_seconds},
                    assertions={"case_execution": False},
                    observed={"error_type": type(exc).__name__, "error": str(exc)},
                    duration_seconds=round(time.monotonic() - started, 3),
                    limitations=case.limitations,
                )
            )
    return results
