"""Generate a self-contained report without external scripts or network calls."""

from __future__ import annotations

import html
import json
from collections.abc import Iterable
from pathlib import Path

from cutsignal.pipeline import PipelineResult


def _polyline(values: list[float], *, width: int = 760, height: int = 220) -> str:
    if not values:
        return ""
    lower = min(values)
    upper = max(values)
    spread = max(upper - lower, 1e-9)
    points: list[str] = []
    for index, value in enumerate(values):
        x = 10 + index * (width - 20) / max(len(values) - 1, 1)
        y = height - 10 - (value - lower) / spread * (height - 20)
        points.append(f"{x:.1f},{y:.1f}")
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="trend chart">'
        '<rect width="100%" height="100%" rx="12" fill="#101827"/>'
        f'<polyline points="{" ".join(points)}" fill="none" stroke="#50e3c2" '
        'stroke-width="3" vector-effect="non-scaling-stroke"/>'
        f'<text x="12" y="18" fill="#93a4bb" font-size="12">max {upper:.2f}</text>'
        f'<text x="12" y="{height - 8}" fill="#93a4bb" font-size="12">min {lower:.2f}</text>'
        "</svg>"
    )


def _list(items: Iterable[str]) -> str:
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"


def _strength_rows(result: PipelineResult) -> str:
    rows = []
    for item in result.strength.exercises:
        rows.append(
            "<tr>"
            f"<td>{html.escape(item.exercise)}</td>"
            f"<td>{item.sessions}</td>"
            f"<td>{item.e1rm_change_pct:+.1f}%</td>"
            f"<td>{item.hierarchical_slope_pct_per_week:+.2f}%/wk</td>"
            f"<td>{item.decline_probability:.0%}</td>"
            f"<td>{'yes' if item.fatigue_signal else 'no'}</td>"
            "</tr>"
        )
    return "".join(rows)


def _diet_rows(result: PipelineResult) -> str:
    rows = []
    for day in result.diet.daily:
        rows.append(
            "<tr>"
            f"<td>{day.day}</td><td>{day.calories_kcal:.0f}</td>"
            f"<td>{day.robust_protein_lower_g:.1f} g</td>"
            f"<td>{day.robust_fiber_lower_g:.1f} g</td>"
            f"<td>{day.robust_cost_upper:.2f}</td><td>{day.prep_minutes:.0f} min</td>"
            "</tr>"
        )
    return "".join(rows)


def _sensitivity_rows(result: PipelineResult) -> str:
    return "".join(
        "<tr>"
        f"<td>{html.escape(item.scenario)}</td>"
        f"<td>{'pass' if item.feasible else 'violation'}</td>"
        f"<td>{html.escape(', '.join(item.violations) or 'none')}</td>"
        "</tr>"
        for item in result.diet.sensitivity
    )


def _pareto_rows(result: PipelineResult) -> str:
    return "".join(
        "<tr>"
        f"<td>{html.escape(item.label)}</td>"
        f"<td>{item.total_cost:.2f}</td>"
        f"<td>{item.total_prep_minutes:.0f} min</td>"
        f"<td>{item.mean_preference:.2f}</td>"
        "</tr>"
        for item in result.diet_pareto
    )


def render_html_report(result: PipelineResult, destination: Path) -> Path:
    """Render only derived aggregates; source IDs and raw records are omitted."""
    cut = result.cut
    decision = result.integrated_decision
    weight_chart = _polyline([item.trend_weight_median_kg for item in cut.state_estimates])
    tdee_chart = _polyline([item.tdee_median_kcal for item in cut.state_estimates])
    css = """
    :root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    body { margin: 0; background: #07101d; color: #e8eef8; }
    main { max-width: 1080px; margin: auto; padding: 36px 22px 72px; }
    h1 { font-size: 2.35rem; margin-bottom: .25rem; }
    h2 { margin-top: 2.4rem; }
    .muted { color: #93a4bb; }
    .notice { border-left: 4px solid #ffcc66; background: #171d27; padding: 14px 18px; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit,minmax(190px,1fr)); gap: 12px; }
    .card { background: #101827; border: 1px solid #22324a; border-radius: 14px; padding: 16px; }
    .card strong { display:block; font-size:1.55rem; color:#50e3c2; margin-top:6px; }
    table { width:100%; border-collapse: collapse; background:#101827; }
    th,td { text-align:left; padding:10px; border-bottom:1px solid #26364c; }
    th { color:#93a4bb; }
    svg { width:100%; height:auto; }
    code { color:#80bfff; }
    """
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>CutSignal private report</title><style>{css}</style></head><body><main>
<h1>CutSignal</h1><p class="muted">Private, offline decision report · {cut.start_date} to {cut.end_date}</p>
<p class="notice"><strong>Scope:</strong> {html.escape(decision.scope_note)}</p>
<h2>Integrated decision</h2><div class="card"><strong>{html.escape(decision.action)}</strong>
{_list(decision.rationale)}<p class="muted">Evidence order</p>{_list(decision.evidence_order)}</div>
<h2>Fat-loss signal</h2><div class="cards">
<div class="card">Trend<strong>{cut.latest_trend_kg_per_week:+.2f} kg/week</strong></div>
<div class="card">Plateau probability<strong>{cut.plateau_probability:.0%}</strong></div>
<div class="card">TDEE median<strong>{cut.latest_tdee_kcal:.0f} kcal/day</strong></div>
<div class="card">Decision stability<strong>{cut.sensitivity_decision_stability:.0%}</strong></div>
</div><h3>Trend weight</h3>{weight_chart}<h3>Latent TDEE</h3>{tdee_chart}
<p>Weight completeness: {cut.weight_completeness:.0%}; intake completeness: {cut.intake_completeness:.0%}.</p>
<h2>Strength retention</h2><p>Overall retention score: <strong>{result.strength.overall_retention_score:.1f}</strong>;
status: <strong>{result.strength.decision.action}</strong>.</p>
<table><thead><tr><th>Exercise</th><th>Sessions</th><th>e1RM change</th><th>Shrunk trend</th>
<th>Decline probability</th><th>Fatigue</th></tr></thead><tbody>{_strength_rows(result)}</tbody></table>
<h2>Robust weekly food plan</h2><p>{result.diet.unique_foods} unique foods; robust weekly cost
{result.diet.robust_total_cost_upper:.2f}; weighted data quality {result.diet.weighted_data_quality:.0%}.
Solver status: <strong>{html.escape(result.diet.status)}</strong>; MIP gap:
<strong>{"n/a" if result.diet.mip_gap is None else f"{result.diet.mip_gap:.1%}"}</strong>.</p>
<table><thead><tr><th>Day</th><th>Calories</th><th>Robust protein</th><th>Robust fiber</th>
<th>Robust cost</th><th>Prep</th></tr></thead><tbody>{_diet_rows(result)}</tbody></table>
<h3>Coefficient stress tests</h3><table><thead><tr><th>Scenario</th><th>Result</th><th>Violations</th>
</tr></thead><tbody>{_sensitivity_rows(result)}</tbody></table>
<h3>Non-dominated objective profiles</h3><table><thead><tr><th>Profile</th><th>Cost</th><th>Prep</th>
<th>Preference</th></tr></thead><tbody>{_pareto_rows(result)}</tbody></table>
<h2>Limitations</h2>{_list([*cut.limitations, *result.strength.limitations, *result.diet.assumptions])}
<p class="muted">No raw record, source identifier, device identifier, or credential is embedded in this report.</p>
</main></body></html>"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    json_path = destination.with_suffix(".json")
    json_path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return destination
