"""Deterministic synthetic demo with known latent changes and no personal data."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from cutsignal.models import (
    DailyObservation,
    DietConstraints,
    FoodItem,
    SourceRef,
    StrengthSet,
)


def generate_daily_demo(days: int = 112, seed: int = 20260820) -> list[DailyObservation]:
    rng = np.random.default_rng(seed)
    start = date(2026, 1, 5)
    true_weight = 82.0
    fluid = 0.0
    output: list[DailyObservation] = []
    for index in range(days):
        day = start + timedelta(days=index)
        tdee = 2_470.0 - min(index, 70) * 1.7
        planned_intake = 2_050.0 if index < 72 else tdee - 20.0
        actual_intake = planned_intake + rng.normal(0, 95)
        true_weight += (actual_intake - tdee) / 7_700 + rng.normal(0, 0.012)
        fluid = 0.72 * fluid + rng.normal(0, 0.23)
        if index % 21 == 19:
            fluid += 0.65
        measured_weight = true_weight + fluid + rng.normal(0, 0.08)
        missing_weight = rng.random() < 0.09
        missing_intake = rng.random() < 0.07
        flags: set[str] = set()
        if index == 50:
            measured_weight += 2.8
            flags.add("synthetic_scale_outlier")
        output.append(
            DailyObservation(
                date=day,
                weight_kg=None if missing_weight else measured_weight,
                energy_intake_kcal=None if missing_intake else max(actual_intake, 1_200),
                active_energy_kcal=max(180, rng.normal(520, 110)),
                steps=max(1_000, int(rng.normal(9_000, 1_700))),
                sleep_hours=float(np.clip(rng.normal(7.2, 0.65), 4.5, 9.5)),
                training_minutes=55.0 if index % 2 == 0 else 0.0,
                resting_hr_bpm=float(np.clip(rng.normal(58, 3), 45, 80)),
                hrv_ms=float(np.clip(rng.normal(56, 9), 20, 100)),
                sources=[
                    SourceRef(
                        provider="CutSignal synthetic generator",
                        record_type="daily-demo",
                        source_id=f"demo-{index:03d}",
                    )
                ],
                quality_flags=flags,
            )
        )
    return output


def generate_strength_demo(daily: list[DailyObservation], seed: int = 20260821) -> list[StrengthSet]:
    rng = np.random.default_rng(seed)
    weights_by_day = {item.date: item.weight_kg for item in daily if item.weight_kg is not None}
    start = daily[0].date
    exercises = {
        "Back Squat": (112.5, -0.00045),
        "Bench Press": (82.5, 0.00012),
        "Romanian Deadlift": (120.0, 0.00008),
    }
    output: list[StrengthSet] = []
    session_index = 0
    for offset in range(0, len(daily), 3):
        day = start + timedelta(days=offset)
        if day > daily[-1].date:
            break
        for exercise_index, (exercise, (base, daily_change)) in enumerate(exercises.items()):
            if (session_index + exercise_index) % 2:
                continue
            latent = base * (1 + daily_change * offset)
            if exercise == "Back Squat" and offset > 78:
                latent *= 1 - 0.0012 * (offset - 78)
            reps = 5
            load = max(20.0, latent / (1 + reps / 30) + rng.normal(0, 1.0))
            rpe = float(np.clip(7.4 + max(offset - 78, 0) * 0.018 + rng.normal(0, 0.25), 6, 10))
            bodyweight = weights_by_day.get(day)
            for set_number in range(3):
                output.append(
                    StrengthSet(
                        date=day,
                        exercise=exercise,
                        weight_kg=max(0, load - set_number * 1.25),
                        reps=reps,
                        rpe=min(10.0, rpe + set_number * 0.2),
                        set_type="working",
                        bodyweight_kg=bodyweight,
                        source=SourceRef(
                            provider="CutSignal synthetic generator",
                            record_type="strength-demo",
                            source_id=f"demo-{session_index}-{exercise_index}-{set_number}",
                        ),
                    )
                )
        session_index += 1
    return output


def generate_food_demo() -> list[FoodItem]:
    """Return plausible but explicitly synthetic values for software demonstration."""
    rows = [
        (
            "chicken",
            "Chicken breast",
            165,
            31,
            0,
            0,
            3.6,
            74,
            1.30,
            12,
            0.82,
            "protein",
            {"omnivore"},
        ),
        (
            "tofu",
            "Firm tofu",
            100,
            12,
            1,
            3,
            8,
            15,
            0.55,
            8,
            0.78,
            "protein",
            {"vegetarian", "vegan"},
        ),
        (
            "lentils",
            "Cooked lentils",
            116,
            9,
            8,
            20,
            0.4,
            4,
            0.38,
            10,
            0.76,
            "legume",
            {"vegetarian", "vegan"},
        ),
        ("eggs", "Whole eggs", 143, 13, 0, 1, 10, 142, 0.70, 6, 0.86, "protein", {"vegetarian"}),
        (
            "yogurt",
            "Plain Greek yogurt",
            100,
            10,
            0,
            4,
            0.4,
            36,
            0.75,
            1,
            0.90,
            "dairy",
            {"vegetarian"},
        ),
        (
            "oats",
            "Rolled oats",
            150,
            5,
            4,
            27,
            3,
            2,
            0.30,
            5,
            0.83,
            "grain",
            {"vegetarian", "vegan"},
        ),
        (
            "rice",
            "Cooked brown rice",
            123,
            3,
            2,
            26,
            1,
            4,
            0.22,
            4,
            0.75,
            "grain",
            {"vegetarian", "vegan"},
        ),
        (
            "potato",
            "Boiled potato",
            87,
            2,
            2,
            20,
            0.1,
            4,
            0.20,
            8,
            0.72,
            "starch",
            {"vegetarian", "vegan"},
        ),
        (
            "broccoli",
            "Steamed broccoli",
            35,
            2.5,
            3,
            7,
            0.4,
            41,
            0.35,
            6,
            0.72,
            "vegetable",
            {"vegetarian", "vegan"},
        ),
        (
            "spinach",
            "Cooked spinach",
            23,
            3,
            2.5,
            4,
            0.3,
            70,
            0.32,
            5,
            0.65,
            "vegetable",
            {"vegetarian", "vegan"},
        ),
        (
            "carrot",
            "Carrots",
            41,
            0.9,
            3,
            10,
            0.2,
            69,
            0.18,
            2,
            0.74,
            "vegetable",
            {"vegetarian", "vegan"},
        ),
        (
            "apple",
            "Apple",
            52,
            0.3,
            2.4,
            14,
            0.2,
            1,
            0.35,
            0,
            0.88,
            "fruit",
            {"vegetarian", "vegan"},
        ),
        (
            "banana",
            "Banana",
            89,
            1.1,
            2.6,
            23,
            0.3,
            1,
            0.28,
            0,
            0.84,
            "fruit",
            {"vegetarian", "vegan"},
        ),
        (
            "salmon",
            "Baked salmon",
            208,
            22,
            0,
            0,
            13,
            59,
            1.75,
            12,
            0.80,
            "protein",
            {"pescatarian"},
        ),
        ("tuna", "Canned tuna", 116, 26, 0, 0, 1, 300, 1.05, 2, 0.76, "protein", {"pescatarian"}),
        (
            "almonds",
            "Almonds",
            174,
            6,
            3.5,
            6,
            15,
            1,
            0.65,
            0,
            0.70,
            "fat",
            {"vegetarian", "vegan"},
        ),
        (
            "olive-oil",
            "Olive oil",
            119,
            0,
            0,
            0,
            13.5,
            0,
            0.32,
            0,
            0.72,
            "fat",
            {"vegetarian", "vegan"},
        ),
        (
            "berries",
            "Mixed berries",
            57,
            0.7,
            3,
            14,
            0.3,
            1,
            0.62,
            0,
            0.91,
            "fruit",
            {"vegetarian", "vegan"},
        ),
    ]
    foods: list[FoodItem] = []
    for (
        food_id,
        name,
        kcal,
        protein,
        fiber,
        carbs,
        fat,
        sodium,
        price,
        prep,
        pref,
        category,
        tags,
    ) in rows:
        foods.append(
            FoodItem(
                food_id=f"synthetic:{food_id}",
                name=name,
                serving_g=100,
                calories_kcal=kcal,
                protein_g=protein,
                fiber_g=fiber,
                carbs_g=carbs,
                fat_g=fat,
                sodium_mg=sodium,
                price=price,
                prep_minutes=prep,
                preference_score=pref,
                nutrient_uncertainty=0.08,
                price_uncertainty=0.12,
                data_quality_score=0.55,
                category=category,
                tags=tags,
                max_servings_per_day=5,
                source=SourceRef(
                    provider="CutSignal synthetic generator",
                    record_type="food-demo",
                    source_id=food_id,
                    confidence=0.55,
                ),
            )
        )
    return foods


def demo_constraints() -> DietConstraints:
    return DietConstraints(
        days=7,
        calories_min=1_750,
        calories_max=2_150,
        protein_min_g=120,
        fiber_min_g=24,
        sodium_max_mg=2_500,
        budget_max_per_day=14,
        prep_minutes_max_per_day=100,
        max_days_per_food=5,
        min_unique_foods=8,
    )
