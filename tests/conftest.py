from __future__ import annotations

from datetime import date, timedelta

import pytest

from cutsignal.models import DailyObservation, DietConstraints, FoodItem, SourceRef, StrengthSet
from cutsignal.synthetic import generate_food_demo


@pytest.fixture
def source() -> SourceRef:
    return SourceRef(provider="test-fixture", record_type="test")


@pytest.fixture
def short_daily() -> list[DailyObservation]:
    start = date(2026, 1, 1)
    return [
        DailyObservation(
            date=start + timedelta(days=index),
            weight_kg=80 - index * 0.04,
            energy_intake_kcal=2_000,
            sleep_hours=7.5,
        )
        for index in range(35)
    ]


@pytest.fixture
def repeated_strength(source: SourceRef) -> list[StrengthSet]:
    start = date(2026, 1, 1)
    records: list[StrengthSet] = []
    for index in range(8):
        for set_number in range(3):
            records.append(
                StrengthSet(
                    date=start + timedelta(days=index * 4),
                    exercise="Bench Press",
                    weight_kg=80 + index * 0.2 - set_number,
                    reps=5,
                    rpe=8 + set_number * 0.2,
                    bodyweight_kg=80 - index * 0.1,
                    source=source,
                )
            )
    return records


@pytest.fixture
def demo_foods() -> list[FoodItem]:
    return generate_food_demo()[:12]


@pytest.fixture
def small_constraints() -> DietConstraints:
    return DietConstraints(
        days=2,
        calories_min=1_300,
        calories_max=1_850,
        protein_min_g=75,
        fiber_min_g=15,
        sodium_max_mg=2_500,
        budget_max_per_day=11,
        prep_minutes_max_per_day=95,
        max_days_per_food=2,
        min_unique_foods=4,
    )
