"""Known-truth synthetic stress evaluation for the recent-rate model.

This module compares CutSignal with a deliberately simple observed-weight OLS
baseline.  It is an internal simulation benchmark, not external calibration or
evidence that either method is accurate for a real population.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from scipy.stats import t as student_t

from cutsignal.analysis.state_space import ParticleFilterConfig, run_particle_filter_diagnostics
from cutsignal.models import DailyObservation, SourceRef

EVALUATION_SEED = 20260824


class SyntheticScenario(BaseModel):
    """A fully declared data-generating condition with a known trend rate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    true_rate_kg_per_week: Annotated[float, Field(ge=-2, le=2)]
    days: Annotated[int, Field(ge=28, le=365)] = 70
    fluid_process_sd_kg: Annotated[float, Field(gt=0, le=2)] = 0.23
    measurement_sd_kg: Annotated[float, Field(gt=0, le=2)] = 0.08
    missing_weight_probability: Annotated[float, Field(ge=0, lt=0.8)] = 0.05
    missing_intake_probability: Annotated[float, Field(ge=0, lt=0.8)] = 0.05
    intake_logging_multiplier: Annotated[float, Field(ge=0.5, le=2)] = 1.0
    recent_outlier_kg: Annotated[float, Field(ge=-10, le=10)] = 0.0
    seed: int


class MethodScenarioResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["linked_particle_trajectories", "observed_weight_ols"]
    estimated_rate_kg_per_week: float
    interval_95_kg_per_week: tuple[float, float]
    plateau_probability: Annotated[float, Field(ge=0, le=1)]
    plateau_prediction: bool
    absolute_error_kg_per_week: Annotated[float, Field(ge=0)]
    interval_contains_truth: bool
    brier_score: Annotated[float, Field(ge=0, le=1)]
    observations_in_rate_window: int


class ScenarioEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: SyntheticScenario
    true_plateau: bool
    particle: MethodScenarioResult
    ols: MethodScenarioResult


class MethodSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str
    runs: int
    mean_absolute_error_kg_per_week: float
    median_absolute_error_kg_per_week: float
    p90_absolute_error_kg_per_week: float
    interval_coverage: Annotated[float, Field(ge=0, le=1)]
    mean_brier_score: Annotated[float, Field(ge=0, le=1)]
    classification_accuracy: Annotated[float, Field(ge=0, le=1)]
    false_positives: int
    false_negatives: int
    mean_absolute_error_bootstrap_95: tuple[float, float]
    mean_brier_bootstrap_95: tuple[float, float]


class SyntheticEvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    evidence_type: Literal["known_truth_synthetic_stress_benchmark"] = "known_truth_synthetic_stress_benchmark"
    rate_window_days: int
    plateau_band_kg_per_week: float
    plateau_probability_threshold: float
    particles: int
    scenarios: list[ScenarioEvaluation]
    summaries: list[MethodSummary]
    interpretation_limits: list[str]


def default_scenarios() -> list[SyntheticScenario]:
    """Return the versioned three-rate by four-condition scenario grid."""
    rates = {"loss": -0.45, "plateau": 0.0, "gain": 0.22}
    conditions: dict[str, dict[str, float]] = {
        "clean": {},
        "high-fluid": {"fluid_process_sd_kg": 0.55},
        "missing": {
            "missing_weight_probability": 0.20,
            "missing_intake_probability": 0.25,
        },
        "outlier-and-intake-bias": {
            "recent_outlier_kg": 2.5,
            "intake_logging_multiplier": 1.15,
        },
    }
    scenarios: list[SyntheticScenario] = []
    index = 0
    for condition, overrides in conditions.items():
        for rate_name, rate in rates.items():
            payload: dict[str, object] = {
                "id": f"{rate_name}-{condition}",
                "true_rate_kg_per_week": rate,
                "seed": EVALUATION_SEED + index,
                **overrides,
            }
            scenarios.append(SyntheticScenario.model_validate(payload))
            index += 1
    return scenarios


