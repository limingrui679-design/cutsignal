"""FoodData Central and Open Food Facts normalization helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from cutsignal.exceptions import DataValidationError
from cutsignal.models import FoodItem, SourceRef

USDA_API_ROOT = "https://api.nal.usda.gov/fdc/v1"
OFF_API_ROOT = "https://world.openfoodfacts.org/api/v3.6/product"
USER_AGENT = "CutSignal/0.2 (local fitness analytics client)"
MAX_FOOD_API_BYTES = 5 * 1024 * 1024
_FDC_ID = re.compile(r"[0-9]{1,12}")
_BARCODE = re.compile(r"[0-9]{4,32}")


@dataclass(frozen=True)
class _NutrientValue:
    name: str
    amount: float
    unit: str
    nutrient_id: int | None


def _nutrient_values(food_nutrients: list[dict[str, Any]]) -> list[_NutrientValue]:
    values: list[_NutrientValue] = []
    for entry in food_nutrients:
        nutrient = entry.get("nutrient", entry)
        name = str(nutrient.get("name") or entry.get("nutrientName") or "").casefold()
        amount = entry.get("amount", entry.get("value"))
        if not name or amount is None:
            continue
        raw_id = nutrient.get("id", entry.get("nutrientId"))
        try:
            nutrient_id = int(raw_id) if raw_id is not None else None
        except (TypeError, ValueError):
            nutrient_id = None
        values.append(
            _NutrientValue(
                name=name,
                amount=float(amount),
                unit=str(nutrient.get("unitName") or entry.get("unitName") or "").strip().casefold(),
                nutrient_id=nutrient_id,
            )
        )
    return values


def _convert_unit(value: _NutrientValue, target: str) -> float:
    # Unicode case-folding maps the micro sign (U+00B5) to Greek mu (U+03BC).
    unit = value.unit.replace("µ", "u").replace("μ", "u")
    if not unit:
        # Older fixture payloads and some user-created extracts omit unitName.
        # USDA canonical targets are kcal, g, and mg for the fields used here.
        return value.amount
    if target == "kcal":
        if unit in {"kcal", "calorie", "calories"}:
            return value.amount
        if unit in {"kj", "kilojoule", "kilojoules"}:
            return value.amount / 4.184
    elif target == "g":
        if unit in {"g", "gram", "grams"}:
            return value.amount
        if unit in {"mg", "milligram", "milligrams"}:
            return value.amount / 1_000
        if unit in {"ug", "mcg", "microgram", "micrograms"}:
            return value.amount / 1_000_000
    elif target == "mg":
        if unit in {"mg", "milligram", "milligrams"}:
            return value.amount
        if unit in {"g", "gram", "grams"}:
            return value.amount * 1_000
        if unit in {"ug", "mcg", "microgram", "micrograms"}:
            return value.amount / 1_000
    raise DataValidationError(f"unsupported USDA nutrient unit {value.unit!r} for {value.name!r}")


def _find_nutrient(
    nutrients: list[_NutrientValue],
    *names: str,
    target_unit: str,
    preferred_ids: tuple[int, ...] = (),
) -> float:
    candidates = [item for item in nutrients if any(name in item.name for name in names)]
    if not candidates:
        return 0.0
    priorities = {nutrient_id: index for index, nutrient_id in enumerate(preferred_ids)}
    selected = min(
        enumerate(candidates),
        key=lambda pair: (
            priorities.get(pair[1].nutrient_id, len(priorities))
            if pair[1].nutrient_id is not None
            else len(priorities),
            pair[0],
        ),
    )[1]
    return _convert_unit(selected, target_unit)


def _validated_identifier(value: str, pattern: re.Pattern[str], label: str) -> str:
    normalized = value.strip()
    if pattern.fullmatch(normalized) is None:
        raise DataValidationError(f"invalid {label}: {value!r}")
    return normalized


def _fetch_json(url: str, *, params: dict[str, str], timeout: float) -> dict[str, Any]:
    content = bytearray()
    with (
        httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as client,
        client.stream("GET", url, params=params) as response,
    ):
        response.raise_for_status()
        content_length = response.headers.get("content-length")
        if content_length is not None:
            try:
                reported_size = int(content_length)
            except ValueError as exc:
                raise DataValidationError("food API returned an invalid content-length header") from exc
            if reported_size < 0:
                raise DataValidationError("food API returned an invalid content-length header")
            if reported_size > MAX_FOOD_API_BYTES:
                raise DataValidationError("food API response exceeds the configured size limit")
        for chunk in response.iter_bytes():
            if len(content) + len(chunk) > MAX_FOOD_API_BYTES:
                raise DataValidationError("food API response exceeds the configured size limit")
            content.extend(chunk)
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DataValidationError("food API returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise DataValidationError("food API response must be a JSON object")
    return payload


def food_from_usda(
    payload: dict[str, Any],
    *,
    price_per_100g: float,
    prep_minutes: float = 0.0,
    preference_score: float = 0.5,
    category: str = "other",
    tags: set[str] | None = None,
    allergens: set[str] | None = None,
) -> FoodItem:
    """Normalize one USDA details response as a 100 g candidate serving."""
    nutrients = _nutrient_values(list(payload.get("foodNutrients", [])))
    calories = _find_nutrient(
        nutrients,
        "energy",
        target_unit="kcal",
        # 1008 is the cross-data-type Energy field. Foundation Foods may
        # instead expose the newer Atwater specific/general IDs 2048/2047.
        preferred_ids=(1008, 2048, 2047),
    )
    protein = _find_nutrient(nutrients, "protein", target_unit="g", preferred_ids=(1003,))
    fiber = _find_nutrient(
        nutrients,
        "total dietary fiber",
        "fiber, total dietary",
        "fiber",
        target_unit="g",
        preferred_ids=(1079,),
    )
    description = str(payload.get("description") or payload.get("lowercaseDescription") or "")
    fdc_id = str(payload.get("fdcId") or "")
    if not description or not fdc_id:
        raise DataValidationError("USDA payload needs description and fdcId")
    required_present = sum(value > 0 for value in (calories, protein, fiber))
    quality = 0.75 + required_present / 3 * 0.25
    return FoodItem(
        food_id=f"usda:{fdc_id}",
        name=description.title(),
        serving_g=100,
        calories_kcal=calories,
        protein_g=protein,
        fiber_g=fiber,
        carbs_g=_find_nutrient(
            nutrients,
            "carbohydrate, by difference",
            "carbohydrate",
            target_unit="g",
            preferred_ids=(1005,),
        ),
        fat_g=_find_nutrient(
            nutrients,
            "total lipid",
            "total fat",
            target_unit="g",
            preferred_ids=(1004,),
        ),
        sodium_mg=_find_nutrient(nutrients, "sodium", target_unit="mg", preferred_ids=(1093,)),
        price=price_per_100g,
        prep_minutes=prep_minutes,
        preference_score=preference_score,
        nutrient_uncertainty=0.03,
        price_uncertainty=0.10,
        data_quality_score=quality,
        category=category,
        tags=tags or set(),
        allergens=allergens or set(),
        source=SourceRef(
            provider="USDA FoodData Central",
            record_type="food-details",
            source_id=fdc_id,
            original_unit="per 100 g",
            confidence=quality,
        ),
    )


def food_from_open_food_facts(
    payload: dict[str, Any],
    *,
    price_per_100g: float,
    prep_minutes: float = 0.0,
    preference_score: float = 0.5,
    category: str = "packaged",
) -> FoodItem:
    """Normalize one OFF product while retaining its crowdsourced-data caveat."""
    product = payload.get("product", payload)
    nutriments = dict(product.get("nutriments") or {})
    code = str(product.get("code") or payload.get("code") or "")
    name = str(product.get("product_name") or product.get("generic_name") or "")
    if not code or not name:
        raise DataValidationError("Open Food Facts payload needs a barcode and product name")

    def number(key: str) -> float:
        raw = nutriments.get(key)
        return float(str(raw)) if raw not in (None, "") else 0.0

    calories = number("energy-kcal_100g")
    if not calories and number("energy_100g"):
        calories = number("energy_100g") / 4.184
    completeness = sum(number(key) > 0 for key in ("energy-kcal_100g", "proteins_100g", "fiber_100g", "fat_100g")) / 4
    quality = min(0.85, 0.45 + 0.40 * completeness)
    allergen_tags = {str(item).split(":")[-1].casefold() for item in product.get("allergens_tags", [])}
    diet_tags: set[str] = set()
    labels = {str(item).casefold() for item in product.get("labels_tags", [])}
    if any("vegetarian" in label for label in labels):
        diet_tags.add("vegetarian")
    if any("vegan" in label for label in labels):
        diet_tags.add("vegan")
    return FoodItem(
        food_id=f"off:{code}",
        name=name,
        serving_g=100,
        calories_kcal=calories,
        protein_g=number("proteins_100g"),
        fiber_g=number("fiber_100g"),
        carbs_g=number("carbohydrates_100g"),
        fat_g=number("fat_100g"),
        sodium_mg=number("sodium_100g") * 1_000,
        price=price_per_100g,
        prep_minutes=prep_minutes,
        preference_score=preference_score,
        nutrient_uncertainty=max(0.10, 0.30 - completeness * 0.15),
        price_uncertainty=0.15,
        data_quality_score=quality,
        category=category,
        allergens=allergen_tags,
        tags=diet_tags,
        source=SourceRef(
            provider="Open Food Facts",
            record_type="product",
            source_id=code,
            original_unit="per 100 g",
            confidence=quality,
        ),
    )


def fetch_usda_food(fdc_id: str, api_key: str, timeout: float = 20.0) -> dict[str, Any]:
    identifier = _validated_identifier(fdc_id, _FDC_ID, "FoodData Central id")
    return _fetch_json(
        f"{USDA_API_ROOT}/food/{identifier}",
        params={"api_key": api_key},
        timeout=timeout,
    )


def fetch_open_food_facts(barcode: str, timeout: float = 20.0) -> dict[str, Any]:
    identifier = _validated_identifier(barcode, _BARCODE, "barcode")
    fields = ",".join(
        [
            "code",
            "product_name",
            "generic_name",
            "nutriments",
            "allergens_tags",
            "labels_tags",
        ]
    )
    payload = _fetch_json(
        f"{OFF_API_ROOT}/{identifier}.json",
        params={"fields": fields},
        timeout=timeout,
    )
    if payload.get("status") == "failure":
        raise DataValidationError(f"Open Food Facts product not found: {identifier}")
    return payload
