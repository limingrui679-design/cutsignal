from __future__ import annotations

from datetime import date, timedelta

import pytest

from cutsignal.analysis.strength import StrengthAnalysisConfig, analyze_strength, estimate_e1rm
from cutsignal.models import SourceRef, StrengthSet


def test_e1rm_consensus_and_rpe() -> None:
    without_rpe, wide = estimate_e1rm(100, 5)
    with_rpe, narrow = estimate_e1rm(100, 5, 9)
    assert without_rpe > 100
    assert with_rpe > without_rpe
    assert narrow <= wide


def test_strength_analysis_metrics_and_pareto(repeated_strength, short_daily) -> None:
    result = analyze_strength(repeated_strength, short_daily)
    assert result.usable_sets == len(repeated_strength)
    assert result.excluded_sets == 0
    assert len(result.exercises) == 1
    exercise = result.exercises[0]
    assert exercise.sessions == 8
    assert exercise.relative_strength_change_pct is not None
    assert exercise.slope_interval_pct_per_week[0] <= exercise.hierarchical_slope_pct_per_week
    assert exercise.mean_intensity_pct_e1rm > 0
    assert exercise.sessions_per_week > 0
    assert result.weekly_summaries
    assert result.shrinkage_method == "uncertainty_weighted_empirical_bayes"
    assert result.pareto_frontier
    assert result.decision.action in {"stable", "monitor"}


def test_strength_filters_warmups_and_insufficient_history(source: SourceRef) -> None:
    rows = [
        StrengthSet(
            date=date(2026, 1, 1),
            exercise="Squat",
            weight_kg=20,
            reps=5,
            set_type="warmup",
            source=source,
        ),
        StrengthSet(
            date=date(2026, 1, 1),
            exercise="Squat",
            weight_kg=100,
            reps=5,
            source=source,
        ),
    ]
    result = analyze_strength(rows, config=StrengthAnalysisConfig(min_sessions_per_exercise=2))
    assert result.excluded_sets == 1
    assert result.decision.action == "collect_more_data"
    assert "insufficient_sessions_for_trend" in result.exercises[0].quality_flags
    with pytest.raises(ValueError, match="at least one"):
        analyze_strength([])
    with pytest.raises(ValueError, match="no usable"):
        analyze_strength(rows[:1])


def test_decline_plus_rpe_volume_signal_triggers_recovery_review(source: SourceRef) -> None:
    start = date(2026, 1, 1)
    rows: list[StrengthSet] = []
    for session in range(12):
        load = 105 - session * 1.8
        rpe = min(10.0, 7.0 + session * 0.25)
        set_count = 4 if session < 9 else 2
        for set_number in range(set_count):
            rows.append(
                StrengthSet(
                    date=start + timedelta(days=session * 4),
                    exercise="Back Squat",
                    weight_kg=load - set_number,
                    reps=5,
                    rpe=rpe,
                    source=source,
                )
            )
    result = analyze_strength(
        rows,
        config=StrengthAnalysisConfig(
            min_sessions_per_exercise=4,
            hierarchy_prior_sessions=0.5,
            material_decline_pct_per_week=-0.2,
        ),
    )
    assert result.exercises[0].fatigue_signal
    assert result.exercises[0].decline_probability >= 0.8
    assert result.decision.action == "review_recovery"
