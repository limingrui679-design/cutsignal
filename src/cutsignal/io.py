"""Deterministic JSONL and CSV persistence for validated domain models."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import TypeVar

import pandas as pd
from pydantic import BaseModel

from cutsignal.exceptions import DataValidationError
from cutsignal.input_safety import (
    MAX_JSONL_BYTES,
    MAX_JSONL_LINE_BYTES,
    MAX_ROWS,
    MAX_TABULAR_BYTES,
    validate_file_size,
    validate_row_count,
)
from cutsignal.models import DailyObservation, FoodItem, StrengthSet

ModelT = TypeVar("ModelT", bound=BaseModel)


def write_jsonl(records: Iterable[BaseModel], path: Path) -> Path:
    """Stream models to a same-directory temporary file, then replace atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(record.model_dump_json(exclude_none=True))
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return path


def read_jsonl(path: Path, model: type[ModelT]) -> list[ModelT]:
    validate_file_size(path, MAX_JSONL_BYTES, "JSONL input")
    records: list[ModelT] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line_number > MAX_ROWS:
                raise DataValidationError(f"JSONL input exceeds {MAX_ROWS} rows")
            if not line.strip():
                continue
            if len(line.encode("utf-8")) > MAX_JSONL_LINE_BYTES:
                raise DataValidationError(f"JSONL line {line_number} exceeds {MAX_JSONL_LINE_BYTES} bytes")
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
    validate_file_size(path, MAX_TABULAR_BYTES, "food CSV")
    frame = pd.read_csv(path)
    validate_row_count(len(frame), "food CSV")
    records: list[FoodItem] = []
    for item in frame.to_dict(orient="records"):
        for set_field in ("allergens", "tags"):
            raw = item.get(set_field)
            if isinstance(raw, str):
                item[set_field] = {part.strip().lower() for part in raw.split("|") if part.strip()}
            elif pd.isna(raw):
                item[set_field] = set()
        micro = item.get("micronutrients")
        if isinstance(micro, str) and micro.strip():
            item["micronutrients"] = json.loads(micro)
        elif pd.isna(micro):
            item["micronutrients"] = {}
        raw_source = item.get("source")
        if isinstance(raw_source, str) and raw_source.strip():
            item["source"] = json.loads(raw_source)
        records.append(FoodItem.model_validate(item))
    return records
