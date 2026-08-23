#!/usr/bin/env python3
"""Run a fail-closed OSV dependency audit with bounded transport retries."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts" / "dependency-audit.json"
MAX_TAIL_CHARS = 4_000
TRANSPORT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\btimeout\b",
        r"timed out",
        r"connection (?:aborted|closed|error|failed|refused|reset)",
        r"failed to establish a new connection",
        r"name or service not known",
        r"temporary failure in name resolution",
        r"network is unreachable",
        r"remote end closed connection",
        r"service unavailable",
        r"bad gateway",
        r"gateway timeout",
        r"too many requests",
        r"(?:http|status(?: code)?)\s*(?:429|500|502|503|504)\b",
        r"\b(?:ssl|tls)\b.*(?:error|failed|failure)",
    )
)


def _tail(value: str) -> str:
    """Return a bounded diagnostic tail without changing audit semantics."""
    return value.strip()[-MAX_TAIL_CHARS:]


def _captured_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else value


def _is_transport_error(stdout: str, stderr: str) -> bool:
    combined = f"{stdout}\n{stderr}"
    return any(pattern.search(combined) is not None for pattern in TRANSPORT_PATTERNS)


def summarize_payload(payload: object) -> tuple[int, list[dict[str, Any]]]:
    """Validate pip-audit JSON and return dependency and vulnerability evidence."""
    if not isinstance(payload, dict) or not isinstance(payload.get("dependencies"), list):
        raise ValueError("pip-audit JSON must contain a dependencies list")

    dependencies = payload["dependencies"]
    vulnerability_index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            raise ValueError("each pip-audit dependency must be an object")
        raw_vulnerabilities = dependency.get("vulns", [])
        if not isinstance(raw_vulnerabilities, list):
            raise ValueError("each dependency's vulns field must be a list")
        for vulnerability in raw_vulnerabilities:
            if not isinstance(vulnerability, dict) or not isinstance(vulnerability.get("id"), str):
                raise ValueError("each vulnerability must be an object with a string id")
            dependency_name = str(dependency.get("name") or "unknown")
            installed_version = str(dependency.get("version") or "unknown")
            vulnerability_id = vulnerability["id"]
            key = (dependency_name, installed_version, vulnerability_id)
            record = vulnerability_index.setdefault(
                key,
                {
                    "dependency": dependency_name,
                    "installed_version": installed_version,
                    "id": vulnerability_id,
                    "aliases": [],
                    "fix_versions": [],
                },
            )
            for field in ("aliases", "fix_versions"):
                values = vulnerability.get(field, [])
                if isinstance(values, list):
                    record[field] = sorted({*record[field], *(value for value in values if isinstance(value, str))})
    return len(dependencies), list(vulnerability_index.values())


def dependency_inventory(payload: object) -> list[dict[str, Any]]:
    """Return the audited package/version inventory without copying raw service output."""
    if not isinstance(payload, dict) or not isinstance(payload.get("dependencies"), list):
        raise ValueError("pip-audit JSON must contain a dependencies list")
    inventory: list[dict[str, Any]] = []
    for dependency in payload["dependencies"]:
        if not isinstance(dependency, dict):
            raise ValueError("each pip-audit dependency must be an object")
        inventory.append(
            {
                "name": dependency.get("name"),
                "version": dependency.get("version"),
                "skip_reason": dependency.get("skip_reason"),
            }
        )
    return inventory


def classify_result(returncode: int, stdout: str, stderr: str) -> tuple[str, int | None, list[dict[str, Any]]]:
    """Classify one run without treating audit/tool failures as clean results."""
    try:
        payload = json.loads(stdout)
        dependency_count, vulnerabilities = summarize_payload(payload)
    except (json.JSONDecodeError, ValueError):
        if _is_transport_error(stdout, stderr):
            return "transport_error", None, []
        return "audit_tool_error", None, []

    if vulnerabilities:
        return "vulnerabilities_found", dependency_count, vulnerabilities
    if returncode == 0:
        return "passed", dependency_count, []
    if _is_transport_error(stdout, stderr):
        return "transport_error", dependency_count, []
    return "audit_tool_error", dependency_count, []


def _write_evidence(destination: Path, evidence: dict[str, Any]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")


def run_audit(destination: Path, *, max_attempts: int = 3, retry_delay_seconds: float = 2.0) -> int:
    """Audit the installed environment and return a shell-compatible status."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least one")
    if retry_delay_seconds < 0:
        raise ValueError("retry_delay_seconds must be nonnegative")

    command = [
        sys.executable,
        "-m",
        "pip_audit",
        "--skip-editable",
        "--progress-spinner",
        "off",
        "--vulnerability-service",
        "osv",
        "--timeout",
        "60",
        "--format",
        "json",
    ]
    attempts: list[dict[str, Any]] = []
    dependency_count: int | None = None
    dependencies: list[dict[str, Any]] = []
    vulnerabilities: list[dict[str, Any]] = []
    failure_mode: str | None = None

    for attempt_number in range(1, max_attempts + 1):
        started = time.monotonic()
        try:
            result = subprocess.run(  # noqa: S603
                command,
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=120,
                check=False,
            )
            classification, observed_count, observed_vulnerabilities = classify_result(
                result.returncode, result.stdout, result.stderr
            )
            if observed_count is not None:
                dependency_count = observed_count
                dependencies = dependency_inventory(json.loads(result.stdout))
            vulnerabilities = observed_vulnerabilities
            attempts.append(
                {
                    "attempt": attempt_number,
                    "classification": classification,
                    "returncode": result.returncode,
                    "duration_seconds": round(time.monotonic() - started, 3),
                    "stdout_tail": "" if classification == "passed" else _tail(result.stdout),
                    "stderr_tail": "" if classification == "passed" else _tail(result.stderr),
                }
            )
        except subprocess.TimeoutExpired as exc:
            classification = "transport_error"
            attempts.append(
                {
                    "attempt": attempt_number,
                    "classification": classification,
                    "returncode": None,
                    "duration_seconds": round(time.monotonic() - started, 3),
                    "stdout_tail": _tail(_captured_text(exc.stdout)),
                    "stderr_tail": _tail(_captured_text(exc.stderr)),
                }
            )

        if classification == "passed":
            failure_mode = None
            break
        if classification != "transport_error":
            failure_mode = classification
            break
        failure_mode = "transport_or_service_unavailable"
        if attempt_number < max_attempts:
            time.sleep(retry_delay_seconds)

    passed = failure_mode is None
    try:
        tool_version = version("pip-audit")
    except PackageNotFoundError:
        tool_version = "unavailable"
    evidence: dict[str, Any] = {
        "schema_version": 1,
        "passed": passed,
        "service": "osv",
        "tool": "pip-audit",
        "tool_version": tool_version,
        "python_version": sys.version.split()[0],
        "failure_mode": failure_mode,
        "attempts_used": len(attempts),
        "maximum_attempts": max_attempts,
        "dependency_count": dependency_count,
        "dependencies": dependencies,
        "vulnerability_count": len(vulnerabilities),
        "vulnerabilities": vulnerabilities,
        "attempts": attempts,
        "scope_note": (
            "Audit of the installed environment via pip-audit/OSV; an unavailable service, malformed output, "
            "or audit-tool error fails closed and is not evidence that dependencies are vulnerability-free."
        ),
    }
    _write_evidence(destination, evidence)
    print(json.dumps(evidence, indent=2))
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--retry-delay-seconds", type=float, default=2.0)
    arguments = parser.parse_args()
    return run_audit(
        arguments.output,
        max_attempts=arguments.max_attempts,
        retry_delay_seconds=arguments.retry_delay_seconds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
