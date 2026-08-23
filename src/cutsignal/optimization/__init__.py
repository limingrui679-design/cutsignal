"""Robust multi-objective meal-plan optimization."""

from cutsignal.optimization.diet import (
    build_pareto_frontier,
    optimize_weekly_plan,
    validate_weekly_plan,
)

__all__ = ["build_pareto_frontier", "optimize_weekly_plan", "validate_weekly_plan"]
