"""Command-line interface for reproducible local CutSignal workflows."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Literal, NoReturn

import typer
from rich.console import Console
from rich.table import Table

from cutsignal import __version__
from cutsignal.analysis.cut import CutAnalysisConfig
from cutsignal.analysis.state_space import ParticleFilterConfig
from cutsignal.cases import get_case, list_cases, run_case, verify_cases
from cutsignal.exceptions import CutSignalError
from cutsignal.importers import import_apple_health, import_daily_csv, import_strength_csv
from cutsignal.input_safety import MAX_CONSTRAINT_BYTES, validate_file_size
from cutsignal.io import read_daily, read_foods, read_strength, write_jsonl
from cutsignal.models import DietConstraints
from cutsignal.pipeline import run_pipeline
from cutsignal.privacy import audit_paths
from cutsignal.reporting.html import render_html_report
from cutsignal.synthetic import (
    demo_constraints,
    generate_daily_demo,
    generate_food_demo,
    generate_strength_demo,
)

app = typer.Typer(
    name="cutsignal",
    help="Privacy-first decision analytics for fat loss, strength, and food planning.",
    no_args_is_help=True,
)
import_app = typer.Typer(help="Normalize external data into validated, device-independent JSONL.")
cases_app = typer.Typer(help="Inspect and execute deterministic, evidence-bounded product cases.")
app.add_typer(import_app, name="import")
app.add_typer(cases_app, name="cases")
console = Console()


def _abort_expected(exc: Exception) -> NoReturn:
    """Render expected data/input failures without an implementation traceback."""
    typer.echo(f"Input error: {exc}", err=True)
    raise typer.Exit(code=2) from exc


def _write_json(payload: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _manifest(root: Path, paths: list[Path]) -> Path:
    files = []
    for path in paths:
        files.append(
            {
                "path": str(path.relative_to(root)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
        )
    destination = root / "artifact_manifest.json"
    _write_json(
        {
            "project": "CutSignal",
            "version": __version__,
            "synthetic_only": True,
            "files": sorted(files, key=lambda item: str(item["path"])),
        },
        destination,
    )
    return destination


@app.command()
def version() -> None:
    """Print the installed CutSignal version."""
    typer.echo(__version__)


@import_app.command("apple-health")
def import_apple_health_command(
    source: Annotated[Path, typer.Argument(exists=True, readable=True)],
    destination: Path,
) -> None:
    """Stream an Apple Health XML/ZIP into device-independent daily JSONL."""
    try:
        records = import_apple_health(source)
        write_jsonl(records, destination)
    except (CutSignalError, OSError, UnicodeError, ValueError) as exc:
        _abort_expected(exc)
    console.print(f"Wrote [bold]{len(records)}[/bold] daily records to {destination}")


@import_app.command("daily-csv")
def import_daily_csv_command(
    source: Annotated[Path, typer.Argument(exists=True, readable=True)],
    destination: Path,
    provider: Annotated[str, typer.Option(help="Provenance label stored with each row.")] = "generic-csv",
) -> None:
    """Normalize a device or app CSV into the daily schema."""
    try:
        records = import_daily_csv(source, provider=provider)
        write_jsonl(records, destination)
    except (CutSignalError, OSError, UnicodeError, ValueError) as exc:
        _abort_expected(exc)
    console.print(f"Wrote [bold]{len(records)}[/bold] daily records to {destination}")


@import_app.command("strength")
def import_strength_command(
    source: Annotated[Path, typer.Argument(exists=True, readable=True)],
    destination: Path,
    provider: Annotated[str | None, typer.Option(help="Override Hevy/Strong/generic detection.")] = None,
) -> None:
    """Normalize a Hevy, Strong, or generic training CSV."""
    try:
        records = import_strength_csv(source, provider=provider)
        write_jsonl(records, destination)
    except (CutSignalError, OSError, UnicodeError, ValueError) as exc:
        _abort_expected(exc)
    console.print(f"Wrote [bold]{len(records)}[/bold] strength sets to {destination}")


@app.command()
def analyze(
    daily: Annotated[Path, typer.Option(exists=True, readable=True)],
    strength: Annotated[Path, typer.Option(exists=True, readable=True)],
    foods: Annotated[Path, typer.Option(exists=True, readable=True)],
    constraints: Annotated[Path, typer.Option(exists=True, readable=True)],
    output: Annotated[Path, typer.Option(help="Directory for report.html and result JSON.")] = Path("artifacts/run"),
    particles: Annotated[int, typer.Option(min=500, max=100_000)] = 4_000,
    optimizer_seconds: Annotated[float, typer.Option(min=1, max=300)] = 10.0,
    pareto_seconds: Annotated[float, typer.Option(min=1, max=120)] = 3.0,
    report_profile: Annotated[
        Literal["private", "share-safe"],
        typer.Option(help="private keeps detailed series; share-safe removes exact health series and names."),
    ] = "private",
) -> None:
    """Run all three engines against normalized local input files."""
    try:
        validate_file_size(constraints, MAX_CONSTRAINT_BYTES, "constraint JSON")
        diet_constraints = DietConstraints.model_validate_json(constraints.read_text(encoding="utf-8"))
        result = run_pipeline(
            read_daily(daily),
            read_strength(strength),
            read_foods(foods),
            diet_constraints,
            cut_config=CutAnalysisConfig(filter=ParticleFilterConfig(particles=particles)),
            diet_time_limit_seconds=optimizer_seconds,
            pareto_time_limit_seconds=pareto_seconds,
        )
        report = render_html_report(result, output / "report.html", profile=report_profile)
    except (CutSignalError, OSError, UnicodeError, ValueError) as exc:
        _abort_expected(exc)
    console.print(f"Decision: [bold]{result.integrated_decision.action}[/bold]")
    console.print(f"Report: {report}")


@app.command()
def demo(
    output: Annotated[Path, typer.Option(help="Synthetic artifact directory.")] = Path("artifacts/demo"),
    particles: Annotated[int, typer.Option(min=500, max=100_000)] = 2_000,
    optimizer_seconds: Annotated[float, typer.Option(min=1, max=300)] = 5.0,
    pareto_seconds: Annotated[float, typer.Option(min=1, max=120)] = 2.0,
) -> None:
    """Generate fixed synthetic inputs and a complete offline report."""
    daily = generate_daily_demo()
    strength = generate_strength_demo(daily)
    foods = generate_food_demo()
    constraints = demo_constraints()
    data_dir = output / "data"
    daily_path = write_jsonl(daily, data_dir / "daily.synthetic.jsonl")
    strength_path = write_jsonl(strength, data_dir / "strength.synthetic.jsonl")
    food_path = write_jsonl(foods, data_dir / "foods.synthetic.jsonl")
    constraints_path = data_dir / "constraints.synthetic.json"
    _write_json(constraints.model_dump(mode="json"), constraints_path)
    result = run_pipeline(
        daily,
        strength,
        foods,
        constraints,
        cut_config=CutAnalysisConfig(filter=ParticleFilterConfig(particles=particles)),
        diet_time_limit_seconds=optimizer_seconds,
        pareto_time_limit_seconds=pareto_seconds,
    )
    report = render_html_report(result, output / "report.html", profile="private")
    share_safe_report = render_html_report(
        result,
        output / "report.share-safe.html",
        profile="share-safe",
    )
    manifest = _manifest(
        output,
        [
            daily_path,
            strength_path,
            food_path,
            constraints_path,
            report,
            report.with_suffix(".json"),
            share_safe_report,
            share_safe_report.with_suffix(".json"),
        ],
    )
    table = Table(title="CutSignal synthetic run")
    table.add_column("Gate")
    table.add_column("Result")
    table.add_row("Integrated decision", result.integrated_decision.action)
    table.add_row("Fat-loss signal", result.cut.decision.action)
    table.add_row("Strength signal", result.strength.decision.action)
    table.add_row("Diet solver", f"{result.diet.status}; gap={result.diet.mip_gap!s}")
    table.add_row("Report", str(report))
    table.add_row("Minimized report", str(share_safe_report))
    table.add_row("Manifest", str(manifest))
    console.print(table)


@cases_app.command("list")
def cases_list() -> None:
    """List the executable casebook without running analyses."""
    table = Table(title="CutSignal casebook")
    table.add_column("Case")
    table.add_column("Domain")
    table.add_column("Decision question")
    for case in list_cases():
        table.add_row(case.id, case.domain, case.decision_question)
    console.print(table)


@cases_app.command("run")
def cases_run(
    case_id: Annotated[str, typer.Argument(help="Case id from `cutsignal cases list`.")],
    output: Annotated[Path | None, typer.Option(help="Optional JSON evidence destination.")] = None,
    optimizer_seconds: Annotated[float, typer.Option(min=1, max=300)] = 2.0,
) -> None:
    """Execute one deterministic case and expose all assertions."""
    try:
        get_case(case_id)
        result = run_case(case_id, optimizer_seconds=optimizer_seconds)
    except (CutSignalError, OSError, UnicodeError, ValueError) as exc:
        _abort_expected(exc)
    if output is not None:
        _write_json(result.model_dump(mode="json"), output)
    console.print_json(data=result.model_dump(mode="json"))
    if not result.passed:
        raise typer.Exit(code=1)


@cases_app.command("verify")
def cases_verify(
    output: Annotated[Path, typer.Option(help="JSON evidence destination.")] = Path("artifacts/cases.json"),
    optimizer_seconds: Annotated[float, typer.Option(min=1, max=300)] = 2.0,
) -> None:
    """Run the entire casebook and fail if any stated gate fails."""
    results = verify_cases(optimizer_seconds=optimizer_seconds)
    payload = {
        "schema_version": 1,
        "passed": all(item.passed for item in results),
        "cases": [item.model_dump(mode="json") for item in results],
    }
    _write_json(payload, output)
    console.print(f"Cases: {sum(item.passed for item in results)}/{len(results)} passed; evidence: {output}")
    if not payload["passed"]:
        raise typer.Exit(code=1)


@app.command("privacy-audit")
def privacy_audit(
    paths: Annotated[list[Path], typer.Argument(exists=True, readable=True)],
    fail_on_findings: Annotated[bool, typer.Option(help="Exit nonzero when a finding exists.")] = True,
) -> None:
    """Scan a proposed public tree for likely exports and common identifiers."""
    result = audit_paths(paths)
    console.print(f"Scanned {result.files_scanned} files; findings: {len(result.findings)}")
    for finding in result.findings:
        console.print(f"[{finding.severity}] {finding.path}: {finding.finding}")
    if fail_on_findings and not result.passed:
        raise typer.Exit(code=1)


@app.command()
def ui(
    port: Annotated[int, typer.Option(min=1_024, max=65_535)] = 8_501,
) -> None:
    """Launch the local Streamlit interface without a cloud account."""
    if importlib.util.find_spec("streamlit") is None:
        console.print("Install the optional interface dependencies with: pip install 'cutsignal[ui]'")
        raise typer.Exit(code=2)
    app_path = Path(__file__).with_name("app.py")
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
        "--server.address",
        "127.0.0.1",
    ]
    subprocess.run(command, check=True)  # noqa: S603


if __name__ == "__main__":
    app()
