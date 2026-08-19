from __future__ import annotations

import json
from datetime import date

import pytest
from pydantic import ValidationError

from cutsignal.io import read_daily, read_foods, read_jsonl, write_jsonl
from cutsignal.models import (
    DailyObservation,
    DietConstraints,
    DietObjectiveWeights,
    FoodItem,
    SourceRef,
    StrengthSet,
)


def test_domain_validation_and_defaults(source: SourceRef) -> None:
    with pytest.raises(ValidationError, match="at least one measurement"):
        DailyObservation(date=date(2026, 1, 1))
    missing = DailyObservation(date=date(2026, 1, 1), quality_flags={"missing_day"})
    assert missing.weight_kg is None

    strength = StrengthSet(
        date=date(2026, 1, 1),
        exercise="  Bench   Press ",
        weight_kg=80,
        reps=5,
        source=source,
    )
    assert strength.exercise == "Bench Press"
    assert strength.set_type == "working"

    with pytest.raises(ValidationError, match="macronutrients"):
        FoodItem(
            food_id="bad",
            name="Bad food",
            serving_g=100,
            calories_kcal=10,
            protein_g=20,
            carbs_g=20,
            fat_g=10,
            price=1,
            source=source,
        )
    with pytest.raises(ValidationError, match="calories_min"):
        DietConstraints(
            calories_min=2_000,
            calories_max=1_000,
            protein_min_g=0,
            budget_max_per_day=10,
            prep_minutes_max_per_day=30,
        )
    with pytest.raises(ValidationError, match="objective"):
        DietObjectiveWeights(cost=0, prep_time=0, calorie_deviation=0, preference=0, food_count=0)


def test_jsonl_round_trip_and_invalid_line(tmp_path) -> None:
    path = tmp_path / "daily.jsonl"
    rows = [DailyObservation(date=date(2026, 1, 1), weight_kg=80)]
    assert write_jsonl(rows, path) == path
    assert read_daily(path) == rows
    assert read_jsonl(path, DailyObservation) == rows
    path.write_text('{"date":"bad"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="record at"):
        read_daily(path)


def test_read_food_csv_sets_and_micros(tmp_path, source: SourceRef) -> None:
    source_json = json.dumps(source.model_dump(mode="json"))
    escaped_source = source_json.replace(chr(34), chr(34) * 2)
    path = tmp_path / "foods.csv"
    path.write_text(
        "food_id,name,serving_g,calories_kcal,protein_g,fiber_g,carbs_g,fat_g,price,tags,allergens,micronutrients,source\n"
        f'f1,Beans,100,120,8,7,20,1,0.5,vegan|vegetarian,,"{{""iron"":2.1}}","{escaped_source}"\n',
        encoding="utf-8",
    )
    # CSV cannot directly construct nested Pydantic source objects from JSON text;
    # normalized JSONL is the lossless interchange format.
    with pytest.raises(ValidationError):
        read_foods(path)

    jsonl = tmp_path / "foods.jsonl"
    item = FoodItem(
        food_id="f1",
        name="Beans",
        serving_g=100,
        calories_kcal=120,
        protein_g=8,
        fiber_g=7,
        carbs_g=20,
        fat_g=1,
        price=0.5,
        tags={"vegan"},
        micronutrients={"iron": 2.1},
        source=source,
    )
    write_jsonl([item], jsonl)
    assert read_foods(jsonl)[0].micronutrients["iron"] == pytest.approx(2.1)
