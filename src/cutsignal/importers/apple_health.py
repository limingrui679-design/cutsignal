"""Secure, streaming Apple Health export adapter.

Apple Health is one supported source, not a dependency of the analysis core.
Additive records from multiple devices are reconciled per source/day instead of
blindly summed, preventing common iPhone + Watch double counting.
"""

from __future__ import annotations

import zipfile
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import IO, Any

import numpy as np
from defusedxml.ElementTree import iterparse

from cutsignal.exceptions import DataValidationError
from cutsignal.importers.common import energy_to_kcal, parse_datetime, weight_to_kg
from cutsignal.models import DailyObservation, SourceRef

MAX_XML_BYTES = 4 * 1024 * 1024 * 1024
MAX_COMPRESSION_RATIO = 1_500

RECORD_TYPES = {
    "HKQuantityTypeIdentifierBodyMass": "weight_kg",
    "HKQuantityTypeIdentifierStepCount": "steps",
    "HKQuantityTypeIdentifierActiveEnergyBurned": "active_energy_kcal",
    "HKQuantityTypeIdentifierDietaryEnergyConsumed": "energy_intake_kcal",
    "HKQuantityTypeIdentifierRestingHeartRate": "resting_hr_bpm",
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": "hrv_ms",
}

ADDITIVE_FIELDS = {"steps", "active_energy_kcal", "energy_intake_kcal"}
MEDIAN_FIELDS = {"weight_kg", "resting_hr_bpm", "hrv_ms"}
ASLEEP_MARKERS = ("asleep", "core", "deep", "rem")


@dataclass
class _DayBucket:
    additive: dict[str, dict[str, list[float]]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(list)))
    median: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    sleep_intervals: list[tuple[datetime, datetime]] = field(default_factory=list)
    training_minutes: list[float] = field(default_factory=list)
    sources: dict[tuple[str, str, str | None], SourceRef] = field(default_factory=dict)
    flags: set[str] = field(default_factory=set)


def _safe_xml_member(archive: zipfile.ZipFile) -> zipfile.ZipInfo:
    candidates = [
        info
        for info in archive.infolist()
        if not info.is_dir()
        and info.filename.casefold().endswith(".xml")
        and "export_cda" not in info.filename.casefold()
    ]
    if not candidates:
        raise DataValidationError("Apple Health ZIP contains no candidate health XML")
    for info in candidates:
        path = Path(info.filename)
        if path.is_absolute() or ".." in path.parts:
            raise DataValidationError("unsafe path found inside Apple Health ZIP")
        if info.file_size > MAX_XML_BYTES:
            raise DataValidationError("Apple Health XML exceeds the configured safety limit")
        if info.compress_size and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
            raise DataValidationError("suspicious Apple Health ZIP compression ratio")
    return max(candidates, key=lambda info: info.file_size)


def _source(attrs: dict[str, str], record_type: str) -> SourceRef:
    provider = attrs.get("sourceName", "Apple Health")
    device = attrs.get("device")
    key_id = attrs.get("uuid") or attrs.get("creationDate")
    return SourceRef(
        provider=provider,
        record_type=record_type,
        source_id=key_id,
        device=device,
        original_unit=attrs.get("unit"),
        confidence=0.9 if device else 0.8,
    )


def _record_day(attrs: dict[str, str]) -> date:
    return parse_datetime(attrs.get("endDate") or attrs["startDate"]).date()


def _normalized_value(field_name: str, raw_value: str, unit: str | None) -> float:
    value = float(raw_value)
    if field_name == "weight_kg":
        return weight_to_kg(value, unit)
    if field_name in {"active_energy_kcal", "energy_intake_kcal"}:
        return energy_to_kcal(value, unit)
    return value


