#!/usr/bin/env python3
"""Require immutable third-party action references and dependency-update coverage."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
USES = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)")
PINNED = re.compile(r"^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+@[0-9a-f]{40}$")


def main() -> int:
    errors: list[str] = []
    references: list[str] = []
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        for line_number, line in enumerate(workflow.read_text(encoding="utf-8").splitlines(), start=1):
            match = USES.match(line)
            if match is None:
                continue
            reference = match.group(1)
            references.append(reference)
            if reference.startswith("./"):
                continue
            if PINNED.fullmatch(reference) is None:
                errors.append(f"{workflow.relative_to(ROOT)}:{line_number}: action is not pinned: {reference}")
    dependabot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    for ecosystem in ("pip", "github-actions"):
        if f"package-ecosystem: {ecosystem}" not in dependabot:
            errors.append(f"Dependabot does not cover {ecosystem}")
    if not references:
        errors.append("no GitHub Action references found")
    if errors:
        raise SystemExit("\n".join(errors))
    print(
        f"workflow supply chain: {len(references)} immutable action references; pip/github-actions updates configured"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
