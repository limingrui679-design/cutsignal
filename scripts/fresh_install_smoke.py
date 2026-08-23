#!/usr/bin/env python3
"""Install the built wheel into an isolated venv and exercise packaged resources."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import venv
from pathlib import Path


def _run(command: list[str], cwd: Path) -> dict[str, object]:
    completed = subprocess.run(  # noqa: S603
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=300,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"fresh-install command failed ({completed.returncode}): {command}\n{completed.stdout}\n{completed.stderr}"
        )
    return {
        "command": command,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=Path("artifacts/dist"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/fresh-install.json"))
    args = parser.parse_args()
    wheels = sorted(args.dist.glob("cutsignal-*.whl"), key=lambda path: path.stat().st_mtime)
    if not wheels:
        raise SystemExit(f"no CutSignal wheel found under {args.dist}")
    wheel = wheels[-1].resolve()

    with tempfile.TemporaryDirectory(prefix="cutsignal-fresh-install-") as directory:
        root = Path(directory)
        environment = root / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        checks = [
            _run(
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    str(wheel),
                ],
                root,
            ),
            _run(
                [
                    str(python),
                    "-c",
                    (
                        "import cutsignal; "
                        "from cutsignal.cases import list_cases, run_case; "
                        "assert len(list_cases()) == 8; "
                        "assert run_case('device-overlap-reconciliation').passed; "
                        "assert callable(cutsignal.run_pipeline); "
                        "print(cutsignal.__version__)"
                    ),
                ],
                root,
            ),
            _run([str(python), "-m", "pip", "check"], root),
        ]

    payload = {
        "schema_version": 1,
        "passed": True,
        "wheel": wheel.name,
        "isolated_virtual_environment": True,
        "checks": checks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
