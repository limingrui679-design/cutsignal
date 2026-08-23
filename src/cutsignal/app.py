"""Local Streamlit dashboard for CutSignal."""

from __future__ import annotations

import json
from io import StringIO
from typing import TypeVar

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pydantic import BaseModel

from cutsignal.analysis.cut import CutAnalysisConfig
from cutsignal.analysis.state_space import ParticleFilterConfig
from cutsignal.cases import CaseRunResult, CaseSpec, list_cases, run_case
from cutsignal.exceptions import CutSignalError
from cutsignal.input_safety import (
    MAX_CONSTRAINT_BYTES,
    MAX_JSONL_LINE_BYTES,
    MAX_UI_ROWS,
    MAX_UI_UPLOAD_BYTES,
)
from cutsignal.models import DailyObservation, DietConstraints, FoodItem, StrengthSet
from cutsignal.pipeline import PipelineResult, run_pipeline
from cutsignal.reporting.profiles import build_report_payload
from cutsignal.synthetic import (
    demo_constraints,
    generate_daily_demo,
    generate_food_demo,
    generate_strength_demo,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


def _read_uploaded_jsonl(payload: bytes, model: type[ModelT]) -> list[ModelT]:
    if len(payload) > MAX_UI_UPLOAD_BYTES:
        raise ValueError(f"upload exceeds {MAX_UI_UPLOAD_BYTES} bytes")
    output: list[ModelT] = []
    for line_number, line in enumerate(StringIO(payload.decode("utf-8")), start=1):
        if line_number > MAX_UI_ROWS:
            raise ValueError(f"upload exceeds {MAX_UI_ROWS} rows")
        if line.strip():
            if len(line.encode("utf-8")) > MAX_JSONL_LINE_BYTES:
                raise ValueError(f"JSONL line {line_number} exceeds the configured size limit")
            try:
                output.append(model.model_validate_json(line))
            except ValueError as exc:
                raise ValueError(f"invalid JSONL line {line_number}: {exc}") from exc
    return output


def _read_uploaded_constraints(payload: bytes) -> DietConstraints:
    if len(payload) > MAX_CONSTRAINT_BYTES:
        raise ValueError(f"constraint JSON exceeds {MAX_CONSTRAINT_BYTES} bytes")
    return DietConstraints.model_validate_json(payload)


@st.cache_data(show_spinner=False)
def _run_demo(particles: int, optimizer_seconds: float) -> dict[str, object]:
    daily = generate_daily_demo()
    result = run_pipeline(
        daily,
        generate_strength_demo(daily),
        generate_food_demo(),
        demo_constraints(),
        cut_config=CutAnalysisConfig(filter=ParticleFilterConfig(particles=particles)),
        diet_time_limit_seconds=optimizer_seconds,
        pareto_time_limit_seconds=max(1.0, optimizer_seconds / 2),
    )
    return result.model_dump(mode="json")


def _trend_figure(result: PipelineResult) -> go.Figure:
    states = result.cut.state_estimates
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=[item.date for item in states],
            y=[item.trend_weight_upper_kg for item in states],
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=[item.date for item in states],
            y=[item.trend_weight_lower_kg for item in states],
            fill="tonexty",
            fillcolor="rgba(38, 166, 154, 0.18)",
            line={"width": 0},
            name="95% interval",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=[item.date for item in states],
            y=[item.trend_weight_median_kg for item in states],
            line={"color": "#26a69a", "width": 3},
            name="Trend weight",
        )
    )
    observed = [item for item in states if item.observed_weight_kg is not None]
    figure.add_trace(
        go.Scatter(
            x=[item.date for item in observed],
            y=[item.observed_weight_kg for item in observed],
            mode="markers",
            marker={"color": "rgba(144, 164, 174, .45)", "size": 5},
            name="Observed",
        )
    )
    figure.update_layout(height=430, margin={"l": 10, "r": 10, "t": 25, "b": 10}, yaxis_title="kg")
    return figure


def _tdee_figure(result: PipelineResult) -> go.Figure:
    states = result.cut.state_estimates
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=[item.date for item in states],
            y=[item.tdee_upper_kcal for item in states],
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=[item.date for item in states],
            y=[item.tdee_lower_kcal for item in states],
            fill="tonexty",
            fillcolor="rgba(66, 165, 245, 0.18)",
            line={"width": 0},
            name="95% interval",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=[item.date for item in states],
            y=[item.tdee_median_kcal for item in states],
            line={"color": "#42a5f5", "width": 3},
            name="Latent TDEE",
        )
    )
    figure.update_layout(height=430, margin={"l": 10, "r": 10, "t": 25, "b": 10}, yaxis_title="kcal/day")
    return figure


