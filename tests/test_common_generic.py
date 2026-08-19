from __future__ import annotations

from datetime import date

import pytest

from cutsignal.exceptions import DataValidationError
from cutsignal.importers.common import (
    energy_to_kcal,
    normalize_name,
    optional_float,
    parse_date,
    parse_datetime,
    weight_to_kg,
)
from cutsignal.importers.generic import import_daily_csv


def test_common_parsers_and_units() -> None:
    assert parse_datetime("2026-01-02 08:30:00 +0800").date() == date(2026, 1, 2)
    assert parse_datetime("2026-01-02T00:30:00Z").tzinfo is not None
    assert parse_date("2026/01/03") == date(2026, 1, 3)
    assert optional_float("") is None
    assert optional_float(float("nan")) is None
    assert optional_float("2.5") == 2.5
    assert weight_to_kg(100, "lb") == pytest.approx(45.359237)
    assert weight_to_kg(10, "stone") == pytest.approx(63.5029318)
    assert energy_to_kcal(418.4, "kJ") == pytest.approx(100)
    assert normalize_name("  Heart_Rate  ") == "heart rate"
    with pytest.raises(DataValidationError):
        parse_datetime("yesterday-ish")
    with pytest.raises(DataValidationError):
        optional_float("many")
    with pytest.raises(DataValidationError):
        weight_to_kg(1, "ounce")
    with pytest.raises(DataValidationError):
        energy_to_kcal(1, "watt")


def test_generic_csv_aggregates_duplicate_dates(tmp_path) -> None:
    path = tmp_path / "tracker.csv"
    path.write_text(
        "day,weight_lb,calories,steps,sleep\n"
        "2026-01-01,176,900,4000,7\n"
        "2026-01-01,177,1100,5000,8\n"
        "2026-01-02,175,2000,9500,7.5\n",
        encoding="utf-8",
    )
    rows = import_daily_csv(path, provider="multi-device-export")
    assert len(rows) == 2
    assert rows[0].weight_kg == pytest.approx(80.059, abs=0.01)
    assert rows[0].energy_intake_kcal == 2_000
    assert rows[0].steps == 9_000
    assert rows[0].sleep_hours == 7.5
    assert "aggregated_duplicate_date" in rows[0].quality_flags
    assert rows[0].sources[0].provider == "multi-device-export"


@pytest.mark.parametrize("header", ["unknown,value", "date,unknown"])
def test_generic_csv_rejects_unknown_schema(tmp_path, header: str) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(header + "\n2026-01-01,1\n", encoding="utf-8")
    with pytest.raises(DataValidationError):
        import_daily_csv(path)
