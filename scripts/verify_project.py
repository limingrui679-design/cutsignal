#!/usr/bin/env python3
"""Produce machine-readable evidence for the exact current checkout."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
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
    git_binary = shutil.which("git")
    if git_binary is not None:
        listed = subprocess.run(  # noqa: S603
            [git_binary, "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        files = sorted(
            ROOT / relative.decode("utf-8")
            for relative in listed.split(b"\0")
            if relative and (ROOT / relative.decode("utf-8")).is_file()
        )
    else:
        files = sorted(
            path
            for path in ROOT.rglob("*")
            if path.is_file()
            and ".venv" not in path.relative_to(ROOT).parts
            and not EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts)
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
            "distribution",
            [python, "-m", "build", "--sdist", "--wheel", "--outdir", "artifacts/dist"],
        ),
        "fresh_install": _run(
            "fresh_install",
            [python, "scripts/fresh_install_smoke.py"],
            timeout=420,
        ),
        "pip_check": _run("pip_check", [python, "-m", "pip", "check"]),
        "public_api": _run(
            "public_api",
            [
                python,
                "-c",
                (
                    "import cutsignal; "
                    "assert callable(cutsignal.analyze_cut); "
                    "assert callable(cutsignal.analyze_strength); "
                    "assert callable(cutsignal.optimize_weekly_plan); "
                    "assert callable(cutsignal.run_pipeline)"
                ),
            ],
        ),
        "claims": _run("claims", [python, "scripts/verify_claims.py"]),
        "docs_links": _run("docs_links", [python, "scripts/verify_docs.py"]),
        "cases": _run(
            "cases",
            [
                python,
                "-m",
                "cutsignal",
                "cases",
                "verify",
                "--output",
                "artifacts/cases.json",
                "--optimizer-seconds",
                "2",
            ],
            timeout=240,
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
        ROOT / "data/registry/claims.yml",
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
        "docs/CASEBOOK.md",
        "docs/PROJECT_AUDIT.md",
        "data/registry/sources.yml",
        "data/registry/claims.yml",
    ]
    docs = {
        "passed": all(
            (ROOT / relative).is_file() and (ROOT / relative).stat().st_size > 100 for relative in required_docs
        ),
        "required": required_docs,
        "missing": [relative for relative in required_docs if not (ROOT / relative).is_file()],
    }
    semantic_requirements = {
        "README.md": ["share-safe", "cases verify", "not an exhaustive Pareto frontier"],
        "docs/METHODS.md": ["linked particle", "empirical Bayes", "independent post-solve"],
        "docs/PRIVACY.md": ["private", "share-safe", "does not guarantee anonymity"],
        "docs/CASEBOOK.md": ["deterministic synthetic", "device-overlap-reconciliation"],
        "docs/PROJECT_AUDIT.md": ["P0", "P1", "External conditions"],
    }
    semantic_missing: list[str] = []
    for relative, phrases in semantic_requirements.items():
        path = ROOT / relative
        content = path.read_text(encoding="utf-8") if path.is_file() else ""
        normalized_content = " ".join(content.casefold().split())
        semantic_missing.extend(
            f"{relative}: {phrase}"
            for phrase in phrases
            if " ".join(phrase.casefold().split()) not in normalized_content
        )
    docs["semantic_requirements"] = semantic_requirements
    docs["semantic_missing"] = semantic_missing
    docs["passed"] = bool(docs["passed"]) and not semantic_missing
    coverage: dict[str, Any] = {}
    coverage_path = ARTIFACTS / "coverage.json"
    if coverage_path.exists():
        coverage = json.loads(coverage_path.read_text(encoding="utf-8")).get("totals", {})
    e2e: dict[str, Any] = {}
    e2e_path = ARTIFACTS / "e2e" / "summary.json"
    if e2e_path.exists():
        e2e = json.loads(e2e_path.read_text(encoding="utf-8"))

    git_binary = shutil.which("git")
    git_status = (
        subprocess.run(  # noqa: S603
            [git_binary, "status", "--porcelain"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        ).stdout.splitlines()
        if git_binary is not None
        else ["git executable unavailable"]
    )
    evidence = {
        "schema_version": 1,
        "checkout_fingerprint": checkout_fingerprint(),
        "python": sys.version,
        "platform": sys.platform,
        "git_status_porcelain": git_status,
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
