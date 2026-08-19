from __future__ import annotations

import zipfile

import pytest

from cutsignal.exceptions import DataValidationError
from cutsignal.importers.apple_health import import_apple_health


def _health_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
  <Record type="HKQuantityTypeIdentifierBodyMass" sourceName="Scale" unit="lb" value="176"
    startDate="2026-01-01 07:00:00 +0800" endDate="2026-01-01 07:00:00 +0800"/>
  <Record type="HKQuantityTypeIdentifierBodyMass" sourceName="Scale" unit="lb" value="177"
    startDate="2026-01-01 20:00:00 +0800" endDate="2026-01-01 20:00:00 +0800"/>
  <Record type="HKQuantityTypeIdentifierStepCount" sourceName="Phone" device="phone" unit="count" value="6000"
    startDate="2026-01-01 08:00:00 +0800" endDate="2026-01-01 20:00:00 +0800"/>
  <Record type="HKQuantityTypeIdentifierStepCount" sourceName="Watch" device="watch" unit="count" value="8000"
    startDate="2026-01-01 08:00:00 +0800" endDate="2026-01-01 20:00:00 +0800"/>
  <Record type="HKQuantityTypeIdentifierActiveEnergyBurned" sourceName="Watch" unit="kJ" value="836.8"
    startDate="2026-01-01 08:00:00 +0800" endDate="2026-01-01 20:00:00 +0800"/>
  <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Phone" value="HKCategoryValueSleepAnalysisAsleepCore"
    startDate="2026-01-01 23:00:00 +0800" endDate="2026-01-02 03:00:00 +0800"/>
  <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Phone" value="HKCategoryValueSleepAnalysisAsleepDeep"
    startDate="2026-01-02 02:00:00 +0800" endDate="2026-01-02 07:00:00 +0800"/>
  <Workout sourceName="Gym" duration="1" durationUnit="hr"
    startDate="2026-01-01 18:00:00 +0800" endDate="2026-01-01 19:00:00 +0800"/>
</HealthData>"""


def test_apple_health_streams_and_reconciles_sources(tmp_path) -> None:
    path = tmp_path / "health.xml"
    path.write_text(_health_xml(), encoding="utf-8")
    rows = import_apple_health(path)
    assert len(rows) == 2
    first = rows[0]
    assert first.steps == 8_000
    assert first.active_energy_kcal == pytest.approx(200)
    assert first.training_minutes == 60
    assert first.weight_kg == pytest.approx(80.059, abs=0.01)
    assert "steps_multi_source_reconciled" in first.quality_flags
    assert "weight_kg_daily_median" in first.quality_flags
    assert rows[1].sleep_hours == 8


def test_apple_health_zip_and_failure_modes(tmp_path) -> None:
    zip_path = tmp_path / "health-data.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("apple_health_export/export.xml", _health_xml())
    assert import_apple_health(zip_path)[0].steps == 8_000

    bad_zip = tmp_path / "bad.zip"
    bad_zip.write_bytes(b"not a zip")
    with pytest.raises(DataValidationError, match="invalid"):
        import_apple_health(bad_zip)

    empty = tmp_path / "empty.xml"
    empty.write_text("<HealthData/>", encoding="utf-8")
    with pytest.raises(DataValidationError, match="no supported"):
        import_apple_health(empty)

    unsafe = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(unsafe, "w") as archive:
        archive.writestr("../export.xml", _health_xml())
    with pytest.raises(DataValidationError, match="unsafe"):
        import_apple_health(unsafe)


def test_apple_health_rejects_malformed_supported_record(tmp_path) -> None:
    path = tmp_path / "malformed.xml"
    path.write_text(
        '<HealthData><Record type="HKQuantityTypeIdentifierBodyMass" value="heavy" '
        'startDate="2026-01-01"/></HealthData>',
        encoding="utf-8",
    )
    with pytest.raises(DataValidationError, match="malformed"):
        import_apple_health(path)
