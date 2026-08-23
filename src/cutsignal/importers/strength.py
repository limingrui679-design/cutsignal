"""Hevy, Strong, and generic resistance-training CSV adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from cutsignal.exceptions import DataValidationError
from cutsignal.importers.common import optional_float, parse_date, weight_to_kg
from cutsignal.input_safety import MAX_TABULAR_BYTES, validate_file_size, validate_row_count
from cutsignal.models import SourceRef, StrengthSet

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "date": ("date", "start_time", "start time", "workout_date"),
    "exercise": ("exercise", "exercise_title", "exercise name", "exercise_name"),
    "weight_kg": ("weight_kg", "weight kg", "weight (kg)"),
    "weight_lb": ("weight_lb", "weight lbs", "weight (lb)", "weight"),
    "reps": ("reps", "repetitions"),
    "rpe": ("rpe", "rating of perceived exertion"),
    "set_type": ("set_type", "set type", "type"),
    "duration_seconds": ("duration_seconds", "seconds", "duration"),
    "bodyweight_kg": ("bodyweight_kg", "body weight kg"),
}


SET_TYPES = {
    "normal": "working",
    "working": "working",
    "warmup": "warmup",
    "warm-up": "warmup",
    "dropset": "drop",
    "drop": "drop",
    "failure": "failure",
}


def _detect_provider(columns: set[str]) -> str:
    if "exercise_title" in columns or "start_time" in columns:
        return "hevy"
    if "exercise name" in columns or "workout name" in columns:
        return "strong"
    return "generic-strength-csv"


def _mapping(columns: list[str]) -> dict[str, str]:
    normalized = {column.strip().casefold(): column for column in columns}
    mapping: dict[str, str] = {}
    for target, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[target] = normalized[alias]
                break
    missing = {"date", "exercise", "reps"} - mapping.keys()
    if missing:
        raise DataValidationError(f"strength CSV is missing required fields: {sorted(missing)}")
    if "weight_kg" not in mapping and "weight_lb" not in mapping:
        raise DataValidationError("strength CSV needs weight_kg or weight_lb")
    return mapping


def import_strength_csv(path: Path, provider: str | None = None) -> list[StrengthSet]:
    validate_file_size(path, MAX_TABULAR_BYTES, "strength CSV")
    frame = pd.read_csv(path)
    validate_row_count(len(frame), "strength CSV")
    columns = [str(column) for column in frame.columns]
    mapping = _mapping(columns)
    selected_provider = provider or _detect_provider({column.strip().casefold() for column in columns})
    output: list[StrengthSet] = []
    for index, row in enumerate(frame.to_dict(orient="records"), start=2):
        try:
            reps_value = optional_float(row.get(mapping["reps"]))
            if reps_value is None or reps_value < 1:
                continue
            if "weight_kg" in mapping:
                raw_weight = optional_float(row.get(mapping["weight_kg"]))
                unit = "kg"
            else:
                raw_weight = optional_float(row.get(mapping["weight_lb"]))
                unit = "lb"
            if raw_weight is None:
                continue
            raw_type = str(row.get(mapping.get("set_type", ""), "unknown")).strip().casefold()
            set_type = SET_TYPES.get(raw_type, "unknown")
            item: dict[str, Any] = {
                "date": parse_date(row[mapping["date"]]),
                "exercise": str(row[mapping["exercise"]]),
                "weight_kg": weight_to_kg(raw_weight, unit),
                "reps": round(reps_value),
                "rpe": optional_float(row.get(mapping.get("rpe", ""))),
                "set_type": set_type,
                "duration_seconds": optional_float(row.get(mapping.get("duration_seconds", ""))),
                "bodyweight_kg": optional_float(row.get(mapping.get("bodyweight_kg", ""))),
                "source": SourceRef(
                    provider=selected_provider,
                    record_type="strength-set",
                    source_id=f"row-{index}",
                    original_unit=unit,
                ),
            }
            if reps_value > 30:
                item["quality_flags"] = {"high_rep_set"}
            output.append(StrengthSet.model_validate(item))
        except (ValueError, TypeError) as exc:
            raise DataValidationError(f"invalid strength record at CSV row {index}: {exc}") from exc
    if not output:
        raise DataValidationError("strength CSV contained no usable sets")
    return sorted(output, key=lambda item: (item.date, item.exercise))