def _sensitivity_figure(result: PipelineResult) -> go.Figure:
    values = result.cut.sensitivity
    colors = ["#ffcc66" if item.plateau_probability >= 0.75 else "#50e3c2" for item in values]
    figure = go.Figure(
        go.Bar(
            x=[item.trend_kg_per_week for item in values],
            y=[item.scenario for item in values],
            orientation="h",
            marker_color=colors,
            customdata=[item.plateau_probability for item in values],
            hovertemplate="%{y}<br>rate=%{x:.3f} kg/wk<br>plateau posterior=%{customdata:.1%}<extra></extra>",
        )
    )
    band = result.receipt.cut_config.plateau_band_kg_per_week
    figure.add_vrect(x0=-band, x1=band, fillcolor="rgba(255,204,102,.12)", line_width=0)
    figure.add_vline(x=0, line_dash="dot", line_color="#93a4bb")
    figure.update_layout(
        height=360,
        margin={"l": 10, "r": 10, "t": 25, "b": 10},
        xaxis_title="Posterior median kg/week",
        yaxis={"autorange": "reversed"},
    )
    return figure


def _strength_figure(result: PipelineResult) -> go.Figure:
    figure = go.Figure()
    exercises = sorted({item.exercise for item in result.strength.session_metrics})
    for exercise in exercises:
        values = [item for item in result.strength.session_metrics if item.exercise == exercise]
        figure.add_trace(
            go.Scatter(
                x=[item.date for item in values],
                y=[item.e1rm_kg for item in values],
                mode="lines+markers",
                name=exercise,
                customdata=[item.e1rm_uncertainty_pct for item in values],
                hovertemplate="%{x}<br>e1RM=%{y:.1f} kg<br>formula uncertainty=%{customdata:.1f}%<extra></extra>",
            )
        )
    figure.update_layout(
        height=420,
        margin={"l": 10, "r": 10, "t": 25, "b": 10},
        yaxis_title="Estimated 1RM (kg)",
    )
    return figure


def _training_load_figure(result: PipelineResult) -> go.Figure:
    values = result.strength.weekly_summaries
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=[item.week for item in values],
            y=[item.volume_kg for item in values],
            name="Weekly volume",
            marker_color="rgba(66,165,245,.55)",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=[item.week for item in values],
            y=[item.mean_intensity_pct_e1rm for item in values],
            name="Mean intensity",
            yaxis="y2",
            line={"color": "#ffcc66", "width": 3},
        )
    )
    figure.update_layout(
        height=390,
        margin={"l": 10, "r": 10, "t": 25, "b": 10},
        yaxis={"title": "Volume (kg)"},
        yaxis2={"title": "% e1RM", "overlaying": "y", "side": "right"},
        legend={"orientation": "h"},
    )
    return figure


def _diet_figure(result: PipelineResult) -> go.Figure:
    values = result.diet.daily
    constraints = result.receipt.diet_constraints
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=[item.day for item in values],
            y=[item.robust_calories_upper - item.robust_calories_lower for item in values],
            base=[item.robust_calories_lower for item in values],
            name="Robust calorie interval",
            marker_color="rgba(80,227,194,.58)",
            hovertemplate="day %{x}<br>uncertainty span=%{y:.0f} kcal<extra></extra>",
        )
    )
    figure.add_hline(y=constraints.calories_min, line_dash="dash", line_color="#ffcc66")
    figure.add_hline(y=constraints.calories_max, line_dash="dash", line_color="#ffcc66")
    figure.update_layout(
        height=360,
        margin={"l": 10, "r": 10, "t": 25, "b": 10},
        xaxis_title="Day",
        yaxis_title="kcal",
    )
    return figure


def _tradeoff_figure(result: PipelineResult) -> go.Figure:
    values = result.diet_pareto
    return go.Figure(
        go.Scatter(
            x=[item.total_cost for item in values],
            y=[item.total_prep_minutes for item in values],
            mode="markers+text",
            text=[item.label for item in values],
            textposition="top center",
            marker={
                "size": [12 + item.mean_preference * 16 for item in values],
                "color": [item.mean_preference for item in values],
                "colorscale": "Viridis",
                "showscale": True,
                "colorbar": {"title": "Preference"},
            },
        )
    ).update_layout(
        height=390,
        margin={"l": 10, "r": 10, "t": 25, "b": 10},
        xaxis_title="Weekly cost",
        yaxis_title="Weekly preparation minutes",
    )


