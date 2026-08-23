from __future__ import annotations

import pytest

from cutsignal.cases import get_case, list_cases, run_case, verify_cases


def test_case_catalog_is_unique_and_bounded() -> None:
    cases = list_cases()
    assert len(cases) == 8
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
