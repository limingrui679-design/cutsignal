"""LeanGuard: uncertainty-aware strength retention during a weight-loss phase."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Annotated, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from scipy.stats import norm

from cutsignal.analysis.changepoints import detect_change_points
from cutsignal.models import DailyObservation, StrengthSet


class StrengthAnalysisConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_reps_for_e1rm: Annotated[int, Field(ge=3, le=30)] = 15
    min_sessions_per_exercise: Annotated[int, Field(ge=2, le=20)] = 4
    hierarchy_prior_sessions: Annotated[float, Field(gt=0, le=50)] = 6.0
    material_decline_pct_per_week: Annotated[float, Field(ge=-5, le=0)] = -0.5
    fatigue_recent_sessions: Annotated[int, Field(ge=2, le=10)] = 3
    allometric_exponent: Annotated[float, Field(gt=0, le=1.5)] = 0.67


class SessionMetric(BaseModel):
    date: date
    exercise: str
    e1rm_kg: float
    e1rm_uncertainty_pct: float
    volume_kg: float
    working_sets: int
    mean_rpe: float | None
    bodyweight_kg: float | None


class ExerciseStrengthResult(BaseModel):
    exercise: str
    sessions: int
    span_days: int
    baseline_e1rm_kg: float
    latest_e1rm_kg: float
    e1rm_change_pct: float
    raw_slope_pct_per_week: float
    hierarchical_slope_pct_per_week: float
    slope_interval_pct_per_week: tuple[float, float]
    decline_probability: Annotated[float, Field(ge=0, le=1)]
    relative_strength_change_pct: float | None
    retention_score: float
    fatigue_signal: bool
    change_point_dates: list[date]
    quality_flags: set[str] = Field(default_factory=set)


class ParetoPoint(BaseModel):
    week: date
    bodyweight_kg: float
    strength_index: float


class StrengthDecision(BaseModel):
    action: Literal["stable", "monitor", "review_recovery", "collect_more_data"]
    confidence: Annotated[float, Field(ge=0, le=1)]
    reasons: list[str]
    scope_note: str = (
        "Training decision support only; pain, injury, dizziness, or rapid unexplained change "
        "requires appropriate professional assessment."
    )


class StrengthAnalysisResult(BaseModel):
    start_date: date
    end_date: date
    usable_sets: int
    excluded_sets: int
    exercises: list[ExerciseStrengthResult]
    session_metrics: list[SessionMetric]
    pareto_frontier: list[ParetoPoint]
    overall_retention_score: float
    decision: StrengthDecision
    limitations: list[str]


def estimate_e1rm(weight_kg: float, reps: int, rpe: float | None = None) -> tuple[float, float]:
    """Return a robust consensus e1RM and an explicit heuristic uncertainty percent."""
    effective_reps = float(reps)
    if rpe is not None:
        effective_reps += max(0.0, min(4.0, 10.0 - rpe))
    epley = weight_kg * (1 + effective_reps / 30.0)
    brzycki_denominator = max(37.0 - effective_reps, 1.0)
    brzycki = weight_kg * 36.0 / brzycki_denominator
    lombardi = weight_kg * effective_reps**0.10
    estimate = float(np.median([epley, brzycki, lombardi]))
    formula_spread = float(np.ptp([epley, brzycki, lombardi]) / max(estimate, 1e-9) * 100)
    uncertainty = max(2.0 + reps * 0.45 + (2.0 if rpe is None else 0.0), formula_spread)
    return estimate, uncertainty


def _bodyweight_lookup(observations: list[DailyObservation] | None) -> dict[date, float]:
    if not observations:
        return {}
    known = sorted(
        (item.date.toordinal(), float(item.weight_kg)) for item in observations if item.weight_kg is not None
    )
    if not known:
        return {}
    days = np.asarray([item[0] for item in known], dtype=float)
    weights = np.asarray([item[1] for item in known], dtype=float)
    start, end = int(days[0]), int(days[-1])
    return {date.fromordinal(ordinal): float(np.interp(ordinal, days, weights)) for ordinal in range(start, end + 1)}


def _session_metrics(
    sets: list[StrengthSet],
    daily: list[DailyObservation] | None,
    config: StrengthAnalysisConfig,
) -> tuple[list[SessionMetric], int]:
    lookup = _bodyweight_lookup(daily)
    grouped: dict[tuple[date, str], list[StrengthSet]] = defaultdict(list)
    excluded = 0
    for item in sets:
        if item.set_type == "warmup" or item.reps > config.max_reps_for_e1rm:
            excluded += 1
            continue
        grouped[(item.date, item.exercise)].append(item)
    metrics: list[SessionMetric] = []
    for (day, exercise), session_sets in grouped.items():
        estimates = [estimate_e1rm(item.weight_kg, item.reps, item.rpe) for item in session_sets]
        best_index = int(np.argmax([item[0] for item in estimates]))
        bodyweights = [item.bodyweight_kg for item in session_sets if item.bodyweight_kg is not None]
        bodyweight = float(np.median(bodyweights)) if bodyweights else lookup.get(day)
        rpes = [item.rpe for item in session_sets if item.rpe is not None]
        metrics.append(
            SessionMetric(
                date=day,
                exercise=exercise,
                e1rm_kg=estimates[best_index][0],
                e1rm_uncertainty_pct=estimates[best_index][1],
                volume_kg=sum(item.weight_kg * item.reps for item in session_sets),
                working_sets=len(session_sets),
                mean_rpe=float(np.mean(rpes)) if rpes else None,
                bodyweight_kg=bodyweight,
            )
        )
    return sorted(metrics, key=lambda item: (item.date, item.exercise)), excluded


def _regression_slope(values: list[SessionMetric]) -> tuple[float, float]:
    x = np.asarray([(item.date - values[0].date).days for item in values], dtype=float)
    y = np.asarray([item.e1rm_kg for item in values], dtype=float)
    if len(values) < 3 or np.allclose(x, x[0]):
        return 0.0, np.inf
    design = np.column_stack([np.ones_like(x), x])
    coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    residual = y - design @ coefficients
    dof = max(len(y) - 2, 1)
    variance = float(np.sum(residual**2) / dof)
    covariance = variance * np.linalg.pinv(design.T @ design)
    return float(coefficients[1]), float(np.sqrt(max(covariance[1, 1], 0.0)))


def _fatigue_signal(values: list[SessionMetric], recent_count: int) -> bool:
    if len(values) < recent_count * 2:
        return False
    previous = values[-recent_count * 2 : -recent_count]
    recent = values[-recent_count:]
    e1rm_drop = np.mean([item.e1rm_kg for item in recent]) / np.mean([item.e1rm_kg for item in previous]) - 1
    previous_volume = float(np.mean([item.volume_kg for item in previous]))
    volume_drop = float(np.mean([item.volume_kg for item in recent])) / max(previous_volume, 1e-9) - 1
    previous_rpe = [item.mean_rpe for item in previous if item.mean_rpe is not None]
    recent_rpe = [item.mean_rpe for item in recent if item.mean_rpe is not None]
    rpe_rise = float(np.mean(recent_rpe) - np.mean(previous_rpe)) if previous_rpe and recent_rpe else 0.0
    return bool(e1rm_drop < -0.03 and (rpe_rise >= 0.5 or volume_drop < -0.15))


def _exercise_results(metrics: list[SessionMetric], config: StrengthAnalysisConfig) -> list[ExerciseStrengthResult]:
    grouped: dict[str, list[SessionMetric]] = defaultdict(list)
    for item in metrics:
        grouped[item.exercise].append(item)
    preliminary: dict[str, tuple[float, float, float]] = {}
    raw_slopes: list[float] = []
    for exercise, values in grouped.items():
        if len(values) < config.min_sessions_per_exercise:
            continue
        slope_kg_day, slope_se = _regression_slope(values)
        baseline = values[0].e1rm_kg
        slope_pct_week = slope_kg_day / max(baseline, 1e-9) * 700
        slope_se_pct_week = slope_se / max(baseline, 1e-9) * 700
        preliminary[exercise] = (slope_pct_week, slope_se_pct_week, baseline)
        raw_slopes.append(slope_pct_week)
    global_slope = float(np.median(raw_slopes)) if raw_slopes else 0.0

    output: list[ExerciseStrengthResult] = []
    for exercise, values in sorted(grouped.items()):
        flags: set[str] = set()
        if exercise not in preliminary:
            flags.add("insufficient_sessions_for_trend")
            baseline = values[0].e1rm_kg
            raw_slope = 0.0
            raw_se = 10.0
        else:
            raw_slope, raw_se, baseline = preliminary[exercise]
        span = (values[-1].date - values[0].date).days
        session_reliability = len(values) / (len(values) + config.hierarchy_prior_sessions)
        span_reliability = span / (span + 28) if span > 0 else 0.0
        reliability = session_reliability * span_reliability
        hierarchical = reliability * raw_slope + (1 - reliability) * global_slope
        hierarchical_se = max(raw_se * reliability, 0.15 + (1 - reliability) * 0.75)
        lower = hierarchical - 1.96 * hierarchical_se
        upper = hierarchical + 1.96 * hierarchical_se
        decline_probability = float(norm.cdf((config.material_decline_pct_per_week - hierarchical) / hierarchical_se))
        latest = values[-1].e1rm_kg
        change_pct = (latest / baseline - 1) * 100
        bodyweight_values = [item for item in values if item.bodyweight_kg is not None]
        relative_change: float | None = None
        if len(bodyweight_values) >= 2:
            first = bodyweight_values[0]
            last = bodyweight_values[-1]
            first_bodyweight = first.bodyweight_kg
            last_bodyweight = last.bodyweight_kg
            assert first_bodyweight is not None and last_bodyweight is not None
            first_relative = first.e1rm_kg / first_bodyweight**config.allometric_exponent
            last_relative = last.e1rm_kg / last_bodyweight**config.allometric_exponent
            relative_change = (last_relative / first_relative - 1) * 100
        breaks = detect_change_points([item.e1rm_kg for item in values], min_segment=3, max_change_points=2)
        if any(item.e1rm_uncertainty_pct > 12 for item in values):
            flags.add("high_e1rm_formula_uncertainty")
        output.append(
            ExerciseStrengthResult(
                exercise=exercise,
                sessions=len(values),
                span_days=span,
                baseline_e1rm_kg=baseline,
                latest_e1rm_kg=latest,
                e1rm_change_pct=change_pct,
                raw_slope_pct_per_week=raw_slope,
                hierarchical_slope_pct_per_week=hierarchical,
                slope_interval_pct_per_week=(lower, upper),
                decline_probability=float(np.clip(decline_probability, 0, 1)),
                relative_strength_change_pct=relative_change,
                retention_score=100 + change_pct,
                fatigue_signal=_fatigue_signal(values, config.fatigue_recent_sessions),
                change_point_dates=[values[item.index].date for item in breaks],
                quality_flags=flags,
            )
        )
    return output


def _week_start(day: date) -> date:
    return date.fromordinal(day.toordinal() - day.weekday())


def _pareto(metrics: list[SessionMetric]) -> list[ParetoPoint]:
    by_week: dict[date, list[SessionMetric]] = defaultdict(list)
    for item in metrics:
        if item.bodyweight_kg is not None:
            by_week[_week_start(item.date)].append(item)
    if not by_week:
        return []
    baselines: dict[str, float] = {}
    points: list[ParetoPoint] = []
    for week in sorted(by_week):
        values = by_week[week]
        exercise_best: dict[str, float] = {}
        for item in values:
            exercise_best[item.exercise] = max(exercise_best.get(item.exercise, 0.0), item.e1rm_kg)
            baselines.setdefault(item.exercise, item.e1rm_kg)
        indices = [value / baselines[name] for name, value in exercise_best.items()]
        points.append(
            ParetoPoint(
                week=week,
                bodyweight_kg=float(np.median([item.bodyweight_kg for item in values])),
                strength_index=float(np.mean(indices) * 100),
            )
        )
    frontier: list[ParetoPoint] = []
    for candidate in points:
        dominated = any(
            other.bodyweight_kg <= candidate.bodyweight_kg
            and other.strength_index >= candidate.strength_index
            and (other.bodyweight_kg < candidate.bodyweight_kg or other.strength_index > candidate.strength_index)
            for other in points
        )
        if not dominated:
            frontier.append(candidate)
    return sorted(frontier, key=lambda item: item.bodyweight_kg)


def _decision(results: list[ExerciseStrengthResult]) -> StrengthDecision:
    usable = [item for item in results if "insufficient_sessions_for_trend" not in item.quality_flags]
    if not usable:
        return StrengthDecision(
            action="collect_more_data",
            confidence=0.4,
            reasons=["no exercise has enough repeated sessions for a defensible trend"],
        )
    fatigue = [item for item in usable if item.fatigue_signal]
    declining = [item for item in usable if item.decline_probability >= 0.80]
    if fatigue and declining:
        confidence = float(np.mean([item.decline_probability for item in declining]))
        return StrengthDecision(
            action="review_recovery",
            confidence=confidence,
            reasons=[
                f"{len(declining)} exercise trend(s) show a high decline probability",
                f"{len(fatigue)} exercise(s) combine e1RM decline with RPE/volume signals",
            ],
        )
    if declining or fatigue:
        return StrengthDecision(
            action="monitor",
            confidence=0.7,
            reasons=["some exercise-level signals merit another observation block"],
        )
    return StrengthDecision(
        action="stable",
        confidence=float(1 - max(item.decline_probability for item in usable)),
        reasons=["no well-supported exercise trend crosses the configured decline threshold"],
    )


def analyze_strength(
    sets: list[StrengthSet],
    daily_observations: list[DailyObservation] | None = None,
    config: StrengthAnalysisConfig | None = None,
) -> StrengthAnalysisResult:
    if not sets:
        raise ValueError("at least one strength set is required")
    cfg = config or StrengthAnalysisConfig()
    metrics, excluded = _session_metrics(sets, daily_observations, cfg)
    if not metrics:
        raise ValueError("no usable working sets remain after quality filters")
    exercise_results = _exercise_results(metrics, cfg)
    overall = float(np.median([item.retention_score for item in exercise_results]))
    return StrengthAnalysisResult(
        start_date=min(item.date for item in metrics),
        end_date=max(item.date for item in metrics),
        usable_sets=len(sets) - excluded,
        excluded_sets=excluded,
        exercises=exercise_results,
        session_metrics=metrics,
        pareto_frontier=_pareto(metrics),
        overall_retention_score=overall,
        decision=_decision(exercise_results),
        limitations=[
            "e1RM is a formula-based estimate and becomes less stable at high repetitions.",
            "Exercise execution, equipment, range of motion, and fatigue are not fully observed.",
            "Body-weight-normalized strength is descriptive and depends on the chosen exponent.",
            "Observed decline does not identify whether energy deficit, program design, or recovery caused it.",
        ],
    )
