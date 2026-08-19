"""Deterministic JSONL and CSV persistence for validated domain models."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import TypeVar

import pandas as pd
from pydantic import BaseModel

from cutsignal.models import DailyObservation, FoodItem, StrengthSet

ModelT = TypeVar("ModelT", bound=BaseModel)


def write_jsonl(records: Iterable[BaseModel], path: Path) -> Path:
    """Write models atomically enough for local CLI workflows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [record.model_dump_json(exclude_none=True) for record in records]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return path


def read_jsonl(path: Path, model: type[ModelT]) -> list[ModelT]:
    records: list[ModelT] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(model.model_validate_json(line))
            except ValueError as exc:
                raise ValueError(f"invalid JSONL record at {path}:{line_number}: {exc}") from exc
    return records


def read_daily(path: Path) -> list[DailyObservation]:
    return read_jsonl(path, DailyObservation)


def read_strength(path: Path) -> list[StrengthSet]:
    return read_jsonl(path, StrengthSet)


def read_foods(path: Path) -> list[FoodItem]:
    if path.suffix.lower() == ".jsonl":
        return read_jsonl(path, FoodItem)
    frame = pd.read_csv(path)
    records: list[FoodItem] = []
    for item in frame.to_dict(orient="records"):
        for set_field in ("allergens", "tags"):
            raw = item.get(set_field)
            if isinstance(raw, str):
                item[set_field] = {part.strip().lower() for part in raw.split("|") if part.strip()}
        micro = item.get("micronutrients")
        if isinstance(micro, str) and micro.strip():
            item["micronutrients"] = json.loads(micro)
        records.append(FoodItem.model_validate(item))
    return records
