from __future__ import annotations

from cutsignal.analysis.cut import CutAnalysisConfig
from cutsignal.analysis.state_space import ParticleFilterConfig
from cutsignal.pipeline import integrate_decisions, run_pipeline
from cutsignal.privacy import audit_paths
from cutsignal.reporting.html import render_html_report


def _pipeline(short_daily, repeated_strength, demo_foods, small_constraints):
    return run_pipeline(
        short_daily,
        repeated_strength,
        demo_foods,
        small_constraints,
        cut_config=CutAnalysisConfig(
            filter=ParticleFilterConfig(particles=500),
            maximum_tdee_interval_width=2_000,
        ),
        diet_time_limit_seconds=2,
        pareto_time_limit_seconds=1,
    )


def test_pipeline_decision_precedence_and_report_redaction(
    tmp_path, short_daily, repeated_strength, demo_foods, small_constraints
) -> None:
    result = _pipeline(short_daily, repeated_strength, demo_foods, small_constraints)
    assert result.integrated_decision.action in {
        "continue",
        "collect_more_data",
        "review_recovery_first",
        "consider_plan_review",
        "validate_food_data",
    }
    path = render_html_report(result, tmp_path / "report.html")
    html = path.read_text(encoding="utf-8")
    json_text = path.with_suffix(".json").read_text(encoding="utf-8")
    assert "CutSignal" in html
    assert "Coefficient stress tests" in html
    assert "source_id" not in html
    assert "test-fixture" not in html
    assert "source_id" not in json_text
    assert path.with_suffix(".json").exists()

    collect = result.cut.model_copy(
        update={"decision": result.cut.decision.model_copy(update={"action": "collect_more_data"})}
    )
    assert integrate_decisions(collect, result.strength, result.diet).action == "collect_more_data"
    recovery = result.strength.model_copy(
        update={"decision": result.strength.decision.model_copy(update={"action": "review_recovery"})}
    )
    assert integrate_decisions(result.cut, recovery, result.diet).action == "review_recovery_first"
    quality = result.diet.model_copy(update={"weighted_data_quality": 0.5})
    assert integrate_decisions(result.cut, result.strength, quality).action == "validate_food_data"
    review = result.cut.model_copy(
        update={"decision": result.cut.decision.model_copy(update={"action": "consider_review"})}
    )
    high_quality = result.diet.model_copy(update={"weighted_data_quality": 0.95})
    stable_strength = result.strength.model_copy(
        update={"decision": result.strength.decision.model_copy(update={"action": "stable"})}
    )
    assert integrate_decisions(review, stable_strength, high_quality).action == "consider_plan_review"


def test_privacy_audit_finds_names_and_content(tmp_path) -> None:
    clean = tmp_path / "clean.txt"
    clean.write_text("deterministic synthetic fixture", encoding="utf-8")
    assert audit_paths([clean]).passed

    named = tmp_path / "apple-health.zip"
    named.write_bytes(b"placeholder")
    content = tmp_path / "notes.txt"
    address = "person" + "@" + "example.com"
    phone = "+" + "1" + " 555" + " 123" + " 4567"
    content.write_text(f"contact {address} or {phone}", encoding="utf-8")
    result = audit_paths([tmp_path])
    assert not result.passed
    assert any("health export" in item.finding for item in result.findings)
    assert {item.finding for item in result.findings} >= {
        "possible sensitive content: email",
        "possible sensitive content: phone",
    }