def simulate_known_truth(scenario: SyntheticScenario) -> list[DailyObservation]:
    """Simulate scale and logged-intake observations around a declared latent trend."""
    rng = np.random.default_rng(scenario.seed)
    start = date(2026, 1, 1)
    initial_weight = 82.0
    tdee_kcal = 2_400.0
    energy_density = 7_700.0
    actual_intake = tdee_kcal + scenario.true_rate_kg_per_week * energy_density / 7
    fluid = 0.0
    rows: list[DailyObservation] = []
    for index in range(scenario.days):
        day = start + timedelta(days=index)
        latent_weight = initial_weight + scenario.true_rate_kg_per_week * index / 7
        fluid = 0.72 * fluid + rng.normal(0, scenario.fluid_process_sd_kg)
        observed_weight = latent_weight + fluid + rng.normal(0, scenario.measurement_sd_kg)
        if index == scenario.days - 7:
            observed_weight += scenario.recent_outlier_kg
        weight_missing = rng.random() < scenario.missing_weight_probability
        intake_missing = rng.random() < scenario.missing_intake_probability
        logged_intake = actual_intake * scenario.intake_logging_multiplier + rng.normal(0, 70)
        flags = {"synthetic_evaluation"}
        if weight_missing and intake_missing:
            flags.add("missing_day")
        rows.append(
            DailyObservation(
                date=day,
                weight_kg=None if weight_missing else observed_weight,
                energy_intake_kcal=None if intake_missing else max(logged_intake, 1_000),
                sources=[
                    SourceRef(
                        provider="CutSignal known-truth synthetic evaluation",
                        record_type="daily-evaluation",
                        source_id=scenario.id,
                    )
                ],
                quality_flags=flags,
            )
        )
    return rows


def _ols_rate(
    observations: list[DailyObservation],
    *,
    window_days: int,
    plateau_band: float,
) -> tuple[float, tuple[float, float], float, int]:
    end = max(item.date for item in observations)
    start = end - timedelta(days=window_days)
    selected = [item for item in observations if item.date >= start and item.weight_kg is not None]
    if len(selected) < 3:
        raise ValueError("observed-weight OLS needs at least three recent weights")
    x = np.asarray([(item.date - start).days for item in selected], dtype=float)
    y = np.asarray([item.weight_kg for item in selected], dtype=float)
    design = np.column_stack([np.ones_like(x), x])
    coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    fitted = design @ coefficients
    degrees = len(selected) - 2
    residual_variance = float(np.sum((y - fitted) ** 2) / degrees)
    centered = x - float(np.mean(x))
    slope_standard_error = float(np.sqrt(residual_variance / np.sum(centered**2))) * 7
    rate = float(coefficients[1]) * 7
    critical = float(student_t.ppf(0.975, degrees))
    interval = (rate - critical * slope_standard_error, rate + critical * slope_standard_error)
    if slope_standard_error <= 1e-12:
        probability = float(abs(rate) <= plateau_band)
    else:
        lower_z = (-plateau_band - rate) / slope_standard_error
        upper_z = (plateau_band - rate) / slope_standard_error
        probability = float(student_t.cdf(upper_z, degrees) - student_t.cdf(lower_z, degrees))
    return rate, interval, float(np.clip(probability, 0, 1)), len(selected)


def _method_result(
    *,
    method: Literal["linked_particle_trajectories", "observed_weight_ols"],
    rate: float,
    interval: tuple[float, float],
    probability: float,
    truth: float,
    band: float,
    threshold: float,
    observations: int,
) -> MethodScenarioResult:
    true_plateau = abs(truth) <= band
    return MethodScenarioResult(
        method=method,
        estimated_rate_kg_per_week=rate,
        interval_95_kg_per_week=interval,
        plateau_probability=probability,
        plateau_prediction=probability >= threshold,
        absolute_error_kg_per_week=abs(rate - truth),
        interval_contains_truth=interval[0] <= truth <= interval[1],
        brier_score=(probability - float(true_plateau)) ** 2,
        observations_in_rate_window=observations,
    )


def _bootstrap_mean_interval(values: np.ndarray, *, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(2_000, len(values)))
    means = np.mean(values[indices], axis=1)
    lower, upper = np.quantile(means, [0.025, 0.975])
    return float(lower), float(upper)


