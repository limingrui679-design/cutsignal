from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from scripts import audit_dependencies
from scripts.audit_dependencies import classify_result, summarize_payload


def test_dependency_audit_payload_distinguishes_clean_and_vulnerable_results() -> None:
    clean = {"dependencies": [{"name": "alpha", "version": "1.0", "vulns": []}]}
    assert summarize_payload(clean) == (1, [])
    assert classify_result(0, json.dumps(clean), "No known vulnerabilities found") == ("passed", 1, [])

    vulnerable = {
        "dependencies": [
            {
                "name": "alpha",
                "version": "1.0",
                "vulns": [{"id": "OSV-TEST-1", "aliases": ["CVE-TEST"], "fix_versions": ["1.1"]}],
            }
        ]
    }
    classification, count, findings = classify_result(1, json.dumps(vulnerable), "")
    assert classification == "vulnerabilities_found"
    assert count == 1
    assert findings == [
        {
            "dependency": "alpha",
            "installed_version": "1.0",
            "id": "OSV-TEST-1",
            "aliases": ["CVE-TEST"],
            "fix_versions": ["1.1"],
        }
    ]


@pytest.mark.parametrize(
    ("returncode", "stdout", "stderr", "expected"),
    [
        (1, "", "HTTPSConnectionPool: connection refused", "transport_error"),
        (1, "not-json", "service unavailable (HTTP 503)", "transport_error"),
        (2, "not-json", "resolver rejected an invalid requirement", "audit_tool_error"),
        (2, json.dumps({"dependencies": []}), "unexpected internal failure", "audit_tool_error"),
    ],
)
def test_dependency_audit_retries_only_transport_failures(
    returncode: int, stdout: str, stderr: str, expected: str
) -> None:
    classification, _, _ = classify_result(returncode, stdout, stderr)
    assert classification == expected


@pytest.mark.parametrize("payload", [{}, {"dependencies": "invalid"}, {"dependencies": ["invalid"]}])
def test_dependency_audit_rejects_malformed_machine_output(payload: object) -> None:
    with pytest.raises(ValueError):
        summarize_payload(payload)


def test_dependency_audit_retries_transport_then_records_clean_result(tmp_path, monkeypatch) -> None:
    responses = iter(
        [
            SimpleNamespace(returncode=1, stdout="", stderr="service unavailable (HTTP 503)"),
            SimpleNamespace(
                returncode=0,
                stdout=json.dumps({"dependencies": [{"name": "alpha", "version": "1", "vulns": []}]}),
                stderr="No known vulnerabilities found",
            ),
        ]
    )
    calls = 0

    def fake_run(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return next(responses)

    monkeypatch.setattr(audit_dependencies.subprocess, "run", fake_run)
    monkeypatch.setattr(audit_dependencies.time, "sleep", lambda _delay: None)
    destination = tmp_path / "audit.json"

    assert audit_dependencies.run_audit(destination, max_attempts=3, retry_delay_seconds=0) == 0
    evidence = json.loads(destination.read_text(encoding="utf-8"))
    assert calls == 2
    assert evidence["passed"] is True
    assert evidence["attempts_used"] == 2
    assert evidence["dependency_count"] == 1
    assert [attempt["classification"] for attempt in evidence["attempts"]] == ["transport_error", "passed"]


def test_dependency_audit_does_not_retry_vulnerabilities(tmp_path, monkeypatch) -> None:
    vulnerable = {
        "dependencies": [{"name": "alpha", "version": "1", "vulns": [{"id": "OSV-TEST-1", "fix_versions": ["2"]}]}]
    }
    calls = 0

    def fake_run(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return SimpleNamespace(returncode=1, stdout=json.dumps(vulnerable), stderr="")

    monkeypatch.setattr(audit_dependencies.subprocess, "run", fake_run)
    destination = tmp_path / "audit.json"

    assert audit_dependencies.run_audit(destination, max_attempts=3, retry_delay_seconds=0) == 1
    evidence = json.loads(destination.read_text(encoding="utf-8"))
    assert calls == 1
    assert evidence["failure_mode"] == "vulnerabilities_found"
    assert evidence["vulnerability_count"] == 1


@pytest.mark.parametrize(
    ("stderr", "max_attempts", "expected_calls", "failure_mode"),
    [
        ("service unavailable (HTTP 503)", 2, 2, "transport_or_service_unavailable"),
        ("resolver rejected an invalid requirement", 3, 1, "audit_tool_error"),
    ],
)
def test_dependency_audit_exhausts_transport_retries_and_fails_other_errors_immediately(
    tmp_path, monkeypatch, stderr: str, max_attempts: int, expected_calls: int, failure_mode: str
) -> None:
    calls = 0

    def fake_run(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return SimpleNamespace(returncode=2, stdout="not-json", stderr=stderr)

    monkeypatch.setattr(audit_dependencies.subprocess, "run", fake_run)
    monkeypatch.setattr(audit_dependencies.time, "sleep", lambda _delay: None)
    destination = tmp_path / "audit.json"

    assert audit_dependencies.run_audit(destination, max_attempts=max_attempts, retry_delay_seconds=0) == 1
    evidence = json.loads(destination.read_text(encoding="utf-8"))
    assert calls == expected_calls
    assert evidence["passed"] is False
    assert evidence["failure_mode"] == failure_mode
