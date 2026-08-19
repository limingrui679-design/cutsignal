"""FoodData Central and Open Food Facts normalization helpers."""

from __future__ import annotations

from typing import Any

import httpx

from cutsignal.exceptions import DataValidationError
from cutsignal.models import FoodItem, SourceRef

USDA_API_ROOT = "https://api.nal.usda.gov/fdc/v1"
OFF_API_ROOT = "https://world.openfoodfacts.org/api/v3.6/product"
USER_AGENT = "CutSignal/0.1 (open-source fitness analytics; contact via GitHub)"


def _nutrient_map(food_nutrients: list[dict[str, Any]]) -> dict[str, float]:
    values: dict[str, float] = {}
    for entry in food_nutrients:
        nutrient = entry.get("nutrient", entry)
        name = str(nutrient.get("name") or entry.get("nutrientName") or "").casefold()
        amount = entry.get("amount", entry.get("value"))
        if amount is None:
            continue
        values[name] = float(amount)
    return values


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
    nutrients = _nutrient_map(list(payload.get("foodNutrients", [])))

    def find(*names: str) -> float:
        for name in names:
            for key, value in nutrients.items():
                if name in key:
                    return value
        return 0.0

    calories = find("energy")
    if calories > 2_000:  # USDA may expose energy in kJ before kcal.
        calories /= 4.184
    description = str(payload.get("description") or payload.get("lowercaseDescription") or "")
    fdc_id = str(payload.get("fdcId") or "")
    if not description or not fdc_id:
        raise DataValidationError("USDA payload needs description and fdcId")
    required_present = sum(value > 0 for value in (calories, find("protein"), find("total dietary fiber", "fiber")))
    quality = 0.75 + required_present / 3 * 0.25
    return FoodItem(
        food_id=f"usda:{fdc_id}",
        name=description.title(),
        serving_g=100,
        calories_kcal=calories,
        protein_g=find("protein"),
        fiber_g=find("total dietary fiber", "fiber"),
        carbs_g=find("carbohydrate, by difference", "carbohydrate"),
        fat_g=find("total lipid", "total fat"),
        sodium_mg=find("sodium"),
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
    with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
        response = client.get(f"{USDA_API_ROOT}/food/{fdc_id}", params={"api_key": api_key})
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload


def fetch_open_food_facts(barcode: str, timeout: float = 20.0) -> dict[str, Any]:
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
    with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
        response = client.get(f"{OFF_API_ROOT}/{barcode}.json", params={"fields": fields})
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
    if payload.get("status") == "failure":
        raise DataValidationError(f"Open Food Facts product not found: {barcode}")
    return payload
