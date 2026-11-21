from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest

from cutsignal.analysis.changepoints import detect_change_points
from cutsignal.analysis.cut import CutAnalysisConfig, _decision, _hampel_weights, analyze_cut
from cutsignal.analysis.state_space import (
    ParticleFilterConfig,
    run_particle_filter,
    run_particle_filter_diagnostics,
)
from cutsignal.exceptions import DataValidationError, InsufficientDataError
from cutsignal.models import DailyObservation


def test_change_point_detection_and_guards() -> None:
    rng = np.random.default_rng(7)
    first = 80 - np.arange(35) * 0.08
    second = first[-1] + np.arange(1, 36) * 0.01
    values = np.concatenate([first, second]) + rng.normal(0, 0.02, 70)
    points = detect_change_points(values, min_segment=10, max_change_points=2)
    assert points
    assert min(abs(point.index - 35) for point in points) <= 3
    assert detect_change_points([1.0] * 20, min_segment=10) == []
    assert detect_change_points([1.0, 2.0], min_segment=3) == []
    with pytest.raises(ValueError, match="one-dimensional"):
        detect_change_points(np.ones((2, 2)))
    with pytest.raises(ValueError, match="finite"):
        detect_change_points([1.0] * 20 + [float("nan")], min_segment=5)


def test_particle_filter_is_reproducible_and_fills_calendar(short_daily) -> None:
    observations = [item for index, item in enumerate(short_daily) if index != 10]
    config = ParticleFilterConfig(particles=500, random_seed=99)
    first = run_particle_filter(observations, config)
    second = run_particle_filter(observations, config)
    assert len(first) == 35
    assert first[10].date == date(2026, 1, 11)
    assert "missing_day" in first[10].quality_flags
    assert [item.tdee_median_kcal for item in first] == [item.tdee_median_kcal for item in second]
    assert all(item.tdee_lower_kcal <= item.tdee_median_kcal <= item.tdee_upper_kcal for item in first)
    diagnostic = run_particle_filter_diagnostics(
        observations,
        config,
        rate_window_days=14,
        plateau_band_kg_per_week=0.1,
    )
    assert diagnostic.recent_rate.method == "linked_particle_trajectories"
    assert diagnostic.recent_rate.elapsed_days == 14
    assert diagnostic.recent_rate.lower_kg_per_week <= diagnostic.recent_rate.median_kg_per_week
    assert 0 <= diagnostic.recent_rate.plateau_probability <= 1


def test_particle_filter_rejects_insufficient_data() -> None:
    valid = [
        DailyObservation(date=date(2026, 1, 1), weight_kg=80),
        DailyObservation(date=date(2026, 1, 2), weight_kg=79.9),
    ]
    with pytest.raises(ValueError, match="rate_window_days"):
        run_particle_filter_diagnostics(valid, rate_window_days=0)
    with pytest.raises(ValueError, match="rate_window_days"):
        run_particle_filter_diagnostics(valid, rate_window_days=366)
    with pytest.raises(ValueError, match="plateau_band"):
        run_particle_filter_diagnostics(valid, plateau_band_kg_per_week=0)
    with pytest.raises(ValueError, match="plateau_band"):
        run_particle_filter_diagnostics(valid, plateau_band_kg_per_week=5.1)
    with pytest.raises(InsufficientDataError, match="no daily"):
        run_particle_filter([])
    with pytest.raises(InsufficientDataError, match="two"):
        run_particle_filter([DailyObservation(date=date(2026, 1, 1), weight_kg=80)])
    with pytest.raises(ValueError, match="floor"):
        ParticleFilterConfig(tdee_floor_kcal=3_000, tdee_ceiling_kcal=2_000)
    duplicated = [
        DailyObservation(date=date(2026, 1, 1), weight_kg=80),
        DailyObservation(date=date(2026, 1, 1), weight_kg=79),
    ]
    with pytest.raises(DataValidationError, match="unique dates"):
        run_particle_filter(duplicated)


