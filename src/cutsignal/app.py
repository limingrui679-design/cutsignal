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
from cutsignal.models import DailyObservation, DietConstraints, FoodItem, StrengthSet
from cutsignal.pipeline import PipelineResult, run_pipeline
from cutsignal.synthetic import (
    demo_constraints,
    generate_daily_demo,
    generate_food_demo,
    generate_strength_demo,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


def _read_uploaded_jsonl(payload: bytes, model: type[ModelT]) -> list[ModelT]:
    output: list[ModelT] = []
    for line_number, line in enumerate(StringIO(payload.decode("utf-8")), start=1):
        if line.strip():
            try:
                output.append(model.model_validate_json(line))
            except ValueError as exc:
                raise ValueError(f"invalid JSONL line {line_number}: {exc}") from exc
    return output


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
        st.plotly_chart(_trend_figure(result), use_container_width=True)
        st.caption(decision.scope_note)
    with cut_tab:
        st.plotly_chart(_trend_figure(result), use_container_width=True)
        st.plotly_chart(_tdee_figure(result), use_container_width=True)
        st.write("Sensitivity scenarios")
        st.dataframe(pd.DataFrame([item.model_dump() for item in result.cut.sensitivity]), hide_index=True)
        st.write("Detected change points")
        st.dataframe(pd.DataFrame([item.model_dump() for item in result.cut.change_points]), hide_index=True)
    with strength_tab:
        st.write(f"Decision: **{result.strength.decision.action}**")
        st.dataframe(pd.DataFrame([item.model_dump() for item in result.strength.exercises]), hide_index=True)
        if result.strength.pareto_frontier:
            frame = pd.DataFrame([item.model_dump() for item in result.strength.pareto_frontier])
            st.scatter_chart(frame, x="bodyweight_kg", y="strength_index")
    with diet_tab:
        gap = "n/a" if result.diet.mip_gap is None else f"{result.diet.mip_gap:.1%}"
        st.write(f"Solver: **{result.diet.status}** · disclosed MIP gap: **{gap}**")
        st.dataframe(pd.DataFrame([item.model_dump() for item in result.diet.daily]), hide_index=True)
        st.write("Selected foods")
        st.dataframe(pd.DataFrame([item.model_dump() for item in result.diet.entries]), hide_index=True)
        st.write("Coefficient stress tests")
        st.dataframe(pd.DataFrame([item.model_dump() for item in result.diet.sensitivity]), hide_index=True)
        st.write("Non-dominated objective profiles")
        st.dataframe(pd.DataFrame([item.model_dump() for item in result.diet_pareto]), hide_index=True)
    with data_tab:
        st.write(
            "The analysis core is device-independent. Apple Health is one native adapter; normalized "
            "CSV/JSONL can come from Garmin, Fitbit, COROS, a scale, a food logger, or manual records."
        )
        st.write(
            "Uploaded records remain in this local Streamlit process. Reports omit raw rows, source IDs, "
            "device IDs, credentials, and birth dates."
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
        mode = st.radio("Input", ["Synthetic demo", "Normalized JSONL"])
        particles = st.slider("Particle count", min_value=500, max_value=10_000, value=2_000, step=500)
        optimizer_seconds = st.slider("MILP seconds per main solve", 2, 30, 5)

    result: PipelineResult | None = None
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
                    constraints = DietConstraints.model_validate(json.loads(constraint_file.getvalue().decode("utf-8")))
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
                except (UnicodeDecodeError, ValueError) as exc:
                    st.exception(exc)
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
