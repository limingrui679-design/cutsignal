from __future__ import annotations

import json
from typing import ClassVar

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


def test_usda_normalization_uses_explicit_ids_and_units() -> None:
    item = food_from_usda(
        {
            "fdcId": 999,
            "description": "unit conversion fixture",
            "foodNutrients": [
                {"nutrient": {"id": 1008, "name": "Energy", "unitName": "kJ"}, "amount": 1_500},
                {"nutrient": {"id": 1003, "name": "Protein", "unitName": "mg"}, "amount": 10_000},
                {"nutrient": {"id": 1079, "name": "Fiber, total dietary", "unitName": "g"}, "amount": 5},
                {"nutrient": {"id": 1093, "name": "Sodium, Na", "unitName": "g"}, "amount": 0.4},
                {
                    "nutrient": {"id": 1005, "name": "Carbohydrate, by difference", "unitName": "µg"},
                    "amount": 2_000_000,
                },
                {"nutrient": {"id": 1004, "name": "Total lipid (fat)", "unitName": "mg"}, "amount": 3_000},
                {
                    "nutrient": {"id": 2047, "name": "Energy (Atwater General Factors)", "unitName": "kcal"},
                    "amount": 999,
                },
            ],
        },
        price_per_100g=1,
    )
    assert item.calories_kcal == pytest.approx(1_500 / 4.184)
    assert item.protein_g == pytest.approx(10)
    assert item.sodium_mg == pytest.approx(400)
    assert item.carbs_g == pytest.approx(2)
    assert item.fat_g == pytest.approx(3)

    with pytest.raises(DataValidationError, match="unsupported USDA nutrient unit"):
        food_from_usda(
            {
                "fdcId": 1000,
                "description": "invalid unit fixture",
                "foodNutrients": [{"nutrient": {"id": 1008, "name": "Energy", "unitName": "watts"}, "amount": 20}],
            },
            price_per_100g=1,
        )


def test_fetch_helpers_with_local_fakes(monkeypatch) -> None:
    class Response:
        def __init__(self) -> None:
            self.headers: dict[str, str] = {}

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self):
            yield json.dumps({"fdcId": 1, "status": "success"}).encode()

    class Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def stream(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(food_module.httpx, "Client", Client)
    assert food_module.fetch_usda_food("1", "local-key")["fdcId"] == 1
    assert food_module.fetch_open_food_facts("1234")["status"] == "success"
    with pytest.raises(DataValidationError, match="FoodData Central id"):
        food_module.fetch_usda_food("../1", "local-key")
    with pytest.raises(DataValidationError, match="barcode"):
        food_module.fetch_open_food_facts("not/a/barcode")


def test_food_api_response_limit(monkeypatch) -> None:
    class Response:
        def __init__(self) -> None:
            self.headers: dict[str, str] = {}

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self):
            yield b'{"status":"success","padding":"'
            yield b"x" * 20
            yield b'"}'

    class Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def stream(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(food_module.httpx, "Client", Client)
    monkeypatch.setattr(food_module, "MAX_FOOD_API_BYTES", 16)
    with pytest.raises(DataValidationError, match="size limit"):
        food_module.fetch_open_food_facts("1234")


@pytest.mark.parametrize(
    ("headers", "body", "message"),
    [
        ({"content-length": "not-an-integer"}, b"{}", "content-length"),
        ({"content-length": "-1"}, b"{}", "content-length"),
        ({"content-length": str(food_module.MAX_FOOD_API_BYTES + 1)}, b"{}", "size limit"),
        ({}, b"not-json", "invalid JSON"),
        ({}, b"[]", "JSON object"),
    ],
)
def test_food_api_rejects_malformed_metadata_and_payloads(monkeypatch, headers, body, message) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self):
            yield body

    response = Response()
    response.headers = headers

    class Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def stream(self, *args, **kwargs):
            return response

    monkeypatch.setattr(food_module.httpx, "Client", Client)
    with pytest.raises(DataValidationError, match=message):
        food_module.fetch_usda_food("123", "local-key")


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
        headers: ClassVar[dict[str, str]] = {
            "content-length": str(len(b"public-snapshot")),
            "etag": '"synthetic-etag"',
            "last-modified": "Sun, 24 Aug 2026 00:00:00 GMT",
        }
        url = "https://cdn.example.invalid/snapshot.zip"

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
    assert manifest["resolved_url"] == "https://cdn.example.invalid/snapshot.zip"
    assert manifest["etag"] == '"synthetic-etag"'
    assert manifest["retrieved_at_utc"].endswith("+00:00")
    saved = json.loads((tmp_path / "snapshot.zip.manifest.json").read_text(encoding="utf-8"))
    assert saved["sha256"] == manifest["sha256"]

    preserved = tmp_path / "preserved.zip"
    preserved.write_bytes(b"existing")
    monkeypatch.setattr(opl, "MAX_SNAPSHOT_BYTES", 5)
    with pytest.raises(DataValidationError, match="download limit"):
        opl.download_snapshot(preserved, url="https://example.invalid/snapshot.zip")
    assert preserved.read_bytes() == b"existing"
    assert not list(tmp_path.glob(".preserved.zip.*.tmp"))

    Stream.headers = {"content-length": "invalid"}
    with pytest.raises(DataValidationError, match="content-length"):
        opl.download_snapshot(preserved, url="https://example.invalid/snapshot.zip")
    assert preserved.read_bytes() == b"existing"
