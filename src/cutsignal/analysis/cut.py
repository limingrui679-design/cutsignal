"""CutSignal orchestration: plateau probability, sensitivity, and decisions."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from scipy.stats import norm

from cutsignal.analysis.changepoints import detect_change_points
from cutsignal.analysis.state_space import (
    ParticleFilterConfig,
    StateEstimate,
    run_particle_filter,
)
from cutsignal.models import DailyObservation


class CutAnalysisConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    filter: ParticleFilterConfig = Field(default_factory=ParticleFilterConfig)
    trend_window_days: Annotated[int, Field(ge=7, le=42)] = 14
    plateau_band_kg_per_week: Annotated[float, Field(gt=0, le=1)] = 0.10
    plateau_probability_threshold: Annotated[float, Field(ge=0.5, le=0.99)] = 0.75
    minimum_analysis_days: Annotated[int, Field(ge=7, le=60)] = 14
    minimum_decision_days: Annotated[int, Field(ge=14, le=90)] = 21
    minimum_weight_completeness: Annotated[float, Field(ge=0, le=1)] = 0.60
    minimum_intake_completeness: Annotated[float, Field(ge=0, le=1)] = 0.75
    maximum_tdee_interval_width: Annotated[float, Field(gt=0, le=3_000)] = 650


class ChangePointResult(BaseModel):
    date: date
    before_kg_per_week: float
    after_kg_per_week: float
    bic_improvement: float


class SensitivityResult(BaseModel):
    scenario: str
    final_tdee_kcal: float
    tdee_interval_width_kcal: float
    trend_kg_per_week: float
    plateau_probability: float


class DecisionResult(BaseModel):
    action: Literal["continue", "continue_observing", "collect_more_data", "consider_review"]
    confidence: Annotated[float, Field(ge=0, le=1)]
    reasons: list[str]
    next_evidence: list[str]
    scope_note: str = (
        "Decision support only; this does not prescribe calories, diagnose a condition, "
        "or replace a qualified clinician or dietitian."
    )


class CutAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_date: date
    end_date: date
    days: int
    weight_completeness: float
    intake_completeness: float
    latest_trend_kg_per_week: float
    trend_interval_kg_per_week: tuple[float, float]
    plateau_probability: float
    latest_tdee_kcal: float
    latest_tdee_interval_kcal: tuple[float, float]
    state_estimates: list[StateEstimate]
    change_points: list[ChangePointResult]
    sensitivity: list[SensitivityResult]
    sensitivity_decision_stability: float
    decision: DecisionResult
    limitations: list[str]


def _completeness(observations: list[DailyObservation], field: str) -> float:
    start = min(item.date for item in observations)
    end = max(item.date for item in observations)
    days = (end - start).days + 1
    present = len({item.date for item in observations if getattr(item, field) is not None})
    return present / days


def _rate_distribution(
    estimates: list[StateEstimate], window_days: int, band: float
) -> tuple[float, float, float, float]:
    end_index = len(estimates) - 1
    start_index = max(0, end_index - window_days)
    start = estimates[start_index]
    end = estimates[end_index]
    elapsed = max((end.date - start.date).days, 1)
    mean = (end.trend_weight_median_kg - start.trend_weight_median_kg) * 7 / elapsed
    start_sd = (start.trend_weight_upper_kg - start.trend_weight_lower_kg) / (2 * 1.96)
    end_sd = (end.trend_weight_upper_kg - end.trend_weight_lower_kg) / (2 * 1.96)
    sd = max(np.hypot(start_sd, end_sd) * 7 / elapsed, 1e-6)
    lower = float(mean - 1.96 * sd)
    upper = float(mean + 1.96 * sd)
    plateau = float(norm.cdf((band - mean) / sd) - norm.cdf((-band - mean) / sd))
    return float(mean), lower, upper, float(np.clip(plateau, 0, 1))


def _decision(
    *,
    days: int,
    weight_completeness: float,
    intake_completeness: float,
    tdee_width: float,
    rate: float,
    plateau_probability: float,
    config: CutAnalysisConfig,
) -> DecisionResult:
    reasons: list[str] = []
    next_evidence: list[str] = []
    if days < config.minimum_analysis_days:
        reasons.append(f"only {days} days are available")
        next_evidence.append(f"collect at least {config.minimum_analysis_days} days")
    if weight_completeness < config.minimum_weight_completeness:
        reasons.append(f"weight completeness is {weight_completeness:.0%}")
        next_evidence.append("increase consistent weigh-ins under similar conditions")
    if intake_completeness < config.minimum_intake_completeness:
        reasons.append(f"intake completeness is {intake_completeness:.0%}")
        next_evidence.append("improve intake-log coverage before interpreting TDEE")
    if tdee_width > config.maximum_tdee_interval_width:
        reasons.append(f"TDEE 95% interval is wide ({tdee_width:.0f} kcal/day)")
        next_evidence.append("collect more paired intake and weight observations")
    if reasons:
        confidence = max(0.25, 1 - len(reasons) * 0.15)
        return DecisionResult(
            action="collect_more_data",
            confidence=confidence,
            reasons=reasons,
            next_evidence=sorted(set(next_evidence)),
        )

    if days >= config.minimum_decision_days and plateau_probability >= config.plateau_probability_threshold:
        return DecisionResult(
            action="consider_review",
            confidence=plateau_probability,
            reasons=[
                "the posterior trend is concentrated inside the configured plateau band",
                "logging coverage and TDEE precision pass the decision gates",
            ],
            next_evidence=[
                "review adherence, recovery, medication, and measurement conditions",
                "discuss any plan change with a qualified professional when appropriate",
            ],
        )
    if rate < -config.plateau_band_kg_per_week:
        return DecisionResult(
            action="continue",
            confidence=float(1 - plateau_probability),
            reasons=["the estimated trend remains outside the plateau band"],
            next_evidence=["keep logging so the interval can be monitored"],
        )
    return DecisionResult(
        action="continue_observing",
        confidence=float(max(0.5, 1 - plateau_probability)),
        reasons=["the evidence does not yet support a stable plateau decision"],
        next_evidence=["continue the current observation window without reacting to one weigh-in"],
    )


def _hampel_weights(observations: list[DailyObservation]) -> list[DailyObservation]:
    if sum(item.weight_kg is not None for item in observations) < 7:
        return observations
    output: list[DailyObservation] = []
    for index, item in enumerate(observations):
        if item.weight_kg is None:
            output.append(item)
            continue
        nearby = [
            float(candidate.weight_kg)
            for candidate_index, candidate in enumerate(observations)
            if candidate_index != index
            and candidate.weight_kg is not None
            and abs((candidate.date - item.date).days) <= 7
        ]
        if len(nearby) < 5:
            output.append(item)
            continue
        median = float(np.median(nearby))
        mad = float(np.median(np.abs(np.asarray(nearby) - median)))
        # The absolute floor prevents an unrealistically tiny MAD from excluding
        # ordinary 0.2--0.5 kg fluid movement.
        threshold = max(4.5 * 1.4826 * mad, 0.8)
        if abs(item.weight_kg - median) > threshold:
            output.append(
                item.model_copy(
                    update={
                        "weight_kg": None,
                        "quality_flags": item.quality_flags | {"weight_hampel_excluded"},
                    }
                )
            )
        else:
            output.append(item)
    return output


def _scenario(
    name: str,
    observations: list[DailyObservation],
    filter_config: ParticleFilterConfig,
    cut_config: CutAnalysisConfig,
) -> SensitivityResult:
    estimates = run_particle_filter(observations, filter_config)
    rate, _, _, plateau = _rate_distribution(
        estimates, cut_config.trend_window_days, cut_config.plateau_band_kg_per_week
    )
    final = estimates[-1]
    return SensitivityResult(
        scenario=name,
        final_tdee_kcal=final.tdee_median_kcal,
        tdee_interval_width_kcal=final.tdee_upper_kcal - final.tdee_lower_kcal,
        trend_kg_per_week=rate,
        plateau_probability=plateau,
    )


def analyze_cut(observations: list[DailyObservation], config: CutAnalysisConfig | None = None) -> CutAnalysisResult:
    cfg = config or CutAnalysisConfig()
    ordered = sorted(observations, key=lambda item: item.date)
    estimates = run_particle_filter(ordered, cfg.filter)
    days = (estimates[-1].date - estimates[0].date).days + 1
    weight_completeness = _completeness(ordered, "weight_kg")
    intake_completeness = _completeness(ordered, "energy_intake_kcal")
    rate, rate_lower, rate_upper, plateau = _rate_distribution(
        estimates, cfg.trend_window_days, cfg.plateau_band_kg_per_week
    )
    final = estimates[-1]
    tdee_width = final.tdee_upper_kcal - final.tdee_lower_kcal

    raw_breaks = detect_change_points([item.trend_weight_median_kg for item in estimates], min_segment=10)
    change_points = [
        ChangePointResult(
            date=estimates[point.index].date,
            before_kg_per_week=point.before_slope_per_unit * 7,
            after_kg_per_week=point.after_slope_per_unit * 7,
            bic_improvement=point.bic_improvement,
        )
        for point in raw_breaks
    ]

    scenarios = [
        _scenario("recorded-intake", ordered, cfg.filter, cfg),
        _scenario(
            "intake-plus-10-percent",
            ordered,
            cfg.filter.model_copy(update={"intake_multiplier": 1.10, "random_seed": 20260821}),
            cfg,
        ),
        _scenario(
            "intake-plus-20-percent",
            ordered,
            cfg.filter.model_copy(update={"intake_multiplier": 1.20, "random_seed": 20260822}),
            cfg,
        ),
        _scenario(
            "higher-fluid-variance",
            ordered,
            cfg.filter.model_copy(update={"fluid_process_sd_kg": 0.50, "random_seed": 20260823}),
            cfg,
        ),
        _scenario(
            "weight-outliers-excluded",
            _hampel_weights(ordered),
            cfg.filter.model_copy(update={"random_seed": 20260824}),
            cfg,
        ),
    ]

    scenario_actions = [
        _decision(
            days=days,
            weight_completeness=weight_completeness,
            intake_completeness=intake_completeness,
            tdee_width=item.tdee_interval_width_kcal,
            rate=item.trend_kg_per_week,
            plateau_probability=item.plateau_probability,
            config=cfg,
        ).action
        for item in scenarios
    ]
    base_action = scenario_actions[0]
    stability = sum(action == base_action for action in scenario_actions) / len(scenario_actions)
    decision = _decision(
        days=days,
        weight_completeness=weight_completeness,
        intake_completeness=intake_completeness,
        tdee_width=tdee_width,
        rate=rate,
        plateau_probability=plateau,
        config=cfg,
    )
    if stability < 0.8 and decision.action != "collect_more_data":
        decision = DecisionResult(
            action="continue_observing",
            confidence=stability,
            reasons=["the recommended action changes under plausible logging/noise scenarios"],
            next_evidence=["improve data completeness and reassess sensitivity"],
        )

    return CutAnalysisResult(
        start_date=estimates[0].date,
        end_date=estimates[-1].date,
        days=days,
        weight_completeness=weight_completeness,
        intake_completeness=intake_completeness,
        latest_trend_kg_per_week=rate,
        trend_interval_kg_per_week=(rate_lower, rate_upper),
        plateau_probability=plateau,
        latest_tdee_kcal=final.tdee_median_kcal,
        latest_tdee_interval_kcal=(final.tdee_lower_kcal, final.tdee_upper_kcal),
        state_estimates=estimates,
        change_points=change_points,
        sensitivity=scenarios,
        sensitivity_decision_stability=stability,
        decision=decision,
        limitations=[
            "Energy-density and fluid-shift assumptions are uncertain and individualized.",
            "Logged intake can be incomplete; sensitivity scenarios do not identify the true bias.",
            "Plateau probability is a model-based summary, not a diagnosis.",
            "Medication, illness, menstrual-cycle effects, sodium, and glycogen may be unobserved.",
        ],
    )
