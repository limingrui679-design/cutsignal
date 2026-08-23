"""Shared local-input limits that bound accidental memory and parser abuse."""

from __future__ import annotations

from pathlib import Path

from cutsignal.exceptions import DataValidationError

MAX_TABULAR_BYTES = 100 * 1024 * 1024
MAX_JSONL_BYTES = 100 * 1024 * 1024
MAX_JSONL_LINE_BYTES = 2 * 1024 * 1024
MAX_CONSTRAINT_BYTES = 1 * 1024 * 1024
MAX_ROWS = 1_000_000
MAX_UI_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_UI_ROWS = 100_000


def validate_file_size(path: Path, maximum_bytes: int, label: str) -> None:
    size = path.stat().st_size
    if size > maximum_bytes:
        raise DataValidationError(f"{label} is {size} bytes; configured maximum is {maximum_bytes} bytes")


def validate_row_count(count: int, label: str, maximum_rows: int = MAX_ROWS) -> None:
    if count > maximum_rows:
        raise DataValidationError(f"{label} has {count} rows; configured maximum is {maximum_rows}")
