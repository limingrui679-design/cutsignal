from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from cutsignal.app import _read_uploaded_constraints, _read_uploaded_jsonl
from cutsignal.cli import app
from cutsignal.input_safety import MAX_CONSTRAINT_BYTES
from cutsignal.models import DailyObservation
from cutsignal.synthetic import (
    generate_daily_demo,
    generate_food_demo,
    generate_strength_demo,
)

runner = CliRunner()


def test_cli_version_help_and_daily_import(tmp_path) -> None:
    version = runner.invoke(app, ["version"])
    assert version.exit_code == 0
    assert version.stdout.strip() == "0.2.0"
    help_result = runner.invoke(app, ["--help"])
    assert help_result.exit_code == 0
    assert "device-independent" in runner.invoke(app, ["import", "--help"]).stdout

    source = tmp_path / "daily.csv"
    destination = tmp_path / "daily.jsonl"
    source.write_text("date,weight_kg,calories\n2026-01-01,80,2000\n", encoding="utf-8")
    result = runner.invoke(app, ["import", "daily-csv", str(source), str(destination)])
    assert result.exit_code == 0
    assert destination.exists()
    assert "1" in result.stdout

    invalid = tmp_path / "invalid.csv"
    invalid.write_text("unknown,value\na,b\n", encoding="utf-8")
    rejected = runner.invoke(app, ["import", "daily-csv", str(invalid), str(destination)])
    assert rejected.exit_code == 2
    assert "Input error:" in rejected.stderr
    assert "Traceback" not in rejected.stderr

    unknown_case = runner.invoke(app, ["cases", "run", "not-a-case"])
    assert unknown_case.exit_code == 2
    assert "unknown case" in unknown_case.stderr
    assert "Traceback" not in unknown_case.stderr

    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    oversized_constraints = tmp_path / "constraints.json"
    oversized_constraints.write_bytes(b" " * (MAX_CONSTRAINT_BYTES + 1))
    oversized = runner.invoke(
        app,
        [
            "analyze",
            "--daily",
            str(empty),
            "--strength",
            str(empty),
            "--foods",
            str(empty),
            "--constraints",
            str(oversized_constraints),
        ],
    )
    assert oversized.exit_code == 2
    assert "constraint JSON" in oversized.stderr


def test_cli_privacy_exit_and_app_jsonl_parser(tmp_path) -> None:
    clean = tmp_path / "safe.txt"
    clean.write_text("synthetic", encoding="utf-8")
    assert runner.invoke(app, ["privacy-audit", str(clean)]).exit_code == 0
    export = tmp_path / "apple-health.zip"
    export.write_bytes(b"placeholder")
    assert runner.invoke(app, ["privacy-audit", str(export)]).exit_code == 1

    payload = b'{"date":"2026-01-01","weight_kg":80}\n'
    rows = _read_uploaded_jsonl(payload, DailyObservation)
    assert rows[0].weight_kg == 80
    bad = b'{"date":"invalid","weight_kg":80}\n'
    try:
        _read_uploaded_jsonl(bad, DailyObservation)
    except ValueError as exc:
        assert "line 1" in str(exc)
    else:
        raise AssertionError("invalid app JSONL was accepted")
    with pytest.raises(ValueError, match="constraint JSON exceeds"):
        _read_uploaded_constraints(b" " * (MAX_CONSTRAINT_BYTES + 1))


def test_synthetic_generators_are_deterministic_and_labelled() -> None:
    first = generate_daily_demo(days=20)
    second = generate_daily_demo(days=20)
    assert first == second
    strength = generate_strength_demo(first)
    foods = generate_food_demo()
    assert strength
    assert foods
    assert all(item.source.provider == "CutSignal synthetic generator" for item in strength)
    assert all(item.data_quality_score == 0.55 for item in foods)
    assert json.loads(first[0].model_dump_json())["sources"][0]["record_type"] == "daily-demo"
