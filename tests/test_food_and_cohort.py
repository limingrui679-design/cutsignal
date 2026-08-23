from __future__ import annotations

import json

import pytest

from cutsignal.exceptions import DataValidationError, InsufficientDataError
from cutsignal.importers import food as food_module
from cutsignal.importers import openpowerlifting as opl
from cutsignal.importers.food import food_from_open_food_facts, food_from_usda


def test_usda_and_open_food_facts_normalization() -> None:
    usda = food_from_usda(
        {
            "fdcId": 123,
            "description": "black beans",
            "foodNutrients": [
                {"nutrient": {"name": "Energy"}, "amount": 132},
                {"nutrient": {"name": "Protein"}, "amount": 8.9},
                {"nutrient": {"name": "Fiber, total dietary"}, "amount": 8.7},
                {"nutrient": {"name": "Carbohydrate, by difference"}, "amount": 24},
                {"nutrient": {"name": "Total lipid (fat)"}, "amount": 0.5},
            ],
        },
        price_per_100g=0.4,
        tags={"vegan"},
    )
    assert usda.food_id == "usda:123"
    assert usda.data_quality_score == 1
    assert "vegan" in usda.tags

    off = food_from_open_food_facts(
        {
            "product": {
                "code": "456",
                "product_name": "Bean snack",
                "nutriments": {
                    "energy-kcal_100g": 200,
                    "proteins_100g": 10,
                    "fiber_100g": 6,
                    "carbohydrates_100g": 30,
                    "fat_100g": 5,
                    "sodium_100g": 0.4,
                },
                "allergens_tags": ["en:soy"],
                "labels_tags": ["en:vegan"],
            }
        },
        price_per_100g=1,
    )
    assert off.food_id == "off:456"
    assert off.sodium_mg == 400
    assert off.allergens == {"soy"}
    assert off.data_quality_score <= 0.85
    with pytest.raises(DataValidationError):
        food_from_usda({}, price_per_100g=1)
    with pytest.raises(DataValidationError):
        food_from_open_food_facts({}, price_per_100g=1)


def test_fetch_helpers_with_local_fakes(monkeypatch) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {"fdcId": 1, "status": "success"}

    class Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def get(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(food_module.httpx, "Client", Client)
    assert food_module.fetch_usda_food("1", "local-key")["fdcId"] == 1
    assert food_module.fetch_open_food_facts("123")["status"] == "success"


def test_openpowerlifting_cohort_and_snapshot_manifest(tmp_path, monkeypatch) -> None:
    csv = tmp_path / "opl.csv"
    csv.write_text(
        "Sex,Equipment,BodyweightKg,TotalKg,Tested\n"
        "M,Raw,80,400,Yes\nM,Raw,82,500,Yes\nM,Raw,81,450,No\nF,Raw,60,300,Yes\n",
        encoding="utf-8",
    )
    result = opl.cohort_percentile(csv, total_kg=450, bodyweight_kg=81, sex="M")
    assert result["cohort_rows"] == 2
    assert result["percentile"] == pytest.approx(0.5)
    with pytest.raises(InsufficientDataError):
        opl.cohort_percentile(csv, total_kg=200, bodyweight_kg=30, sex="F")

    class Stream:
        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self):
            yield b"public"
            yield b"-snapshot"

    monkeypatch.setattr(opl.httpx, "stream", lambda *args, **kwargs: Stream())
    destination = tmp_path / "snapshot.zip"
    manifest = opl.download_snapshot(destination, url="https://example.invalid/snapshot.zip")
    assert manifest["bytes"] == len(b"public-snapshot")
    saved = json.loads((tmp_path / "snapshot.zip.manifest.json").read_text(encoding="utf-8"))
    assert saved["sha256"] == manifest["sha256"]

    preserved = tmp_path / "preserved.zip"
    preserved.write_bytes(b"existing")
    monkeypatch.setattr(opl, "MAX_SNAPSHOT_BYTES", 5)
    with pytest.raises(DataValidationError, match="download limit"):
        opl.download_snapshot(preserved, url="https://example.invalid/snapshot.zip")
    assert preserved.read_bytes() == b"existing"
    assert not list(tmp_path.glob(".preserved.zip.*.tmp"))