def _render_casebook(cases: list[CaseSpec], selected_id: str, result: CaseRunResult | None) -> None:
    selected = next(item for item in cases if item.id == selected_id)
    st.subheader(selected.title)
    st.write(selected.decision_question)
    st.caption(f"Evidence: {selected.evidence_type} · Limitation: {selected.limitations}")
    st.write("Capabilities: " + ", ".join(selected.capabilities))
    st.info(f"Expected gate: {selected.expected_gate}")
    if result is not None:
        if result.passed:
            st.success("All stated assertions passed.")
        else:
            st.error("One or more assertions failed.")
        st.dataframe(
            pd.DataFrame([{"assertion": name, "passed": passed} for name, passed in result.assertions.items()]),
            hide_index=True,
        )
        st.json(result.observed)


def _render_result(result: PipelineResult) -> None:
    decision = result.integrated_decision
    st.subheader("Evidence-gated result")
    st.info(f"{decision.action.replace('_', ' ').title()}: {'; '.join(decision.rationale)}")
    overview, cut_tab, strength_tab, diet_tab, data_tab = st.tabs(
        ["Overview", "Fat-loss signal", "Strength", "Food plan", "Data & privacy"]
    )
    with overview:
        first, second, third, fourth = st.columns(4)
        first.metric("Trend", f"{result.cut.latest_trend_kg_per_week:+.2f} kg/wk")
        second.metric("Plateau probability", f"{result.cut.plateau_probability:.0%}")
        third.metric("Strength retention", f"{result.strength.overall_retention_score:.1f}")
        fourth.metric("Robust weekly cost", f"{result.diet.robust_total_cost_upper:.2f}")
        st.plotly_chart(_trend_figure(result), width="stretch", key="overview-trend")
        st.caption(decision.scope_note)
    with cut_tab:
        st.plotly_chart(_trend_figure(result), width="stretch", key="cut-trend")
        st.plotly_chart(_tdee_figure(result), width="stretch", key="cut-tdee")
        st.write("Sensitivity scenarios")
        st.plotly_chart(_sensitivity_figure(result), width="stretch", key="cut-sensitivity")
        st.dataframe(pd.DataFrame([item.model_dump() for item in result.cut.sensitivity]), hide_index=True)
        st.write("Detected change points")
        st.dataframe(pd.DataFrame([item.model_dump() for item in result.cut.change_points]), hide_index=True)
    with strength_tab:
        st.write(f"Decision: **{result.strength.decision.action}**")
        st.plotly_chart(_strength_figure(result), width="stretch", key="strength-e1rm")
        st.plotly_chart(_training_load_figure(result), width="stretch", key="strength-load")
        st.dataframe(pd.DataFrame([item.model_dump() for item in result.strength.exercises]), hide_index=True)
        if result.strength.pareto_frontier:
            frame = pd.DataFrame([item.model_dump() for item in result.strength.pareto_frontier])
            st.scatter_chart(frame, x="bodyweight_kg", y="strength_index")
    with diet_tab:
        gap = "n/a" if result.diet.mip_gap is None else f"{result.diet.mip_gap:.1%}"
        st.write(f"Solver: **{result.diet.status}** · disclosed MIP gap: **{gap}**")
        st.plotly_chart(_diet_figure(result), width="stretch", key="diet-bounds")
        st.dataframe(pd.DataFrame([item.model_dump() for item in result.diet.daily]), hide_index=True)
        st.write("Selected foods")
        st.dataframe(pd.DataFrame([item.model_dump() for item in result.diet.entries]), hide_index=True)
        st.write("Coefficient stress tests")
        st.dataframe(pd.DataFrame([item.model_dump() for item in result.diet.sensitivity]), hide_index=True)
        st.write("Sampled non-dominated objective profiles (not an exhaustive frontier)")
        st.plotly_chart(_tradeoff_figure(result), width="stretch", key="diet-tradeoffs")
        st.dataframe(pd.DataFrame([item.model_dump() for item in result.diet_pareto]), hide_index=True)
    with data_tab:
        st.write(
            "The analysis core is device-independent. Apple Health is one native adapter; normalized "
            "CSV/JSONL can come from Garmin, Fitbit, COROS, a scale, a food logger, or manual records."
        )
        st.write(
            "Uploaded records remain in this local Streamlit process. Private reports contain dates and "
            "detailed observed/derived health series. The separate share-safe profile removes those fields, "
            "but derived categories can still be sensitive and must be reviewed before sharing."
        )
        st.json(
            {
                "days": result.cut.days,
                "weight_completeness": result.cut.weight_completeness,
                "intake_completeness": result.cut.intake_completeness,
                "usable_strength_sets": result.strength.usable_sets,
                "food_data_quality": result.diet.weighted_data_quality,
            }
        )
        minimized = json.dumps(
            build_report_payload(result, "share-safe"),
            ensure_ascii=False,
            indent=2,
        )
        st.download_button(
            "Download minimized JSON summary",
            data=minimized,
            file_name="cutsignal.share-safe.json",
            mime="application/json",
        )


