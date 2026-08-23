from __future__ import annotations

import pytest

from cutsignal.evaluation import (
    SyntheticScenario,
    _ols_rate,
    default_scenarios,
    evaluate_synthetic_benchmark,
    simulate_known_truth,
)


def test_known_truth_simulation_is_deterministic_and_labeled() -> None:
    scenario = SyntheticScenario(id="test-loss", true_rate_kg_per_week=-0.4, seed=17)
    first = simulate_known_truth(scenario)
    second = simulate_known_truth(scenario)
    assert first == second
    assert all("synthetic_evaluation" in item.quality_flags for item in first)
    assert all(item.sources[0].provider == "CutSignal known-truth synthetic evaluation" for item in first)

    grid = default_scenarios()
    assert len(grid) == 12
    assert len({item.id for item in grid}) == 12
    assert {item.true_rate_kg_per_week for item in grid} == {-0.45, 0.0, 0.22}

    with pytest.raises(ValueError, match="three recent weights"):
        _ols_rate(first[:2], window_days=14, plateau_band=0.10)


def test_synthetic_evaluation_reports_comparator_failures_and_uncertainty() -> None:
    scenarios = [
        SyntheticScenario(id="loss", true_rate_kg_per_week=-0.45, seed=21),
        SyntheticScenario(id="plateau", true_rate_kg_per_week=0.0, seed=22),
        SyntheticScenario(
            id="noisy-plateau",
            true_rate_kg_per_week=0.0,
            fluid_process_sd_kg=0.55,
            recent_outlier_kg=2.5,
            seed=23,
        ),
    ]
    result = evaluate_synthetic_benchmark(scenarios, particles=500)
    assert result.evidence_type == "known_truth_synthetic_stress_benchmark"
    assert len(result.scenarios) == 3
    assert {item.method for item in result.summaries} == {
        "linked_particle_trajectories",
        "observed_weight_ols",
    }
    for summary in result.summaries:
        assert summary.runs == 3
        assert summary.mean_absolute_error_bootstrap_95[0] <= summary.mean_absolute_error_bootstrap_95[1]
        assert summary.mean_brier_bootstrap_95[0] <= summary.mean_brier_bootstrap_95[1]
    assert all(item.particle.interval_95_kg_per_week for item in result.scenarios)
    assert all(item.ols.interval_95_kg_per_week for item in result.scenarios)
    assert "not an external" in result.interpretation_limits[0]