def test_cut_analysis_runs_all_sensitivity_scenarios(short_daily) -> None:
    config = CutAnalysisConfig(filter=ParticleFilterConfig(particles=500), maximum_tdee_interval_width=2_000)
    result = analyze_cut(short_daily, config)
    assert result.days == 35
    assert result.weight_completeness == 1
    assert result.intake_completeness == 1
    assert len(result.sensitivity) == 5
    assert {item.scenario for item in result.sensitivity} == {
        "recorded-intake",
        "intake-plus-10-percent",
        "intake-plus-20-percent",
        "higher-fluid-variance",
        "weight-outliers-excluded",
    }
    assert {item.random_seed for item in result.sensitivity} == {config.filter.random_seed}
    assert 0 <= result.plateau_probability <= 1
    assert result.rate_posterior_method == "linked_particle_trajectories"
    assert result.rate_posterior_effective_sample_size > 0
    assert result.decision.scope_note.startswith("Decision support")


def test_cut_evidence_gates_and_outlier_exclusion() -> None:
    config = CutAnalysisConfig()
    missing = _decision(
        days=10,
        weight_completeness=0.4,
        intake_completeness=0.5,
        tdee_width=900,
        rate=0,
        plateau_probability=0.9,
        config=config,
    )
    assert missing.action == "collect_more_data"
    assert len(missing.next_evidence) >= 2
    review = _decision(
        days=35,
        weight_completeness=1,
        intake_completeness=1,
        tdee_width=100,
        rate=0.01,
        plateau_probability=0.9,
        config=config,
    )
    assert review.action == "consider_review"
    assert (
        _decision(
            days=35,
            weight_completeness=1,
            intake_completeness=1,
            tdee_width=100,
            rate=-0.4,
            plateau_probability=0.1,
            config=config,
        ).action
        == "continue"
    )

    start = date(2026, 1, 1)
    rows = [
        DailyObservation(
            date=start + timedelta(days=index),
            weight_kg=80 - index * 0.03 + (3 if index == 8 else 0),
            energy_intake_kcal=2_000,
        )
        for index in range(17)
    ]
    filtered = _hampel_weights(rows)
    assert filtered[8].weight_kg is None
    assert "weight_hampel_excluded" in filtered[8].quality_flags


def test_window_ancestry_measures_descendants_after_resampling() -> None:
    days = [
        DailyObservation(
            date=date(2025, 1, 1) + timedelta(days=i), weight_kg=80 + 0.1 * np.sin(i), energy_intake_kcal=2200
        )
        for i in range(30)
    ]
    cfg = ParticleFilterConfig(particles=500, resample_ess_fraction=0.99)
    summary = run_particle_filter_diagnostics(days, cfg, rate_window_days=14).recent_rate
    assert summary.window_start == days[-15].date
    legacy = summary.model_dump(exclude={"distinct_start_ancestors", "ancestor_effective_sample_size"})
    assert type(summary).model_validate(legacy).ancestor_effective_sample_size is None
    assert summary.distinct_start_ancestors is not None and summary.ancestor_effective_sample_size is not None
    assert 1 <= summary.distinct_start_ancestors < cfg.particles
    assert 1 <= summary.ancestor_effective_sample_size <= summary.distinct_start_ancestors + 1e-8
    assert summary.ancestor_effective_sample_size <= summary.effective_sample_size + 1e-8


def test_scale_prior_is_computed_before_seeing_the_current_weight():
    from datetime import date, timedelta

    from cutsignal.analysis.state_space import run_particle_filter
    from cutsignal.models import DailyObservation

    def predict(last):
        rows = [
            DailyObservation(date=date(2025, 1, 1) + timedelta(days=i), weight_kg=w)
            for i, w in enumerate([80, 80.2, 79.9, last])
        ]
        return run_particle_filter(rows, ParticleFilterConfig(particles=500))[-1].prior_scale_weight_median_kg

    assert predict(79) == predict(85)
