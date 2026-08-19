"""Shared parsing and unit-normalization helpers."""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

import pandas as pd

from cutsignal.exceptions import DataValidationError

DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S %z",
    "%Y-%m-%d %H:%M:%S.%f %z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%d",
)


def parse_datetime(value: str) -> datetime:
    text = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DataValidationError(f"unsupported datetime: {value!r}") from exc
    return parsed


def parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        raise DataValidationError("missing date")
    try:
        return pd.to_datetime(str(value), errors="raise").date()
    except (TypeError, ValueError) as exc:
        raise DataValidationError(f"unsupported date: {value!r}") from exc


def optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise DataValidationError(f"expected a number, received {value!r}") from exc
    if not math.isfinite(number):
        return None
    return number


def weight_to_kg(value: float, unit: str | None) -> float:
    normalized = (unit or "kg").strip().lower()
    if normalized in {"kg", "kilogram", "kilograms"}:
        return value
    if normalized in {"lb", "lbs", "pound", "pounds"}:
        return value * 0.45359237
    if normalized in {"stone", "st"}:
        return value * 6.35029318
    raise DataValidationError(f"unsupported weight unit: {unit!r}")


def energy_to_kcal(value: float, unit: str | None) -> float:
    normalized = (unit or "kcal").strip().lower()
    if normalized in {"kcal", "cal", "calorie", "calories"}:
        return value
    if normalized in {"kj", "kilojoule", "kilojoules"}:
        return value / 4.184
    raise DataValidationError(f"unsupported energy unit: {unit!r}")


def normalize_name(value: str) -> str:
    return " ".join(value.strip().casefold().replace("_", " ").split())
