"""Local privacy guardrails for files likely to contain personal health data."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict

SENSITIVE_NAME_PATTERNS = (
    re.compile(r"export\.xml$", re.IGNORECASE),
    re.compile(r"apple.*health.*\.zip$", re.IGNORECASE),
    re.compile(r"hevy.*\.csv$", re.IGNORECASE),
    re.compile(r"strong.*\.csv$", re.IGNORECASE),
)
SENSITIVE_CONTENT_PATTERNS = {
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    # Require a conventional grouped form or one uninterrupted 10--15 digit token.
    # This avoids treating ISO dates and nearby metric values as phone numbers.
    "phone": re.compile(
        r"(?<!\d)(?:\+\d{1,3}[ .-]+)?(?:\(\d{2,4}\)|\d{2,4})[ .-]+\d{3,4}[ .-]+\d{4}(?!\d)"
        r"|(?<!\d)\d{10,15}(?!\d)"
    ),
    # Split scanner signatures so auditing this source file does not match the
    # literal definitions themselves.
    "apple_health_me": re.compile("<" + r"Me\b", re.IGNORECASE),
    "date_of_birth": re.compile("date" + "OfBirth=", re.IGNORECASE),
    "medical_record": re.compile("clinical" + "record|HKClinical" + "TypeIdentifier", re.IGNORECASE),
}


class PrivacyFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    severity: str
    finding: str
    remediation: str


class PrivacyAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    files_scanned: int
    findings: list[PrivacyFinding]


def audit_paths(paths: list[Path], *, max_text_bytes: int = 2_000_000) -> PrivacyAudit:
    findings: list[PrivacyFinding] = []
    scanned = 0
    for root in paths:
        candidates = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file()]
        for path in candidates:
            scanned += 1
            relative = str(path)
            if any(pattern.search(path.name) for pattern in SENSITIVE_NAME_PATTERNS):
                findings.append(
                    PrivacyFinding(
                        path=relative,
                        severity="high",
                        finding="filename resembles a private health export",
                        remediation="move it under an ignored local data directory and remove it from Git history",
                    )
                )
            if path.stat().st_size > max_text_bytes or path.suffix.casefold() in {
                ".zip",
                ".png",
                ".jpg",
                ".pdf",
                ".parquet",
            }:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for name, pattern in SENSITIVE_CONTENT_PATTERNS.items():
                if pattern.search(text):
                    findings.append(
                        PrivacyFinding(
                            path=relative,
                            severity="high" if name in {"apple_health_me", "date_of_birth"} else "medium",
                            finding=f"possible sensitive content: {name}",
                            remediation="replace with synthetic data or redact before publication",
                        )
                    )
    return PrivacyAudit(passed=not findings, files_scanned=scanned, findings=findings)
