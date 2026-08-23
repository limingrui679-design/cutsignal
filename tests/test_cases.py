from __future__ import annotations

from typing import NoReturn

import pytest

from cutsignal.cases import get_case, list_cases, run_case, verify_cases
from cutsignal.exceptions import OptimizationInfeasibleError


def test_case_catalog_is_unique_and_bounded() -> None:
    cases = list_cases()
    assert len(cases) == 9
    assert len({case.id for case in cases}) == len(cases)
    assert all(case.evidence_type == "deterministic_synthetic_fixture" for case in cases)
    assert all(case.capabilities and case.limitations for case in cases)
    with pytest.raises(ValueError, match="unknown case"):
        get_case("not-a-case")


@pytest.mark.slow
def test_every_case_exposes_and_passes_its_assertions() -> None:
    results = verify_cases(optimizer_seconds=2)
    assert {item.case_id for item in results} == {item.id for item in list_cases()}
    assert all(item.assertions for item in results)
    assert all(item.configuration for item in results)
    assert all(item.passed for item in results), {item.case_id: item.assertions for item in results if not item.passed}


def test_device_case_is_directly_runnable() -> None:
    result = run_case("device-overlap-reconciliation")
    assert result.passed
    assert result.observed["steps"] == 8_000


def test_generic_migration_case_is_directly_runnable() -> None:
    result = run_case("generic-schema-migration")
    assert result.passed
    assert result.observed["first_day_steps"] == 7_700


def test_case_verifier_retains_expected_domain_failures(monkeypatch) -> None:
    def fail_case(case_id: str, *, optimizer_seconds: float = 2.0) -> NoReturn:
        raise OptimizationInfeasibleError(f"synthetic failure for {case_id} at {optimizer_seconds}")

    monkeypatch.setattr("cutsignal.cases.run_case", fail_case)

    results = verify_cases(optimizer_seconds=0.25)

    assert len(results) == len(list_cases())
    assert all(not item.passed for item in results)
    assert all(item.assertions == {"case_execution": False} for item in results)
    assert all(item.observed["error_type"] == "OptimizationInfeasibleError" for item in results)