def main() -> None:
    st.set_page_config(page_title="CutSignal", page_icon="📉", layout="wide")
    st.title("CutSignal")
    st.caption("Device-independent fat-loss, strength-retention, and robust food-plan analytics")
    st.warning(
        "Decision support only. CutSignal does not prescribe calories, diagnose a plateau, or replace "
        "individualized medical or nutrition care."
    )
    with st.sidebar:
        st.header("Run locally")
        mode = st.radio("Input", ["Synthetic demo", "Casebook", "Normalized JSONL"])
        particles = 1_000
        if mode != "Casebook":
            particles = st.slider("Particle count", min_value=500, max_value=10_000, value=1_000, step=500)
        optimizer_seconds = st.slider("MILP seconds per main solve", 2, 30, 3)

    result: PipelineResult | None = None
    if mode == "Casebook":
        cases = list_cases()
        selected_id = st.selectbox(
            "Executable case",
            options=[item.id for item in cases],
            format_func=lambda case_id: next(item.title for item in cases if item.id == case_id),
        )
        case_result: CaseRunResult | None = None
        if st.button("Run selected case", type="primary"):
            with st.spinner("Running deterministic case assertions…"):
                case_result = run_case(
                    selected_id,
                    optimizer_seconds=float(optimizer_seconds),
                )
                st.session_state["cutsignal_case_result"] = case_result.model_dump(mode="json")
        stored_case = st.session_state.get("cutsignal_case_result")
        if stored_case is not None and stored_case.get("case_id") == selected_id:
            case_result = CaseRunResult.model_validate(stored_case)
        _render_casebook(cases, selected_id, case_result)
        return
    if mode == "Synthetic demo":
        if st.button("Run synthetic demo", type="primary"):
            with st.spinner("Running five statistical sensitivity scenarios and robust MILPs…"):
                result = PipelineResult.model_validate(_run_demo(particles, float(optimizer_seconds)))
    else:
        st.write("Upload validated normalized files. Nothing is sent to a CutSignal server.")
        daily_file = st.file_uploader("Daily JSONL", type=["jsonl"], key="daily")
        strength_file = st.file_uploader("Strength JSONL", type=["jsonl"], key="strength")
        food_file = st.file_uploader("Food JSONL", type=["jsonl"], key="foods")
        constraint_file = st.file_uploader("Diet constraints JSON", type=["json"], key="constraints")
        if st.button("Analyze uploaded data", type="primary"):
            if not all((daily_file, strength_file, food_file, constraint_file)):
                st.error("All four normalized inputs are required.")
            else:
                try:
                    daily = _read_uploaded_jsonl(daily_file.getvalue(), DailyObservation)
                    strength = _read_uploaded_jsonl(strength_file.getvalue(), StrengthSet)
                    foods = _read_uploaded_jsonl(food_file.getvalue(), FoodItem)
                    constraints = _read_uploaded_constraints(constraint_file.getvalue())
                    with st.spinner("Running analysis locally…"):
                        result = run_pipeline(
                            daily,
                            strength,
                            foods,
                            constraints,
                            cut_config=CutAnalysisConfig(filter=ParticleFilterConfig(particles=particles)),
                            diet_time_limit_seconds=float(optimizer_seconds),
                            pareto_time_limit_seconds=max(1.0, optimizer_seconds / 2),
                        )
                except (CutSignalError, UnicodeDecodeError, ValueError) as exc:
                    st.error(f"Input could not be analyzed: {exc}")
    if result is not None:
        st.session_state["cutsignal_result"] = result.model_dump(mode="json")
    stored = st.session_state.get("cutsignal_result")
    if stored is not None:
        _render_result(PipelineResult.model_validate(stored))
    else:
        st.markdown(
            """
            ### One project, three connected questions

            - Is the recent scale trend really flat once fluid and logging uncertainty are modeled?
            - Is strength being retained, or do exercise-level decline and fatigue signals agree?
            - Can a weekly food plan satisfy user-supplied targets under nutrition and price uncertainty?
            """
        )


if __name__ == "__main__":
    main()