def _merge_interval_hours(intervals: Iterable[tuple[datetime, datetime]]) -> float:
    ordered = sorted((start, end) for start, end in intervals if end > start)
    if not ordered:
        return 0.0
    merged: list[list[datetime]] = [[ordered[0][0], ordered[0][1]]]
    for start, end in ordered[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return sum((end - start).total_seconds() for start, end in merged) / 3_600


def _parse_stream(handle: IO[bytes]) -> dict[date, _DayBucket]:
    buckets: dict[date, _DayBucket] = defaultdict(_DayBucket)
    try:
        context = iterparse(handle, events=("end",))
        for _, element in context:
            tag = element.tag.rsplit("}", 1)[-1]
            attrs = dict(element.attrib)
            if tag == "Record":
                raw_type = attrs.get("type", "")
                if raw_type == "HKCategoryTypeIdentifierSleepAnalysis":
                    value = attrs.get("value", "").casefold()
                    if any(marker in value for marker in ASLEEP_MARKERS) and "awake" not in value:
                        start = parse_datetime(attrs["startDate"])
                        end = parse_datetime(attrs["endDate"])
                        bucket = buckets[end.date()]
                        bucket.sleep_intervals.append((start, end))
                        ref = _source(attrs, "sleep")
                        bucket.sources[(ref.provider, ref.record_type, ref.device)] = ref
                elif raw_type in RECORD_TYPES and attrs.get("value") is not None:
                    field_name = RECORD_TYPES[raw_type]
                    day = _record_day(attrs)
                    bucket = buckets[day]
                    value = _normalized_value(field_name, attrs["value"], attrs.get("unit"))
                    ref = _source(attrs, field_name)
                    bucket.sources[(ref.provider, ref.record_type, ref.device)] = ref
                    if field_name in ADDITIVE_FIELDS:
                        source_key = f"{ref.provider}|{ref.device or 'unknown-device'}"
                        bucket.additive[field_name][source_key].append(value)
                    elif field_name in MEDIAN_FIELDS:
                        bucket.median[field_name].append(value)
            elif tag == "Workout":
                end_raw = attrs.get("endDate") or attrs.get("startDate")
                duration = attrs.get("duration")
                if end_raw and duration:
                    day = parse_datetime(end_raw).date()
                    unit = attrs.get("durationUnit", "min").casefold()
                    value = float(duration)
                    minutes = value / 60 if unit in {"s", "sec", "second"} else value
                    if unit in {"h", "hr", "hour"}:
                        minutes = value * 60
                    buckets[day].training_minutes.append(minutes)
                    ref = _source(attrs, "workout")
                    buckets[day].sources[(ref.provider, ref.record_type, ref.device)] = ref
            element.clear()
    except (KeyError, TypeError, ValueError) as exc:
        raise DataValidationError(f"malformed Apple Health record: {exc}") from exc
    return buckets


def _open_and_parse(path: Path) -> dict[date, _DayBucket]:
    if path.suffix.casefold() == ".zip":
        try:
            with zipfile.ZipFile(path) as archive:
                member = _safe_xml_member(archive)
                with archive.open(member) as handle:
                    return _parse_stream(handle)
        except zipfile.BadZipFile as exc:
            raise DataValidationError("invalid Apple Health ZIP") from exc
    if path.stat().st_size > MAX_XML_BYTES:
        raise DataValidationError("Apple Health XML exceeds the configured safety limit")
    with path.open("rb") as handle:
        return _parse_stream(handle)


def import_apple_health(path: Path) -> list[DailyObservation]:
    """Import an Apple Health XML/ZIP into device-independent daily rows."""
    buckets = _open_and_parse(path)
    observations: list[DailyObservation] = []
    for day in sorted(buckets):
        bucket = buckets[day]
        values: dict[str, Any] = {"date": day}
        for field_name, source_values in bucket.additive.items():
            source_totals = {source: sum(items) for source, items in source_values.items()}
            if source_totals:
                # Max-source reconciliation avoids double-counting overlapping phone/watch records.
                values[field_name] = max(source_totals.values())
                if len(source_totals) > 1:
                    bucket.flags.add(f"{field_name}_multi_source_reconciled")
        for field_name, items in bucket.median.items():
            if items:
                values[field_name] = float(np.median(items))
                if len(items) > 1:
                    bucket.flags.add(f"{field_name}_daily_median")
        sleep_hours = _merge_interval_hours(bucket.sleep_intervals)
        if sleep_hours:
            values["sleep_hours"] = min(sleep_hours, 24.0)
        if bucket.training_minutes:
            values["training_minutes"] = min(sum(bucket.training_minutes), 1_440.0)
        values["sources"] = list(bucket.sources.values())
        values["quality_flags"] = bucket.flags
        try:
            observations.append(DailyObservation.model_validate(values))
        except ValueError as exc:
            raise DataValidationError(f"invalid aggregate for {day}: {exc}") from exc
    if not observations:
        raise DataValidationError("Apple Health export contains no supported records")
    return observations
