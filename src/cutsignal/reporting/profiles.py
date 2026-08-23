"""Explicit report profiles with different disclosure surfaces."""

from __future__ import annotations

from typing import Literal

from cutsignal.pipeline import PipelineResult

ReportProfile = Literal["private", "share-safe"]


def _bucket(value: float, *, low: float, high: float) -> str:
    if value < low:
        return "low"
    if value < high:
        return "moderate"
    return "high"


def build_report_payload(result: PipelineResult, profile: ReportProfile) -> dict[str, object]:
    """Build an explicit JSON payload for a private or minimized report.

    ``private`` preserves the full analytical result, including dates and daily
    observed/latent health series. ``share-safe`` removes dates, daily states,
    exact weights/TDEE/intake values, exercise and food names, menu entries, and
    exact constraint values. It is data-minimized, not an anonymity guarantee.
    """
    if profile not in {"private", "share-safe"}:
        raise ValueError(f"unsupported report profile: {profile!r}")
    if profile == "private":
        return {
            "schema_version": 2,
            "report_profile": "private",
            "privacy_notice": (
                "Contains sensitive dates and health, training, and food-plan metrics. "
                "Keep local unless every field has been reviewed for the intended audience."
            ),
            "result": result.model_dump(mode="json"),
        }

    return {
        "schema_version": 2,
        "report_profile": "share-safe",
        "privacy_notice": (
            "Data-minimized output. Derived categories can still be sensitive and do not "
            "guarantee anonymity. Review before sharing."
        ),
        "integrated_decision": {
            "action": result.integrated_decision.action,
            "evidence_order": result.integrated_decision.evidence_order,
            "scope_note": result.integrated_decision.scope_note,
        },
        "data_adequacy": {
            "observation_window": _bucket(float(result.cut.days), low=21, high=56),
            "weight_coverage": _bucket(result.cut.weight_completeness, low=0.60, high=0.85),
            "intake_coverage": _bucket(result.cut.intake_completeness, low=0.75, high=0.90),
            "strength_history": _bucket(float(len(result.strength.session_metrics)), low=8, high=24),
            "food_data_quality": _bucket(result.diet.weighted_data_quality, low=0.75, high=0.90),
        },
        "fat_loss_signal": {
            "decision": result.cut.decision.action,
            "trend_direction": (
                "decreasing"
                if result.cut.latest_trend_kg_per_week < -0.10
                else "increasing"
                if result.cut.latest_trend_kg_per_week > 0.10
                else "inside_plateau_band"
            ),
            "plateau_probability": _bucket(result.cut.plateau_probability, low=0.50, high=0.75),
            "sensitivity_stability": _bucket(result.cut.sensitivity_decision_stability, low=0.60, high=0.80),
            "rate_method": result.cut.rate_posterior_method,
        },
        "strength_signal": {
            "decision": result.strength.decision.action,
            "exercise_count": len(result.strength.exercises),
            "fatigue_signals_present": any(item.fatigue_signal for item in result.strength.exercises),
            "high_decline_probability_present": any(
                item.decline_probability >= 0.80 for item in result.strength.exercises
            ),
        },
        "food_plan_signal": {
            "solver_status": result.diet.status,
            "mip_gap_disclosed": result.diet.mip_gap is not None,
            "mip_gap_category": (
                "unavailable"
                if result.diet.mip_gap is None
                else "under_1_percent"
                if result.diet.mip_gap <= 0.01
                else "1_to_20_percent"
                if result.diet.mip_gap <= 0.20
                else "over_20_percent"
            ),
            "stress_scenarios": [
                {"scenario": item.scenario, "feasible": item.feasible} for item in result.diet.sensitivity
            ],
            "sampled_trade_off_profiles": [item.label for item in result.diet_pareto],
            "failed_trade_off_profiles": [item.label for item in result.diet_tradeoff_failures],
        },
        "omitted_fields": [
            "calendar_dates",
            "daily_observed_weight_and_intake",
            "daily_latent_weight_and_tdee",
            "exact_health_metrics",
            "exercise_names_and_session_metrics",
            "food_names_and_menu_entries",
            "source_and_device_identifiers",
        ],
    }
