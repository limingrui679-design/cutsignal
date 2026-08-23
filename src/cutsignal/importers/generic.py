"""Device-independent daily CSV importer with explicit column aliases."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from cutsignal.exceptions import DataValidationError
from cutsignal.importers.common import optional_float, parse_date, weight_to_kg
from cutsignal.input_safety import MAX_TABULAR_BYTES, validate_file_size, validate_row_count
from cutsignal.models import DailyObservation, SourceRef

ALIASES: dict[str, tuple[str, ...]] = {
    "date": ("date", "day", "timestamp", "datetime"),
    "weight_kg": ("weight_kg", "bodyweight_kg", "body_weight_kg", "weight"),
    "weight_lb": ("weight_lb", "bodyweight_lb", "body_weight_lb"),
    "energy_intake_kcal": (
        "energy_intake_kcal",
        "calories_kcal",
        "calorie_intake",
        "calories",
        "kcal",
    ),
    "active_energy_kcal": ("active_energy_kcal", "active_calories", "calories_burned"),
    "steps": ("steps", "step_count"),
    "sleep_hours": ("sleep_hours", "sleep_duration_hours", "sleep"),
    "training_minutes": ("training_minutes", "exercise_minutes", "workout_minutes"),
    "resting_hr_bpm": ("resting_hr_bpm", "resting_heart_rate", "rhr"),
    "hrv_ms": ("hrv_ms", "hrv", "heart_rate_variability_ms"),
}


def _column_map(columns: list[str]) -> dict[str, str]:
    normalized = {column.strip().casefold(): column for column in columns}
    mapping: dict[str, str] = {}
    for target, aliases in ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[target] = normalized[alias]
                break
    if "date" not in mapping:
        raise DataValidationError("daily CSV needs a date/day/timestamp column")
    if len(mapping) == 1:
        raise DataValidationError("daily CSV contains no recognized health metrics")
    return mapping


def import_daily_csv(path: Path, provider: str = "generic-csv") -> list[DailyObservation]:
    """Load rows and aggregate repeated dates without silently summing body weight."""
    validate_file_size(path, MAX_TABULAR_BYTES, "daily CSV")
    frame = pd.read_csv(path)
    validate_row_count(len(frame), "daily CSV")
    mapping = _column_map([str(column) for column in frame.columns])
    rows: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for raw in frame.to_dict(orient="records"):
        day = parse_date(raw[mapping["date"]])
        parsed: dict[str, Any] = {}
        for target, column in mapping.items():
            if target == "date":
                continue
            parsed[target] = optional_float(raw.get(column))
        if parsed.get("weight_lb") is not None and parsed.get("weight_kg") is None:
            parsed["weight_kg"] = weight_to_kg(parsed.pop("weight_lb"), "lb")
        else:
            parsed.pop("weight_lb", None)
        rows[day].append(parsed)

    observations: list[DailyObservation] = []
    sum_fields = {"energy_intake_kcal", "active_energy_kcal", "steps", "training_minutes"}
    mean_fields = {"sleep_hours", "resting_hr_bpm", "hrv_ms"}
    for day in sorted(rows):
        values = rows[day]
        output: dict[str, Any] = {"date": day}
        weights = [row["weight_kg"] for row in values if row.get("weight_kg") is not None]
        if weights:
            output["weight_kg"] = float(np.median(weights))
        for field in sum_fields:
            present = [row[field] for row in values if row.get(field) is not None]
            if present:
                total = sum(present)
                output[field] = round(total) if field == "steps" else total
        for field in mean_fields:
            present = [row[field] for row in values if row.get(field) is not None]
            if present:
                output[field] = float(np.mean(present))
        output["sources"] = [SourceRef(provider=provider, record_type="daily-summary")]
        output["quality_flags"] = {"aggregated_duplicate_date"} if len(values) > 1 else set()
        observations.append(DailyObservation.model_validate(output))
    return observations