def _summarize(evaluations: list[ScenarioEvaluation], method: Literal["particle", "ols"]) -> MethodSummary:
    results = [getattr(item, method) for item in evaluations]
    errors = np.asarray([item.absolute_error_kg_per_week for item in results], dtype=float)
    brier = np.asarray([item.brier_score for item in results], dtype=float)
    truth = np.asarray([item.true_plateau for item in evaluations], dtype=bool)
    predicted = np.asarray([item.plateau_prediction for item in results], dtype=bool)
    return MethodSummary(
        method=results[0].method,
        runs=len(results),
        mean_absolute_error_kg_per_week=float(np.mean(errors)),
        median_absolute_error_kg_per_week=float(np.median(errors)),
        p90_absolute_error_kg_per_week=float(np.quantile(errors, 0.90)),
        interval_coverage=float(np.mean([item.interval_contains_truth for item in results])),
        mean_brier_score=float(np.mean(brier)),
        classification_accuracy=float(np.mean(truth == predicted)),
        false_positives=int(np.sum(predicted & ~truth)),
        false_negatives=int(np.sum(~predicted & truth)),
        mean_absolute_error_bootstrap_95=_bootstrap_mean_interval(errors, seed=EVALUATION_SEED + 1),
        mean_brier_bootstrap_95=_bootstrap_mean_interval(brier, seed=EVALUATION_SEED + 2),
    )


def evaluate_synthetic_benchmark(
    scenarios: list[SyntheticScenario] | None = None,
    *,
    particles: int = 500,
    rate_window_days: int = 14,
    plateau_band_kg_per_week: float = 0.10,
    plateau_probability_threshold: float = 0.75,
) -> SyntheticEvaluationResult:
    """Evaluate declared scenarios without adapting parameters during the run."""
    scenario_grid = scenarios or default_scenarios()
    if not scenario_grid:
        raise ValueError("synthetic evaluation needs at least one scenario")
    evaluations: list[ScenarioEvaluation] = []
    for scenario in scenario_grid:
        observations = simulate_known_truth(scenario)
        diagnostics = run_particle_filter_diagnostics(
            observations,
            ParticleFilterConfig(particles=particles, random_seed=scenario.seed),
            rate_window_days=rate_window_days,
            plateau_band_kg_per_week=plateau_band_kg_per_week,
        )
        particle_rate = diagnostics.recent_rate
        recent_count = sum(
            item.weight_kg is not None and item.date >= particle_rate.window_start for item in observations
        )
        particle = _method_result(
            method="linked_particle_trajectories",
            rate=particle_rate.median_kg_per_week,
            interval=(particle_rate.lower_kg_per_week, particle_rate.upper_kg_per_week),
            probability=particle_rate.plateau_probability,
            truth=scenario.true_rate_kg_per_week,
            band=plateau_band_kg_per_week,
            threshold=plateau_probability_threshold,
            observations=recent_count,
        )
        ols_rate, ols_interval, ols_probability, ols_count = _ols_rate(
            observations,
            window_days=rate_window_days,
            plateau_band=plateau_band_kg_per_week,
        )
        ols = _method_result(
            method="observed_weight_ols",
            rate=ols_rate,
            interval=ols_interval,
            probability=ols_probability,
            truth=scenario.true_rate_kg_per_week,
            band=plateau_band_kg_per_week,
            threshold=plateau_probability_threshold,
            observations=ols_count,
        )
        evaluations.append(
            ScenarioEvaluation(
                scenario=scenario,
                true_plateau=abs(scenario.true_rate_kg_per_week) <= plateau_band_kg_per_week,
                particle=particle,
                ols=ols,
            )
        )
    return SyntheticEvaluationResult(
        rate_window_days=rate_window_days,
        plateau_band_kg_per_week=plateau_band_kg_per_week,
        plateau_probability_threshold=plateau_probability_threshold,
        particles=particles,
        scenarios=evaluations,
        summaries=[_summarize(evaluations, "particle"), _summarize(evaluations, "ols")],
        interpretation_limits=[
            "The generator is designed by the project and is not an external or representative cohort.",
            "Bootstrap intervals resample this fixed scenario grid; they are not population confidence intervals.",
            "A lower error in these scenarios does not establish clinical validity or future real-world performance.",
            "The OLS comparator uses the same recent weight window but intentionally ignores intake "
            "and earlier history.",
        ],
    )
