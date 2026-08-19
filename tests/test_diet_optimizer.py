from __future__ import annotations

import pytest

from cutsignal.exceptions import OptimizationInfeasibleError
from cutsignal.models import DietObjectiveWeights
from cutsignal.optimization.diet import _build_problem, build_pareto_frontier, optimize_weekly_plan


def test_robust_milp_returns_auditable_feasible_plan(demo_foods, small_constraints) -> None:
    result = optimize_weekly_plan(demo_foods, small_constraints, time_limit_seconds=2)
    assert result.status == "optimal"
    assert result.mip_gap == 0
    assert result.unique_foods >= small_constraints.min_unique_foods
    assert min(result.constraint_slack.values()) >= -1e-6
    assert len(result.daily) == small_constraints.days
    assert result.sensitivity[0].scenario == "modeled-robust-bounds"
    assert result.sensitivity[0].feasible
    assert any(not item.feasible for item in result.sensitivity[1:])
    assert any("data quality" in warning for warning in result.warnings)


def test_milp_filters_allergens_tags_and_preflight(demo_foods, small_constraints) -> None:
    excluded = {item.name.casefold() for item in demo_foods if "soy" in item.allergens}
    plan = optimize_weekly_plan(
        demo_foods,
        small_constraints.model_copy(update={"excluded_allergens": {"soy"}}),
        time_limit_seconds=2,
    )
    assert not excluded & {entry.food_name.casefold() for entry in plan.entries}

    with pytest.raises(OptimizationInfeasibleError, match="no foods"):
        optimize_weekly_plan(
            demo_foods,
            small_constraints.model_copy(update={"required_tags": {"nonexistent"}}),
            time_limit_seconds=1,
        )
    with pytest.raises(OptimizationInfeasibleError, match="protein"):
        optimize_weekly_plan(
            demo_foods,
            small_constraints.model_copy(update={"protein_min_g": 2_000}),
            time_limit_seconds=1,
        )


def test_pareto_profiles_and_independent_matrix_formulation(demo_foods, small_constraints) -> None:
    points = build_pareto_frontier(demo_foods, small_constraints, time_limit_seconds=1)
    assert points
    assert len({point.label for point in points}) == len(points)
    c, integrality, bounds, linear, layout = _build_problem(
        demo_foods,
        small_constraints,
        DietObjectiveWeights(),
    )
    assert c.shape == (layout.size,)
    assert integrality.shape == c.shape
    assert bounds.lb.shape == c.shape
    assert linear.A.shape[1] == layout.size
