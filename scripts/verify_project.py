#!/usr/bin/env python3
"""Produce machine-readable evidence for the exact current checkout."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from cutsignal.privacy import audit_paths

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
EXCLUDED_PARTS = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__", "artifacts"}


def checkout_fingerprint() -> str:
    digest = hashlib.sha256()
    files = sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file() and not EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts)
    )
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _run(name: str, command: list[str], timeout: int = 180) -> dict[str, Any]:
    started = time.monotonic()
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = "0"
    try:
        result = subprocess.run(  # noqa: S603
            command,
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        output = (result.stdout + "\n" + result.stderr).strip()
        return {
            "name": name,
            "passed": result.returncode == 0,
            "returncode": result.returncode,
            "duration_seconds": round(time.monotonic() - started, 3),
            "command": command,
            "output_tail": output[-12_000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "name": name,
            "passed": False,
            "returncode": None,
            "duration_seconds": round(time.monotonic() - started, 3),
            "command": command,
            "output_tail": f"timed out: {exc}",
        }


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    python = sys.executable
    checks = {
        "ruff_check": _run("ruff_check", [python, "-m", "ruff", "check", "."]),
        "ruff_format": _run("ruff_format", [python, "-m", "ruff", "format", "--check", "."]),
        "mypy": _run("mypy", [python, "-m", "mypy", "src/cutsignal"]),
        "pytest_coverage": _run(
            "pytest_coverage",
            [
                python,
                "-m",
                "pytest",
                "--cov=cutsignal",
                "--cov-report=term-missing",
                "--cov-report=json:artifacts/coverage.json",
            ],
        ),
        "wheel": _run(
            "wheel",
            [python, "-m", "build", "--wheel", "--outdir", "artifacts/dist"],
        ),
        "cli": _run("cli", [python, "-m", "cutsignal", "--help"]),
        "ui": _run("ui", [python, "scripts/ui_smoke.py"]),
        "e2e": _run(
            "e2e",
            [python, "scripts/e2e_smoke.py", "--output", "artifacts/e2e"],
            timeout=240,
        ),
    }

    public_candidates = [
        ROOT / "src",
        ROOT / "tests",
        ROOT / "docs",
        ROOT / "data",
        ROOT / "scripts",
        ROOT / "README.md",
        ROOT / "pyproject.toml",
        ROOT / "CONTRIBUTING.md",
        ROOT / "SECURITY.md",
        ROOT / "CITATION.cff",
    ]
    privacy = audit_paths(public_candidates)
    required_docs = [
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "docs/ARCHITECTURE.md",
        "docs/METHODS.md",
        "docs/DEVICE_ADAPTERS.md",
        "docs/DATA_SOURCES.md",
        "docs/PRIVACY.md",
        "docs/LIMITATIONS.md",
        "docs/VALIDATION.md",
        "data/registry/sources.yml",
    ]
    docs = {
        "passed": all(
            (ROOT / relative).is_file() and (ROOT / relative).stat().st_size > 100 for relative in required_docs
        ),
        "required": required_docs,
        "missing": [relative for relative in required_docs if not (ROOT / relative).is_file()],
    }
    coverage: dict[str, Any] = {}
    coverage_path = ARTIFACTS / "coverage.json"
    if coverage_path.exists():
        coverage = json.loads(coverage_path.read_text(encoding="utf-8")).get("totals", {})
    e2e: dict[str, Any] = {}
    e2e_path = ARTIFACTS / "e2e" / "summary.json"
    if e2e_path.exists():
        e2e = json.loads(e2e_path.read_text(encoding="utf-8"))

    evidence = {
        "schema_version": 1,
        "checkout_fingerprint": checkout_fingerprint(),
        "python": sys.version,
        "platform": sys.platform,
        "checks": checks,
        "coverage": coverage,
        "privacy": privacy.model_dump(mode="json"),
        "documentation": docs,
        "e2e": e2e,
    }
    destination = ARTIFACTS / "verification.json"
    destination.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    passed = all(item["passed"] for item in checks.values()) and privacy.passed and docs["passed"]
    print(f"verification: {'passed' if passed else 'failed'}")
    print(f"evidence: {destination}")
    for name, result in checks.items():
        print(f"- {name}: {'pass' if result['passed'] else 'FAIL'} ({result['duration_seconds']}s)")
    print(f"- privacy: {'pass' if privacy.passed else 'FAIL'} ({len(privacy.findings)} findings)")
    print(f"- documentation: {'pass' if docs['passed'] else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
