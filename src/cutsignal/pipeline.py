"""End-to-end orchestration across CutSignal, LeanGuard, and BudgetCut."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from cutsignal.analysis.cut import CutAnalysisConfig, CutAnalysisResult, analyze_cut
from cutsignal.analysis.strength import (
    StrengthAnalysisConfig,
    StrengthAnalysisResult,
    analyze_strength,
)
from cutsignal.models import (
    DailyObservation,
    DietConstraints,
    DietObjectiveWeights,
    FoodItem,
    StrengthSet,
)
from cutsignal.optimization.diet import (
    DietPlanResult,
    PlanPoint,
    build_pareto_frontier,
    optimize_weekly_plan,
)


class IntegratedDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "continue",
        "collect_more_data",
        "review_recovery_first",
        "consider_plan_review",
        "validate_food_data",
    ]
    rationale: list[str]
    evidence_order: list[str]
    scope_note: str = (
        "CutSignal prioritizes evidence collection and review; it does not prescribe a calorie "
        "target, diagnose a plateau, or replace individualized professional care."
    )


class PipelineResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cut: CutAnalysisResult
    strength: StrengthAnalysisResult
    diet: DietPlanResult
    diet_pareto: list[PlanPoint]
    integrated_decision: IntegratedDecision


def integrate_decisions(
    cut: CutAnalysisResult,
    strength: StrengthAnalysisResult,
    diet: DietPlanResult,
) -> IntegratedDecision:
    if cut.decision.action == "collect_more_data":
        return IntegratedDecision(
            action="collect_more_data",
            rationale=[
                *cut.decision.reasons,
                "model adjustment is deferred until evidence gates pass",
            ],
            evidence_order=[
                "paired weight and intake coverage",
                "TDEE interval width",
                "strength and recovery trend",
                "diet-plan sensitivity",
            ],
        )
    if strength.decision.action == "review_recovery":
        return IntegratedDecision(
            action="review_recovery_first",
            rationale=[
                *strength.decision.reasons,
                "a food-intake adjustment is not prioritized while recovery signals are unresolved",
            ],
            evidence_order=[
                "pain/illness and recovery context",
                "training volume, RPE, and technique consistency",
                "weight/TDEE trend",
                "diet feasibility",
            ],
        )
    if diet.weighted_data_quality < 0.75:
        return IntegratedDecision(
            action="validate_food_data",
            rationale=["the optimized plan relies heavily on lower-confidence nutrient or price records"],
            evidence_order=[
                "replace synthetic/crowdsourced foods with verified records",
                "confirm local prices and serving sizes",
                "rerun robust optimization",
            ],
        )
    if cut.decision.action == "consider_review":
        return IntegratedDecision(
            action="consider_plan_review",
            rationale=[
                *cut.decision.reasons,
                "strength evidence does not trigger recovery-first gating",
            ],
            evidence_order=[
                "check adherence and measurement conditions",
                "review food-plan feasibility and sensitivity",
                "seek qualified input before a material change",
            ],
        )
    return IntegratedDecision(
        action="continue",
        rationale=[
            "the current evidence does not pass a change threshold",
            "strength analysis does not show a high-confidence material decline",
        ],
        evidence_order=["continue consistent logging", "review at the next observation window"],
    )


def run_pipeline(
    daily: list[DailyObservation],
    strength_sets: list[StrengthSet],
    foods: list[FoodItem],
    diet_constraints: DietConstraints,
    *,
    cut_config: CutAnalysisConfig | None = None,
    strength_config: StrengthAnalysisConfig | None = None,
    diet_objectives: DietObjectiveWeights | None = None,
    diet_time_limit_seconds: float = 10.0,
    pareto_time_limit_seconds: float = 3.0,
) -> PipelineResult:
    cut = analyze_cut(daily, cut_config)
    strength = analyze_strength(strength_sets, daily, strength_config)
    diet = optimize_weekly_plan(
        foods,
        diet_constraints,
        diet_objectives,
        time_limit_seconds=diet_time_limit_seconds,
    )
    pareto = build_pareto_frontier(
        foods,
        diet_constraints,
        time_limit_seconds=pareto_time_limit_seconds,
    )
    return PipelineResult(
        cut=cut,
        strength=strength,
        diet=diet,
        diet_pareto=pareto,
        integrated_decision=integrate_decisions(cut, strength, diet),
    )
