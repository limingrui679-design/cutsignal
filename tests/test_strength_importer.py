from __future__ import annotations

import pytest

from cutsignal.exceptions import DataValidationError
from cutsignal.importers.strength import import_strength_csv


def test_hevy_and_strong_detection(tmp_path) -> None:
    hevy = tmp_path / "hevy-export.csv"
    hevy.write_text(
        "start_time,exercise_title,weight_kg,reps,rpe,set_type\n"
        "2026-01-01 10:00:00,Bench Press,80,5,8,normal\n"
        "2026-01-01 10:00:00,Bench Press,20,10,,warmup\n",
        encoding="utf-8",
    )
    hevy_rows = import_strength_csv(hevy)
    assert len(hevy_rows) == 2
    assert hevy_rows[0].source.provider == "hevy"
    assert {item.set_type for item in hevy_rows} == {"working", "warmup"}

    strong = tmp_path / "strong.csv"
    strong.write_text(
        "Date,Workout Name,Exercise Name,Weight,Reps,RPE,Set Type\n2026-01-02,Upper,Bench Press,176,5,8,Normal\n",
        encoding="utf-8",
    )
    row = import_strength_csv(strong)[0]
    assert row.source.provider == "strong"
    assert row.weight_kg == pytest.approx(79.832, abs=0.01)


def test_strength_import_quality_and_errors(tmp_path) -> None:
    path = tmp_path / "generic.csv"
    path.write_text(
        "date,exercise,weight_kg,reps\n2026-01-01,Squat,100,31\n2026-01-01,Squat,,5\n",
        encoding="utf-8",
    )
    rows = import_strength_csv(path, provider="manual-log")
    assert rows[0].source.provider == "manual-log"
    assert "high_rep_set" in rows[0].quality_flags

    missing = tmp_path / "missing.csv"
    missing.write_text("date,exercise,reps\n2026-01-01,Squat,5\n", encoding="utf-8")
    with pytest.raises(DataValidationError, match="weight"):
        import_strength_csv(missing)

    none = tmp_path / "none.csv"
    none.write_text("date,exercise,weight_kg,reps\n2026-01-01,Squat,,\n", encoding="utf-8")
    with pytest.raises(DataValidationError, match="no usable"):
        import_strength_csv(none)
