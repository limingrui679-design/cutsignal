#!/usr/bin/env python3
"""Install the built wheel into an isolated venv and exercise packaged resources."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import time
import venv
from pathlib import Path

COMMAND_TIMEOUT_SECONDS = 600


def _run(name: str, command: list[str], cwd: Path) -> dict[str, object]:
    started = time.monotonic()
    print(f"[fresh-install] {name}: running", flush=True)
    completed = subprocess.run(  # noqa: S603
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"fresh-install command failed ({completed.returncode}): {command}\n{completed.stdout}\n{completed.stderr}"
        )
    duration = round(time.monotonic() - started, 3)
    print(f"[fresh-install] {name}: passed ({duration}s)", flush=True)
    return {
        "name": name,
        "command": command,
        "duration_seconds": duration,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=Path("artifacts/dist"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/fresh-install.json"))
    args = parser.parse_args()
    args.output.unlink(missing_ok=True)
    wheels = sorted(args.dist.glob("cutsignal-*.whl"), key=lambda path: path.stat().st_mtime)
    if len(wheels) != 1:
        raise SystemExit(f"expected exactly one CutSignal wheel under {args.dist}; found {len(wheels)}")
    wheel = wheels[0].resolve()

    overall_started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="cutsignal-fresh-install-") as directory:
        root = Path(directory)
        environment = root / "venv"
        venv_started = time.monotonic()
        print("[fresh-install] virtual_environment: running", flush=True)
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        venv_duration = round(time.monotonic() - venv_started, 3)
        print(f"[fresh-install] virtual_environment: passed ({venv_duration}s)", flush=True)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        checks = [
            _run(
                "wheel_install",
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "--only-binary=:all:",
                    str(wheel),
                ],
                root,
            ),
            _run(
                "packaged_resources_and_api",
                [
                    str(python),
                    "-c",
                    (
                        "import cutsignal; "
                        "from importlib.metadata import version; "
                        "from cutsignal.cases import list_cases, run_case; "
                        "assert cutsignal.__version__ == version('cutsignal'); "
                        "assert len(list_cases()) == 9; "
                        "assert run_case('device-overlap-reconciliation').passed; "
                        "assert callable(cutsignal.run_pipeline); "
                        "print(cutsignal.__version__)"
                    ),
                ],
                root,
            ),
            _run("pip_check", [str(python), "-m", "pip", "check"], root),
            _run(
                "installed_distributions",
                [str(python), "-m", "pip", "list", "--format=json", "--disable-pip-version-check"],
                root,
            ),
        ]

    payload = {
        "schema_version": 1,
        "passed": True,
        "wheel": wheel.name,
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "isolated_virtual_environment": True,
        "virtual_environment_seconds": venv_duration,
        "total_duration_seconds": round(time.monotonic() - overall_started, 3),
        "checks": checks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
