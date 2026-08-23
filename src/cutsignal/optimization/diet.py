"""BudgetCut mixed-integer weekly diet optimizer.

Food portions are integer serving units. Daily constraints use conservative
nutrient and price coefficients when robust mode is enabled. The optimizer does
not choose calorie targets; it only evaluates constraints supplied by the user.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, cast

import numpy as np
import pulp
from pydantic import BaseModel, ConfigDict, Field
from scipy.optimize import Bounds, LinearConstraint

from cutsignal.exceptions import DataValidationError, OptimizationInfeasibleError
from cutsignal.models import DietConstraints, DietObjectiveWeights, FoodItem

MAX_OPTIMIZER_FOODS = 500
MAX_SOLVER_SECONDS = 3_600.0


class MealPlanEntry(BaseModel):
    day: int
    food_id: str
    food_name: str
    servings: int
    grams: float
    calories_kcal: float
    protein_g: float
    fiber_g: float
    cost: float
    prep_minutes: float
    data_quality_score: Annotated[float, Field(ge=0, le=1)]


class DailyPlanSummary(BaseModel):
    day: int
    calories_kcal: float
    robust_calories_lower: float
    robust_calories_upper: float
    protein_g: float
    robust_protein_lower_g: float
    fiber_g: float
    robust_fiber_lower_g: float
    sodium_mg: float
    cost: float
    robust_cost_upper: float
    prep_minutes: float
    preference_score: float


class PlanPoint(BaseModel):
    label: str
    total_cost: float
    total_prep_minutes: float
    mean_preference: float
    unique_foods: int


class PlanSensitivityResult(BaseModel):
    scenario: str
    feasible: bool
    minimum_slack_by_constraint: dict[str, float]
    violations: list[str]


class PlanValidationResult(BaseModel):
    """Independent post-solve checks against the original user constraints."""

    feasible: bool
    slack_by_constraint: dict[str, float]
    violations: list[str]


class DietPlanResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    solver_message: str
    mip_gap: float | None
    objective_value: float
    entries: list[MealPlanEntry]
    daily: list[DailyPlanSummary]
    total_cost: float
    robust_total_cost_upper: float
    unique_foods: int
    weighted_data_quality: Annotated[float, Field(ge=0, le=1)]
    constraint_slack: dict[str, float]
    independent_validation: PlanValidationResult
    sensitivity: list[PlanSensitivityResult]
    warnings: list[str]
    assumptions: list[str]


@dataclass(frozen=True)
class _Layout:
    days: int
    foods: int

    @property
    def x_start(self) -> int:
        return 0

    @property
    def y_start(self) -> int:
        return self.days * self.foods

    @property
    def z_start(self) -> int:
        return 2 * self.days * self.foods

    @property
    def positive_deviation_start(self) -> int:
        return self.z_start + self.foods

    @property
    def negative_deviation_start(self) -> int:
        return self.positive_deviation_start + self.days

    @property
    def size(self) -> int:
        return self.negative_deviation_start + self.days

    def x(self, day: int, food: int) -> int:
        return self.x_start + day * self.foods + food

    def y(self, day: int, food: int) -> int:
        return self.y_start + day * self.foods + food

    def z(self, food: int) -> int:
        return self.z_start + food

    def positive_deviation(self, day: int) -> int:
        return self.positive_deviation_start + day

    def negative_deviation(self, day: int) -> int:
        return self.negative_deviation_start + day


def _eligible(foods: list[FoodItem], constraints: DietConstraints) -> list[FoodItem]:
    if len(foods) > MAX_OPTIMIZER_FOODS:
        raise DataValidationError(f"food catalog has {len(foods)} items; optimizer maximum is {MAX_OPTIMIZER_FOODS}")
    if len({food.food_id for food in foods}) != len(foods):
        raise OptimizationInfeasibleError("food_id values must be unique")
    selected: list[FoodItem] = []
    for food in foods:
        if constraints.excluded_allergens & {item.casefold() for item in food.allergens}:
            continue
        tags = {item.casefold() for item in food.tags}
        if constraints.required_tags and not constraints.required_tags <= tags:
            continue
        if constraints.forbidden_tags & tags:
            continue
        selected.append(food)
    if not selected:
        raise OptimizationInfeasibleError("no foods remain after allergen/tag filters")
    if len(selected) < constraints.min_unique_foods:
        raise OptimizationInfeasibleError(
            f"only {len(selected)} eligible foods remain, below min_unique_foods={constraints.min_unique_foods}"
        )
    return selected


def validate_weekly_plan(
    entries: list[MealPlanEntry],
    foods: list[FoodItem],
    constraints: DietConstraints,
) -> PlanValidationResult:
    """Recompute every hard constraint without reading solver variables."""
    lookup = {food.food_id: food for food in foods}
    slacks: dict[str, float] = {}
    violations: list[str] = []
    if len(lookup) != len(foods):
        violations.append("duplicate_food_ids")
    unknown = sorted({entry.food_id for entry in entries} - lookup.keys())
    if unknown:
        violations.extend(f"unknown_food:{food_id}" for food_id in unknown)
    invalid_days = sorted({entry.day for entry in entries if not 1 <= entry.day <= constraints.days})
    violations.extend(f"invalid_day:{day}" for day in invalid_days)
    if any(entry.servings <= 0 for entry in entries):
        violations.append("nonpositive_servings")

    by_day: dict[int, list[MealPlanEntry]] = {
        day: [entry for entry in entries if entry.day == day] for day in range(1, constraints.days + 1)
    }
    for day, day_entries in by_day.items():
        if not day_entries:
            violations.append(f"day_{day}.empty")
            continue
        selected = [(lookup[entry.food_id], entry.servings) for entry in day_entries if entry.food_id in lookup]

        def robust_total(
            field: str,
            mode: str,
            selected_items: list[tuple[FoodItem, int]] = selected,
        ) -> float:
            return float(
                sum(
                    _coefficient(food, field, mode, constraints.robust_nutrition) * servings
                    for food, servings in selected_items
                )
            )

        day_slacks = {
            f"day_{day}.calories_min": robust_total("calories_kcal", "lower") - constraints.calories_min,
            f"day_{day}.calories_max": constraints.calories_max - robust_total("calories_kcal", "upper"),
            f"day_{day}.protein_min": robust_total("protein_g", "lower") - constraints.protein_min_g,
            f"day_{day}.fiber_min": robust_total("fiber_g", "lower") - constraints.fiber_min_g,
            f"day_{day}.cost_max": constraints.budget_max_per_day
            - sum(
                food.price * (1 + food.price_uncertainty if constraints.robust_price else 1) * servings
                for food, servings in selected
            ),
            f"day_{day}.prep_max": constraints.prep_minutes_max_per_day
            - sum(food.prep_minutes * servings for food, servings in selected),
        }
        if constraints.sodium_max_mg is not None:
            day_slacks[f"day_{day}.sodium_max"] = constraints.sodium_max_mg - robust_total("sodium_mg", "upper")
        for nutrient, required in constraints.micronutrient_min.items():
            amount = sum(
                float(food.micronutrients.get(nutrient, 0.0))
                * (1 - food.nutrient_uncertainty if constraints.robust_nutrition else 1)
                * servings
                for food, servings in selected
            )
            day_slacks[f"day_{day}.micronutrient_{nutrient}_min"] = amount - required
        slacks.update(day_slacks)

        servings_by_food: dict[str, int] = {}
        for entry in day_entries:
            servings_by_food[entry.food_id] = servings_by_food.get(entry.food_id, 0) + entry.servings
        for food_id, servings in servings_by_food.items():
            if food_id in lookup:
                slacks[f"day_{day}.{food_id}.servings_max"] = lookup[food_id].max_servings_per_day - servings

    used_foods = {entry.food_id for entry in entries if entry.food_id in lookup}
    slacks["weekly.unique_foods_min"] = len(used_foods) - constraints.min_unique_foods
    for food_id in used_foods:
        if food_id not in lookup:
            continue
        days_used = len({entry.day for entry in entries if entry.food_id == food_id})
        slacks[f"weekly.{food_id}.days_max"] = constraints.max_days_per_food - days_used
        food = lookup[food_id]
        allergens = {item.casefold() for item in food.allergens}
        tags = {item.casefold() for item in food.tags}
        if constraints.excluded_allergens & allergens:
            violations.append(f"excluded_allergen:{food_id}")
        if constraints.required_tags and not {item.casefold() for item in constraints.required_tags} <= tags:
            violations.append(f"required_tag_missing:{food_id}")
        if {item.casefold() for item in constraints.forbidden_tags} & tags:
            violations.append(f"forbidden_tag:{food_id}")

    violations.extend(sorted(name for name, value in slacks.items() if value < -1e-6))
    unique_violations = sorted(set(violations))
    return PlanValidationResult(
        feasible=not unique_violations,
        slack_by_constraint=slacks,
        violations=unique_violations,
    )


def _coefficient(food: FoodItem, field: str, mode: str, robust: bool) -> float:
    value = float(getattr(food, field))
    if not robust:
        return value
    uncertainty = food.nutrient_uncertainty
    if mode == "lower":
        return value * (1 - uncertainty)
    if mode == "upper":
        return value * (1 + uncertainty)
    raise ValueError(f"unknown robust coefficient mode: {mode}")


def _preflight(foods: list[FoodItem], constraints: DietConstraints) -> None:
    maximum_protein = sum(
        _coefficient(food, "protein_g", "lower", constraints.robust_nutrition) * food.max_servings_per_day
        for food in foods
    )
    maximum_fiber = sum(
        _coefficient(food, "fiber_g", "lower", constraints.robust_nutrition) * food.max_servings_per_day
        for food in foods
    )
    if maximum_protein + 1e-6 < constraints.protein_min_g:
        raise OptimizationInfeasibleError(
            f"eligible foods can supply at most {maximum_protein:.1f} robust protein g/day"
        )
    if maximum_fiber + 1e-6 < constraints.fiber_min_g:
        raise OptimizationInfeasibleError(f"eligible foods can supply at most {maximum_fiber:.1f} robust fiber g/day")


def _build_problem(
    foods: list[FoodItem],
    constraints: DietConstraints,
    objectives: DietObjectiveWeights,
) -> tuple[np.ndarray, np.ndarray, Bounds, LinearConstraint, _Layout]:
    layout = _Layout(constraints.days, len(foods))
    c = np.zeros(layout.size)
    integrality = np.zeros(layout.size, dtype=int)
    lower_bounds = np.zeros(layout.size)
    upper_bounds = np.full(layout.size, np.inf)

    for day in range(layout.days):
        for food_index, food in enumerate(foods):
            x = layout.x(day, food_index)
            y = layout.y(day, food_index)
            robust_price = food.price * (1 + food.price_uncertainty if constraints.robust_price else 1)
            c[x] = objectives.cost * robust_price + objectives.prep_time * food.prep_minutes
            # A tiny deterministic perturbation breaks equivalent day permutations.
            c[y] = (
                objectives.food_count
                + objectives.preference * (1 - food.preference_score)
                + 1e-7 * (day + 1) * (food_index + 1)
            )
            integrality[x] = 1
            integrality[y] = 1
            upper_bounds[x] = food.max_servings_per_day
            upper_bounds[y] = 1
        c[layout.positive_deviation(day)] = objectives.calorie_deviation
        c[layout.negative_deviation(day)] = objectives.calorie_deviation
    for food_index in range(layout.foods):
        integrality[layout.z(food_index)] = 1
        upper_bounds[layout.z(food_index)] = 1

    rows: list[np.ndarray] = []
    lowers: list[float] = []
    uppers: list[float] = []

    def add(row: np.ndarray, lower: float = -np.inf, upper: float = np.inf) -> None:
        rows.append(row)
        lowers.append(lower)
        uppers.append(upper)

    for day in range(layout.days):
        for food_index, food in enumerate(foods):
            link_upper = np.zeros(layout.size)
            link_upper[layout.x(day, food_index)] = 1
            link_upper[layout.y(day, food_index)] = -food.max_servings_per_day
            add(link_upper, upper=0)

            link_lower = np.zeros(layout.size)
            link_lower[layout.x(day, food_index)] = 1
            link_lower[layout.y(day, food_index)] = -1
            add(link_lower, lower=0)

            global_link = np.zeros(layout.size)
            global_link[layout.y(day, food_index)] = 1
            global_link[layout.z(food_index)] = -1
            add(global_link, upper=0)

        calorie_lower = np.zeros(layout.size)
        calorie_upper = np.zeros(layout.size)
        protein_lower = np.zeros(layout.size)
        fiber_lower = np.zeros(layout.size)
        sodium_upper = np.zeros(layout.size)
        price_upper = np.zeros(layout.size)
        prep_upper = np.zeros(layout.size)
        calorie_mean = np.zeros(layout.size)
        for food_index, food in enumerate(foods):
            x = layout.x(day, food_index)
            calorie_lower[x] = _coefficient(food, "calories_kcal", "lower", constraints.robust_nutrition)
            calorie_upper[x] = _coefficient(food, "calories_kcal", "upper", constraints.robust_nutrition)
            protein_lower[x] = _coefficient(food, "protein_g", "lower", constraints.robust_nutrition)
            fiber_lower[x] = _coefficient(food, "fiber_g", "lower", constraints.robust_nutrition)
            sodium_upper[x] = _coefficient(food, "sodium_mg", "upper", constraints.robust_nutrition)
            price_upper[x] = food.price * (1 + food.price_uncertainty if constraints.robust_price else 1)
            prep_upper[x] = food.prep_minutes
            calorie_mean[x] = food.calories_kcal
        add(calorie_lower, lower=constraints.calories_min)
        add(calorie_upper, upper=constraints.calories_max)
        add(protein_lower, lower=constraints.protein_min_g)
        add(fiber_lower, lower=constraints.fiber_min_g)
        if constraints.sodium_max_mg is not None:
            add(sodium_upper, upper=constraints.sodium_max_mg)
        add(price_upper, upper=constraints.budget_max_per_day)
        add(prep_upper, upper=constraints.prep_minutes_max_per_day)

        for nutrient, required in constraints.micronutrient_min.items():
            micro = np.zeros(layout.size)
            for food_index, food in enumerate(foods):
                amount = float(food.micronutrients.get(nutrient, 0.0))
                if constraints.robust_nutrition:
                    amount *= 1 - food.nutrient_uncertainty
                micro[layout.x(day, food_index)] = amount
            add(micro, lower=required)

        target = (constraints.calories_min + constraints.calories_max) / 2
        calorie_mean[layout.positive_deviation(day)] = -1
        calorie_mean[layout.negative_deviation(day)] = 1
        add(calorie_mean, lower=target, upper=target)

    for food_index in range(layout.foods):
        days_used = np.zeros(layout.size)
        for day in range(layout.days):
            days_used[layout.y(day, food_index)] = 1
        add(days_used, upper=constraints.max_days_per_food)

        z_used = np.zeros(layout.size)
        z_used[layout.z(food_index)] = 1
        for day in range(layout.days):
            z_used[layout.y(day, food_index)] = -1
        add(z_used, upper=0)

    unique = np.zeros(layout.size)
    for food_index in range(layout.foods):
        unique[layout.z(food_index)] = 1
    add(unique, lower=constraints.min_unique_foods)

    matrix = np.vstack(rows)
    return (
        c,
        integrality,
        Bounds(lower_bounds, upper_bounds),
        LinearConstraint(matrix, np.asarray(lowers), np.asarray(uppers)),
        layout,
    )


def _summarize(
    solution: np.ndarray,
    foods: list[FoodItem],
    constraints: DietConstraints,
    layout: _Layout,
    *,
    status: str,
    objective_value: float,
    solver_message: str,
    mip_gap: float | None,
) -> DietPlanResult:
    entries: list[MealPlanEntry] = []
    daily_summaries: list[DailyPlanSummary] = []
    all_servings = 0
    quality_weighted = 0.0
    robust_total_cost = 0.0
    for day in range(layout.days):
        selected: list[tuple[FoodItem, int]] = []
        for food_index, food in enumerate(foods):
            servings = round(solution[layout.x(day, food_index)])
            if servings <= 0:
                continue
            selected.append((food, servings))
            all_servings += servings
            quality_weighted += servings * food.data_quality_score
            entries.append(
                MealPlanEntry(
                    day=day + 1,
                    food_id=food.food_id,
                    food_name=food.name,
                    servings=servings,
                    grams=food.serving_g * servings,
                    calories_kcal=food.calories_kcal * servings,
                    protein_g=food.protein_g * servings,
                    fiber_g=food.fiber_g * servings,
                    cost=food.price * servings,
                    prep_minutes=food.prep_minutes * servings,
                    data_quality_score=food.data_quality_score,
                )
            )

        def total(field: str, selected_items: list[tuple[FoodItem, int]] = selected) -> float:
            return float(sum(float(getattr(food, field)) * count for food, count in selected_items))

        robust_calories_lower = sum(
            _coefficient(food, "calories_kcal", "lower", constraints.robust_nutrition) * count
            for food, count in selected
        )
        robust_calories_upper = sum(
            _coefficient(food, "calories_kcal", "upper", constraints.robust_nutrition) * count
            for food, count in selected
        )
        robust_protein = sum(
            _coefficient(food, "protein_g", "lower", constraints.robust_nutrition) * count for food, count in selected
        )
        robust_fiber = sum(
            _coefficient(food, "fiber_g", "lower", constraints.robust_nutrition) * count for food, count in selected
        )
        robust_cost = sum(
            food.price * (1 + food.price_uncertainty if constraints.robust_price else 1) * count
            for food, count in selected
        )
        robust_total_cost += robust_cost
        servings_count = max(sum(count for _, count in selected), 1)
        daily_summaries.append(
            DailyPlanSummary(
                day=day + 1,
                calories_kcal=total("calories_kcal"),
                robust_calories_lower=robust_calories_lower,
                robust_calories_upper=robust_calories_upper,
                protein_g=total("protein_g"),
                robust_protein_lower_g=robust_protein,
                fiber_g=total("fiber_g"),
                robust_fiber_lower_g=robust_fiber,
                sodium_mg=total("sodium_mg"),
                cost=total("price"),
                robust_cost_upper=robust_cost,
                prep_minutes=total("prep_minutes"),
                preference_score=sum(food.preference_score * count for food, count in selected) / servings_count,
            )
        )
    used_foods = {entry.food_id for entry in entries}
    slack = {
        "minimum_robust_calories": min(
            item.robust_calories_lower - constraints.calories_min for item in daily_summaries
        ),
        "maximum_robust_calories": min(
            constraints.calories_max - item.robust_calories_upper for item in daily_summaries
        ),
        "minimum_robust_protein": min(
            item.robust_protein_lower_g - constraints.protein_min_g for item in daily_summaries
        ),
        "minimum_robust_fiber": min(item.robust_fiber_lower_g - constraints.fiber_min_g for item in daily_summaries),
        "maximum_robust_cost": min(constraints.budget_max_per_day - item.robust_cost_upper for item in daily_summaries),
        "maximum_prep_minutes": min(
            constraints.prep_minutes_max_per_day - item.prep_minutes for item in daily_summaries
        ),
    }
    warnings: list[str] = []
    quality = quality_weighted / max(all_servings, 1)
    if quality < 0.75:
        warnings.append("serving-weighted source data quality is below 0.75")
    if status != "optimal":
        gap_text = "unknown" if mip_gap is None else f"{mip_gap:.1%}"
        warnings.append(f"solver stopped at the time limit with a disclosed MIP gap of {gap_text}")
    if min(slack.values()) < 1e-5:
        warnings.append("at least one constraint is binding; small input changes may alter feasibility")
    sensitivity = _stress_test(entries, foods, constraints)
    independent_validation = validate_weekly_plan(entries, foods, constraints)
    if not independent_validation.feasible:
        raise OptimizationInfeasibleError(
            "solver returned a plan that failed independent validation: " + ", ".join(independent_validation.violations)
        )
    return DietPlanResult(
        status=status,
        solver_message=solver_message,
        mip_gap=mip_gap,
        objective_value=objective_value,
        entries=entries,
        daily=daily_summaries,
        total_cost=sum(item.cost for item in entries),
        robust_total_cost_upper=robust_total_cost,
        unique_foods=len(used_foods),
        weighted_data_quality=quality,
        constraint_slack=slack,
        independent_validation=independent_validation,
        sensitivity=sensitivity,
        warnings=warnings,
        assumptions=[
            "Nutrient values are treated as per-serving averages.",
            "Robust bounds use the user-visible uncertainty fraction, not a clinical guarantee.",
            "Price, availability, recipes, cooking yield, and adherence may differ in practice.",
            "The user supplies targets; CutSignal does not determine an appropriate calorie deficit.",
        ],
    )


def _stress_test(
    entries: list[MealPlanEntry],
    foods: list[FoodItem],
    constraints: DietConstraints,
) -> list[PlanSensitivityResult]:
    """Evaluate the chosen plan under visible coefficient shocks without re-optimizing."""
    food_lookup = {food.food_id: food for food in foods}
    by_day: dict[int, list[tuple[FoodItem, int]]] = {
        day: [(food_lookup[entry.food_id], entry.servings) for entry in entries if entry.day == day]
        for day in range(1, constraints.days + 1)
    }
    scenarios = {
        "modeled-robust-bounds": (0.0, 0.0),
        "nutrition-uncertainty-plus-5-points": (0.05, 0.0),
        "nutrition-uncertainty-plus-10-points": (0.10, 0.0),
        "price-plus-10-percent": (0.0, 0.10),
        "price-plus-20-percent": (0.0, 0.20),
    }
    results: list[PlanSensitivityResult] = []
    for scenario, (nutrition_shock, price_shock) in scenarios.items():
        slacks: dict[str, list[float]] = {
            "calories_min": [],
            "calories_max": [],
            "protein_min": [],
            "fiber_min": [],
            "cost_max": [],
            "prep_max": [],
        }
        if constraints.sodium_max_mg is not None:
            slacks["sodium_max"] = []
        for nutrient in constraints.micronutrient_min:
            slacks[f"micronutrient_{nutrient}_min"] = []
        for day in range(1, constraints.days + 1):
            selected = by_day[day]

            def robust_total(
                field: str,
                mode: str,
                selected_items: list[tuple[FoodItem, int]] = selected,
                nutrition_delta: float = nutrition_shock,
            ) -> float:
                total = 0.0
                for food, servings in selected_items:
                    base = _coefficient(food, field, mode, constraints.robust_nutrition)
                    shock = 1 - nutrition_delta if mode == "lower" else 1 + nutrition_delta
                    total += base * shock * servings
                return total

            slacks["calories_min"].append(robust_total("calories_kcal", "lower") - constraints.calories_min)
            slacks["calories_max"].append(constraints.calories_max - robust_total("calories_kcal", "upper"))
            slacks["protein_min"].append(robust_total("protein_g", "lower") - constraints.protein_min_g)
            slacks["fiber_min"].append(robust_total("fiber_g", "lower") - constraints.fiber_min_g)
            robust_cost = sum(
                food.price
                * (1 + food.price_uncertainty if constraints.robust_price else 1)
                * (1 + price_shock)
                * servings
                for food, servings in selected
            )
            slacks["cost_max"].append(constraints.budget_max_per_day - robust_cost)
            prep = sum(food.prep_minutes * servings for food, servings in selected)
            slacks["prep_max"].append(constraints.prep_minutes_max_per_day - prep)
            if constraints.sodium_max_mg is not None:
                slacks["sodium_max"].append(constraints.sodium_max_mg - robust_total("sodium_mg", "upper"))
            for nutrient, required in constraints.micronutrient_min.items():
                amount = sum(
                    float(food.micronutrients.get(nutrient, 0.0))
                    * (1 - food.nutrient_uncertainty if constraints.robust_nutrition else 1)
                    * (1 - nutrition_shock)
                    * servings
                    for food, servings in selected
                )
                slacks[f"micronutrient_{nutrient}_min"].append(amount - required)
        minimum = {name: float(min(values)) for name, values in slacks.items()}
        violations = sorted(name for name, value in minimum.items() if value < -1e-6)
        results.append(
            PlanSensitivityResult(
                scenario=scenario,
                feasible=not violations,
                minimum_slack_by_constraint=minimum,
                violations=violations,
            )
        )
    return results


def _solve_pulp(
    foods: list[FoodItem],
    constraints: DietConstraints,
    objectives: DietObjectiveWeights,
    time_limit_seconds: float,
) -> tuple[np.ndarray, str, float, float | None]:
    """Solve the weekly MILP with the open-source HiGHS solver."""
    layout = _Layout(constraints.days, len(foods))
    problem = pulp.LpProblem("cutsignal_weekly_diet", pulp.LpMinimize)
    x = {
        (day, food_index): problem.add_variable(
            f"x_{day}_{food_index}",
            lowBound=0,
            upBound=food.max_servings_per_day,
            cat=pulp.LpInteger,
        )
        for day in range(layout.days)
        for food_index, food in enumerate(foods)
    }
    y = {
        (day, food_index): problem.add_variable(f"y_{day}_{food_index}", cat=pulp.LpBinary)
        for day in range(layout.days)
        for food_index in range(layout.foods)
    }
    z = {food_index: problem.add_variable(f"z_{food_index}", cat=pulp.LpBinary) for food_index in range(layout.foods)}
    target = (constraints.calories_min + constraints.calories_max) / 2
    positive_deviation = {
        day: problem.add_variable(f"positive_deviation_{day}", lowBound=0) for day in range(layout.days)
    }
    negative_deviation = {
        day: problem.add_variable(f"negative_deviation_{day}", lowBound=0) for day in range(layout.days)
    }

    for day in range(layout.days):
        for food_index, food in enumerate(foods):
            problem += x[day, food_index] <= food.max_servings_per_day * y[day, food_index]
            problem += x[day, food_index] >= y[day, food_index]
            problem += y[day, food_index] <= z[food_index]

        problem += (
            pulp.lpSum(
                _coefficient(food, "calories_kcal", "lower", constraints.robust_nutrition) * x[day, index]
                for index, food in enumerate(foods)
            )
            >= constraints.calories_min
        )
        problem += (
            pulp.lpSum(
                _coefficient(food, "calories_kcal", "upper", constraints.robust_nutrition) * x[day, index]
                for index, food in enumerate(foods)
            )
            <= constraints.calories_max
        )
        problem += (
            pulp.lpSum(
                _coefficient(food, "protein_g", "lower", constraints.robust_nutrition) * x[day, index]
                for index, food in enumerate(foods)
            )
            >= constraints.protein_min_g
        )
        problem += (
            pulp.lpSum(
                _coefficient(food, "fiber_g", "lower", constraints.robust_nutrition) * x[day, index]
                for index, food in enumerate(foods)
            )
            >= constraints.fiber_min_g
        )
        problem += (
            pulp.lpSum(
                food.price * (1 + food.price_uncertainty if constraints.robust_price else 1) * x[day, index]
                for index, food in enumerate(foods)
            )
            <= constraints.budget_max_per_day
        )
        problem += (
            pulp.lpSum(food.prep_minutes * x[day, index] for index, food in enumerate(foods))
            <= constraints.prep_minutes_max_per_day
        )
        if constraints.sodium_max_mg is not None:
            problem += (
                pulp.lpSum(
                    _coefficient(food, "sodium_mg", "upper", constraints.robust_nutrition) * x[day, index]
                    for index, food in enumerate(foods)
                )
                <= constraints.sodium_max_mg
            )
        for nutrient, required in constraints.micronutrient_min.items():
            problem += (
                pulp.lpSum(
                    float(food.micronutrients.get(nutrient, 0.0))
                    * (1 - food.nutrient_uncertainty if constraints.robust_nutrition else 1)
                    * x[day, index]
                    for index, food in enumerate(foods)
                )
                >= required
            )

        problem += (
            pulp.lpSum(food.calories_kcal * x[day, index] for index, food in enumerate(foods))
            - positive_deviation[day]
            + negative_deviation[day]
            == target
        )

    for food_index in range(layout.foods):
        problem += pulp.lpSum(y[day, food_index] for day in range(layout.days)) <= constraints.max_days_per_food
        problem += z[food_index] <= pulp.lpSum(y[day, food_index] for day in range(layout.days))
    problem += pulp.lpSum(z.values()) >= constraints.min_unique_foods

    objective_terms: list[pulp.LpAffineExpression] = []
    for day in range(layout.days):
        for food_index, food in enumerate(foods):
            robust_price = food.price * (1 + food.price_uncertainty if constraints.robust_price else 1)
            x_cost = objectives.cost * robust_price + objectives.prep_time * food.prep_minutes
            y_cost = (
                objectives.food_count
                + objectives.preference * (1 - food.preference_score)
                + 1e-7 * (day + 1) * (food_index + 1)
            )
            objective_terms.append(x_cost * x[day, food_index])
            objective_terms.append(y_cost * y[day, food_index])
        objective_terms.append(objectives.calorie_deviation * positive_deviation[day])
        objective_terms.append(objectives.calorie_deviation * negative_deviation[day])
    problem += pulp.lpSum(objective_terms)

    solver = pulp.HiGHS(
        msg=False,
        timeLimit=time_limit_seconds,
        gapRel=0.001,
        threads=1,
        random_seed=20260820,
    )
    problem.solve(solver)
    solver_model = cast(Any, problem.solverModel)
    info = solver_model.getInfo()
    model_status = str(solver_model.modelStatusToString(solver_model.getModelStatus()))
    has_solution = int(info.primal_solution_status) == 2
    if not has_solution:
        raise OptimizationInfeasibleError(
            f"weekly diet optimization failed ({model_status}); review all constraints together"
        )
    status = "optimal" if model_status == "Optimal" else "feasible_time_limit"
    solution = np.zeros(layout.size)
    for day in range(layout.days):
        for food_index in range(layout.foods):
            solution[layout.x(day, food_index)] = float(pulp.value(x[day, food_index]))
            solution[layout.y(day, food_index)] = float(pulp.value(y[day, food_index]))
    for food_index in range(layout.foods):
        solution[layout.z(food_index)] = float(pulp.value(z[food_index]))
    objective = float(pulp.value(problem.objective))
    gap = float(info.mip_gap) if np.isfinite(float(info.mip_gap)) else None
    return solution, status, objective, gap


def optimize_weekly_plan(
    foods: list[FoodItem],
    constraints: DietConstraints,
    objectives: DietObjectiveWeights | None = None,
    *,
    time_limit_seconds: float = 30.0,
) -> DietPlanResult:
    """Solve the robust weekly MILP and disclose incumbent status and MIP gap."""
    if not np.isfinite(time_limit_seconds) or not 0 < time_limit_seconds <= MAX_SOLVER_SECONDS:
        raise ValueError(f"time_limit_seconds must be greater than 0 and at most {MAX_SOLVER_SECONDS:g}")
    selected = _eligible(foods, constraints)
    _preflight(selected, constraints)
    weights = objectives or DietObjectiveWeights()
    layout = _Layout(constraints.days, len(selected))
    solution, status, objective, mip_gap = _solve_pulp(selected, constraints, weights, time_limit_seconds)
    return _summarize(
        solution,
        selected,
        constraints,
        layout,
        status=status,
        objective_value=objective,
        solver_message=f"PuLP HiGHS: {status}",
        mip_gap=mip_gap,
    )


def build_pareto_frontier(
    foods: list[FoodItem],
    constraints: DietConstraints,
    *,
    time_limit_seconds: float = 5.0,
) -> list[PlanPoint]:
    """Return a sampled non-dominated set from five explicit weighted objectives.

    This is not an exhaustive Pareto frontier. Weighted-sum sampling can miss
    non-convex or unsampled trade-offs in a discrete feasible region.
    """
    profiles = {
        "balanced": DietObjectiveWeights(),
        "lowest-cost": DietObjectiveWeights(
            cost=3.0, prep_time=0.05, calorie_deviation=0.01, preference=0.1, food_count=0.05
        ),
        "fast-prep": DietObjectiveWeights(
            cost=0.2, prep_time=3.0, calorie_deviation=0.01, preference=0.2, food_count=0.05
        ),
        "preference-first": DietObjectiveWeights(
            cost=0.2, prep_time=0.1, calorie_deviation=0.01, preference=4.0, food_count=0.05
        ),
        "simple": DietObjectiveWeights(cost=0.5, prep_time=0.2, calorie_deviation=0.01, preference=0.5, food_count=2.0),
    }
    points: list[PlanPoint] = []
    seen: set[tuple[float, float, float, int]] = set()
    for label, weights in profiles.items():
        plan = optimize_weekly_plan(
            foods,
            constraints,
            weights,
            time_limit_seconds=time_limit_seconds,
        )
        servings = sum(entry.servings for entry in plan.entries)
        mean_preference = sum(
            item.preference_score * sum(entry.servings for entry in plan.entries if entry.food_id == item.food_id)
            for item in foods
        ) / max(servings, 1)
        point = PlanPoint(
            label=label,
            total_cost=plan.total_cost,
            total_prep_minutes=sum(item.prep_minutes for item in plan.daily),
            mean_preference=mean_preference,
            unique_foods=plan.unique_foods,
        )
        key = (
            round(point.total_cost, 4),
            round(point.total_prep_minutes, 4),
            round(point.mean_preference, 4),
            point.unique_foods,
        )
        if key not in seen:
            seen.add(key)
            points.append(point)
    frontier: list[PlanPoint] = []
    for candidate in points:
        dominated = any(
            other.total_cost <= candidate.total_cost
            and other.total_prep_minutes <= candidate.total_prep_minutes
            and other.mean_preference >= candidate.mean_preference
            and (
                other.total_cost < candidate.total_cost
                or other.total_prep_minutes < candidate.total_prep_minutes
                or other.mean_preference > candidate.mean_preference
            )
            for other in points
        )
        if not dominated:
            frontier.append(candidate)
    return sorted(frontier, key=lambda item: (item.total_cost, item.total_prep_minutes))
