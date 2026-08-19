"""Validated domain models shared by importers and analysis modules."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

UnitInterval = Annotated[float, Field(ge=0.0, le=1.0)]
PositiveFloat = Annotated[float, Field(gt=0.0)]
NonNegativeFloat = Annotated[float, Field(ge=0.0)]


class SourceRef(BaseModel):
    """Provenance for one imported or derived value."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    record_type: str
    source_id: str | None = None
    device: str | None = None
    original_unit: str | None = None
    confidence: UnitInterval = 1.0


class DailyObservation(BaseModel):
    """One privacy-preserving daily row used by the energy model."""

    model_config = ConfigDict(extra="forbid")

    date: date
    weight_kg: Annotated[float | None, Field(gt=20, lt=400)] = None
    energy_intake_kcal: Annotated[float | None, Field(ge=0, le=20_000)] = None
    active_energy_kcal: Annotated[float | None, Field(ge=0, le=10_000)] = None
    steps: Annotated[int | None, Field(ge=0, le=200_000)] = None
    sleep_hours: Annotated[float | None, Field(ge=0, le=24)] = None
    training_minutes: Annotated[float | None, Field(ge=0, le=1_440)] = None
    resting_hr_bpm: Annotated[float | None, Field(ge=20, le=250)] = None
    hrv_ms: Annotated[float | None, Field(ge=0, le=1_000)] = None
    sources: list[SourceRef] = Field(default_factory=list)
    quality_flags: set[str] = Field(default_factory=set)

    @model_validator(mode="after")
    def require_signal(self) -> DailyObservation:
        fields = (
            self.weight_kg,
            self.energy_intake_kcal,
            self.active_energy_kcal,
            self.steps,
            self.sleep_hours,
            self.training_minutes,
            self.resting_hr_bpm,
            self.hrv_ms,
        )
        if all(value is None for value in fields) and "missing_day" not in self.quality_flags:
            raise ValueError("a daily observation must contain at least one measurement")
        return self


class StrengthSet(BaseModel):
    """Normalized working-set record from Hevy, Strong, or a generic CSV."""

    model_config = ConfigDict(extra="forbid")

    date: date
    exercise: str = Field(min_length=1, max_length=120)
    weight_kg: Annotated[float, Field(ge=0, le=1_500)]
    reps: Annotated[int, Field(ge=1, le=200)]
    rpe: Annotated[float | None, Field(ge=1, le=10)] = None
    set_type: Literal["working", "warmup", "drop", "failure", "unknown"] = "working"
    bodyweight_kg: Annotated[float | None, Field(gt=20, lt=400)] = None
    duration_seconds: Annotated[float | None, Field(ge=0, le=86_400)] = None
    source: SourceRef
    quality_flags: set[str] = Field(default_factory=set)

    @field_validator("exercise")
    @classmethod
    def normalize_exercise(cls, value: str) -> str:
        return " ".join(value.strip().split())


class FoodItem(BaseModel):
    """One candidate serving for the robust weekly diet optimizer."""

    model_config = ConfigDict(extra="forbid")

    food_id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    serving_g: PositiveFloat
    calories_kcal: NonNegativeFloat
    protein_g: NonNegativeFloat
    fiber_g: NonNegativeFloat = 0.0
    carbs_g: NonNegativeFloat = 0.0
    fat_g: NonNegativeFloat = 0.0
    sodium_mg: NonNegativeFloat = 0.0
    micronutrients: dict[str, NonNegativeFloat] = Field(default_factory=dict)
    price: NonNegativeFloat
    prep_minutes: NonNegativeFloat = 0.0
    preference_score: UnitInterval = 0.5
    nutrient_uncertainty: UnitInterval = 0.05
    price_uncertainty: UnitInterval = 0.05
    data_quality_score: UnitInterval = 1.0
    category: str = "other"
    allergens: set[str] = Field(default_factory=set)
    tags: set[str] = Field(default_factory=set)
    max_servings_per_day: Annotated[int, Field(ge=1, le=20)] = 4
    source: SourceRef

    @model_validator(mode="after")
    def validate_macro_energy(self) -> FoodItem:
        macro_kcal = self.protein_g * 4 + self.carbs_g * 4 + self.fat_g * 9
        if self.calories_kcal > 0 and macro_kcal > self.calories_kcal * 1.8:
            raise ValueError("macronutrients are inconsistent with declared calories")
        return self


class DietConstraints(BaseModel):
    """User-controlled limits; no defaults are presented as medical advice."""

    model_config = ConfigDict(extra="forbid")

    days: Annotated[int, Field(ge=1, le=14)] = 7
    calories_min: PositiveFloat
    calories_max: PositiveFloat
    protein_min_g: NonNegativeFloat
    fiber_min_g: NonNegativeFloat = 0.0
    sodium_max_mg: PositiveFloat | None = None
    micronutrient_min: dict[str, NonNegativeFloat] = Field(default_factory=dict)
    budget_max_per_day: PositiveFloat
    prep_minutes_max_per_day: PositiveFloat
    max_days_per_food: Annotated[int, Field(ge=1, le=14)] = 4
    min_unique_foods: Annotated[int, Field(ge=1, le=100)] = 6
    excluded_allergens: set[str] = Field(default_factory=set)
    required_tags: set[str] = Field(default_factory=set)
    forbidden_tags: set[str] = Field(default_factory=set)
    robust_nutrition: bool = True
    robust_price: bool = True

    @model_validator(mode="after")
    def validate_bounds(self) -> DietConstraints:
        if self.calories_min > self.calories_max:
            raise ValueError("calories_min must not exceed calories_max")
        if self.max_days_per_food > self.days:
            raise ValueError("max_days_per_food must not exceed days")
        return self


class DietObjectiveWeights(BaseModel):
    """Normalized objective trade-offs for the multi-objective optimizer."""

    model_config = ConfigDict(extra="forbid")

    cost: NonNegativeFloat = 1.0
    prep_time: NonNegativeFloat = 0.25
    calorie_deviation: NonNegativeFloat = 0.01
    preference: NonNegativeFloat = 1.0
    food_count: NonNegativeFloat = 0.1

    @model_validator(mode="after")
    def require_objective(self) -> DietObjectiveWeights:
        if sum(self.model_dump().values()) <= 0:
            raise ValueError("at least one objective weight must be positive")
        return self
