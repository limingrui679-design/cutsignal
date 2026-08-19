"""Robust bootstrap particle filter for trend weight and latent TDEE.

This is an uncertainty model, not a metabolic truth machine. The energy-density
coefficient, fluid shifts, intake logging, and process noise are all modeled as
uncertain. Subject-specific estimates require repeated weight and intake data.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator
from scipy.special import gammaln

from cutsignal.exceptions import InsufficientDataError
from cutsignal.models import DailyObservation


class ParticleFilterConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    particles: Annotated[int, Field(ge=500, le=100_000)] = 4_000
    initial_tdee_kcal: Annotated[float, Field(ge=800, le=8_000)] = 2_200
    initial_tdee_sd: Annotated[float, Field(gt=0, le=2_000)] = 450
    tdee_random_walk_sd: Annotated[float, Field(gt=0, le=200)] = 18
    trend_process_sd_kg: Annotated[float, Field(gt=0, le=0.5)] = 0.025
    missing_intake_process_sd_kg: Annotated[float, Field(gt=0, le=1.0)] = 0.09
    fluid_ar: Annotated[float, Field(ge=0, lt=1)] = 0.72
    fluid_process_sd_kg: Annotated[float, Field(gt=0, le=2.0)] = 0.32
    measurement_sd_kg: Annotated[float, Field(gt=0, le=2.0)] = 0.13
    measurement_student_df: Annotated[float, Field(gt=2, le=100)] = 4.0
    energy_density_mean: Annotated[float, Field(ge=4_000, le=12_000)] = 7_700
    energy_density_sd: Annotated[float, Field(gt=0, le=3_000)] = 850
    resample_ess_fraction: Annotated[float, Field(gt=0, le=1)] = 0.5
    tdee_floor_kcal: Annotated[float, Field(ge=500, le=3_000)] = 800
    tdee_ceiling_kcal: Annotated[float, Field(ge=2_000, le=10_000)] = 6_000
    intake_multiplier: Annotated[float, Field(ge=0.5, le=2.0)] = 1.0
    random_seed: int = 20260820

    @model_validator(mode="after")
    def validate_tdee_bounds(self) -> ParticleFilterConfig:
        if self.tdee_floor_kcal >= self.tdee_ceiling_kcal:
            raise ValueError("TDEE floor must be below ceiling")
        return self


class StateEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    observed_weight_kg: float | None
    energy_intake_kcal: float | None
    trend_weight_median_kg: float
    trend_weight_lower_kg: float
    trend_weight_upper_kg: float
    tdee_median_kcal: float
    tdee_lower_kcal: float
    tdee_upper_kcal: float
    effective_sample_size: float
    quality_flags: set[str] = Field(default_factory=set)


def _student_t_logpdf(residual: np.ndarray, scale: float, degrees: float) -> np.ndarray:
    z = residual / scale
    constant = gammaln((degrees + 1.0) / 2.0) - gammaln(degrees / 2.0) - 0.5 * np.log(degrees * np.pi) - np.log(scale)
    result = constant - ((degrees + 1.0) / 2.0) * np.log1p((z**2) / degrees)
    return np.asarray(result, dtype=float)


def _weighted_quantile(values: np.ndarray, weights: np.ndarray) -> tuple[float, float, float]:
    order = np.argsort(values)
    sorted_values = values[order]
    cumulative = np.cumsum(weights[order])
    cumulative /= cumulative[-1]
    selected = np.interp([0.025, 0.5, 0.975], cumulative, sorted_values)
    return float(selected[0]), float(selected[1]), float(selected[2])


def _systematic_resample(weights: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    positions = (rng.random() + np.arange(weights.size)) / weights.size
    cumulative = np.cumsum(weights)
    cumulative[-1] = 1.0
    return np.asarray(np.searchsorted(cumulative, positions), dtype=np.int64)


def _calendar(observations: list[DailyObservation]) -> list[DailyObservation]:
    by_day = {observation.date: observation for observation in observations}
    start = min(by_day)
    end = max(by_day)
    output: list[DailyObservation] = []
    current = start
    while current <= end:
        observation = by_day.get(current)
        if observation is None:
            output.append(
                DailyObservation(
                    date=current,
                    energy_intake_kcal=None,
                    quality_flags={"missing_day"},
                )
            )
        else:
            output.append(observation)
        current += timedelta(days=1)
    return output


def run_particle_filter(
    observations: list[DailyObservation],
    config: ParticleFilterConfig | None = None,
) -> list[StateEstimate]:
    """Estimate daily trend weight and TDEE with robust observation updates."""
    if not observations:
        raise InsufficientDataError("no daily observations")
    weights_present = [item for item in observations if item.weight_kg is not None]
    if len(weights_present) < 2:
        raise InsufficientDataError("at least two body-weight observations are required")
    cfg = config or ParticleFilterConfig()
    calendar = _calendar(sorted(observations, key=lambda item: item.date))
    rng = np.random.default_rng(cfg.random_seed)
    n = cfg.particles
    first_weight_value = weights_present[0].weight_kg
    assert first_weight_value is not None
    first_weight = float(first_weight_value)

    tdee = np.clip(
        rng.normal(cfg.initial_tdee_kcal, cfg.initial_tdee_sd, n),
        cfg.tdee_floor_kcal,
        cfg.tdee_ceiling_kcal,
    )
    fluid = rng.normal(0.0, cfg.fluid_process_sd_kg, n)
    trend = first_weight - fluid
    energy_density = np.clip(rng.normal(cfg.energy_density_mean, cfg.energy_density_sd, n), 4_000, 12_000)
    particle_weights = np.full(n, 1.0 / n)
    estimates: list[StateEstimate] = []

    for day_index, observation in enumerate(calendar):
        if day_index > 0:
            tdee = np.clip(
                tdee + rng.normal(0.0, cfg.tdee_random_walk_sd, n),
                cfg.tdee_floor_kcal,
                cfg.tdee_ceiling_kcal,
            )
            fluid = cfg.fluid_ar * fluid + rng.normal(0.0, cfg.fluid_process_sd_kg, n)
            if observation.energy_intake_kcal is not None:
                intake = observation.energy_intake_kcal * cfg.intake_multiplier
                trend += (intake - tdee) / energy_density
                trend += rng.normal(0.0, cfg.trend_process_sd_kg, n)
            else:
                trend += rng.normal(0.0, cfg.missing_intake_process_sd_kg, n)

        flags = set(observation.quality_flags)
        if observation.weight_kg is not None:
            residual = observation.weight_kg - (trend + fluid)
            log_likelihood = _student_t_logpdf(residual, cfg.measurement_sd_kg, cfg.measurement_student_df)
            log_likelihood -= np.max(log_likelihood)
            particle_weights *= np.exp(log_likelihood)
            total = float(np.sum(particle_weights))
            if not np.isfinite(total) or total <= 0:
                particle_weights.fill(1.0 / n)
                flags.add("particle_weight_reset")
            else:
                particle_weights /= total
        else:
            flags.add("weight_missing")

        ess = float(1.0 / np.sum(particle_weights**2))
        weight_lower, weight_median, weight_upper = _weighted_quantile(trend, particle_weights)
        tdee_lower, tdee_median, tdee_upper = _weighted_quantile(tdee, particle_weights)
        estimates.append(
            StateEstimate(
                date=observation.date,
                observed_weight_kg=observation.weight_kg,
                energy_intake_kcal=observation.energy_intake_kcal,
                trend_weight_median_kg=weight_median,
                trend_weight_lower_kg=weight_lower,
                trend_weight_upper_kg=weight_upper,
                tdee_median_kcal=tdee_median,
                tdee_lower_kcal=tdee_lower,
                tdee_upper_kcal=tdee_upper,
                effective_sample_size=ess,
                quality_flags=flags,
            )
        )
        if ess < cfg.resample_ess_fraction * n:
            indices = _systematic_resample(particle_weights, rng)
            trend = trend[indices]
            tdee = tdee[indices]
            fluid = fluid[indices]
            energy_density = energy_density[indices]
            particle_weights.fill(1.0 / n)
    return estimates
