from __future__ import annotations

import pytest

from cutsignal.analysis.cut import CutAnalysisConfig
from cutsignal.analysis.state_space import ParticleFilterConfig
from cutsignal.optimization.diet import TradeoffProfileFailure
from cutsignal.pipeline import integrate_decisions, run_pipeline
from cutsignal.privacy import audit_paths
from cutsignal.reporting.html import render_html_report
from cutsignal.reporting.profiles import build_report_payload


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
    path = render_html_report(result, tmp_path / "report.html", profile="private")
    html = path.read_text(encoding="utf-8")
    json_text = path.with_suffix(".json").read_text(encoding="utf-8")
    assert "CutSignal" in html
    assert "Coefficient stress tests" in html
    assert "source_id" not in html
    assert "test-fixture" not in html
    assert "source_id" not in json_text
    assert 'data-report-profile="private"' in html
    assert '"report_profile": "private"' in json_text
    assert "observed_weight_kg" in json_text
    assert "Sensitive private report" in html
    assert 'class="skip-link"' in html
    assert 'aria-labelledby="trend-weight-chart-title trend-weight-chart-description"' in html
    assert 'class="table-wrap"' in html
    assert 'scope="col"' in html
    assert "@media (max-width: 600px)" in html
    assert path.with_suffix(".json").exists()

    minimized = render_html_report(result, tmp_path / "share-safe.html", profile="share-safe")
    minimized_html = minimized.read_text(encoding="utf-8")
    minimized_json = minimized.with_suffix(".json").read_text(encoding="utf-8")
    assert 'data-report-profile="share-safe"' in minimized_html
    assert 'aria-label="Decision signals"' in minimized_html
    assert '<caption class="sr-only">' in minimized_html
    assert '"report_profile": "share-safe"' in minimized_json
    assert '"mip_gap_category":' in minimized_json
    for forbidden in (
        "observed_weight_kg",
        "energy_intake_kcal",
        "state_estimates",
        str(result.cut.start_date),
        result.strength.exercises[0].exercise,
        result.diet.entries[0].food_name,
    ):
        assert forbidden not in minimized_html
        assert forbidden not in minimized_json
    with pytest.raises(ValueError, match="unsupported report profile"):
        build_report_payload(result, "unknown")  # type: ignore[arg-type]

    diagnosed = result.model_copy(
        update={
            "diet_tradeoff_failures": [
                TradeoffProfileFailure(
                    label="fast-prep",
                    error_type="OptimizationInfeasibleError",
                    reason="synthetic profile timeout",
                )
            ]
        }
    )
    diagnosed_report = render_html_report(diagnosed, tmp_path / "diagnosed.html", profile="private")
    assert "fast-prep: synthetic profile timeout" in diagnosed_report.read_text(encoding="utf-8")
    diagnosed_minimized = render_html_report(
        diagnosed,
        tmp_path / "diagnosed.share-safe.html",
        profile="share-safe",
    )
    diagnosed_json = diagnosed_minimized.with_suffix(".json").read_text(encoding="utf-8")
    assert '"failed_trade_off_profiles": [' in diagnosed_json
    assert '"fast-prep"' in diagnosed_json
    assert "synthetic profile timeout" not in diagnosed_json

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

    large_text = tmp_path / "renamed-data.txt"
    large_text.write_text("synthetic but requires complete review", encoding="utf-8")
    bounded = audit_paths([large_text], max_text_bytes=8)
    assert not bounded.passed
    assert any("complete-scan limit" in item.finding for item in bounded.findings)


def test_privacy_audit_finds_credentials_and_private_keys(tmp_path) -> None:
    token_file = tmp_path / "configuration.txt"
    token = "gh" + "p_" + "A" * 40
    token_file.write_text(f"credential={token}", encoding="utf-8")
    private_key = tmp_path / "renamed.txt"
    private_key.write_text("-----BEGIN " + "PRIVATE KEY-----\nsynthetic", encoding="utf-8")
    environment = tmp_path / ".env.production"
    environment.write_text("SYNTHETIC=true", encoding="utf-8")

    result = audit_paths([tmp_path])

    assert not result.passed
    findings = {item.finding for item in result.findings}
    assert "possible sensitive content: github_token" in findings
    assert "possible sensitive content: private_key" in findings
    assert any(item.path.endswith(".env.production") for item in result.findings)

    example = tmp_path / ".env.example"
    example.write_text("OPTIONAL_API_KEY=DEMO_KEY\n", encoding="utf-8")
    assert audit_paths([example]).passed


def test_privacy_audit_does_not_treat_metrics_or_commit_ids_as_phones(tmp_path) -> None:
    evidence = tmp_path / "verification.yml"
    evidence.write_text(
        "coverage: 91.93412162162163\n"
        "commit: 54b5241c2b4e7b15448aec6766ce61f21af451f4\n"
        "reference: https://doi.org/10.1214/aos/1176344136\n",
        encoding="utf-8",
    )

    result = audit_paths([evidence])

    assert result.passed


def test_privacy_audit_rejects_local_home_paths(tmp_path) -> None:
    document = tmp_path / "audit.md"
    local_path = "/" + "Users" + "/example/Documents/private-project"
    document.write_text(f"checkout: {local_path}\n", encoding="utf-8")

    result = audit_paths([document])

    assert not result.passed
    assert any(item.finding == "possible sensitive content: local_home_path" for item in result.findings)


def test_privacy_directory_walk_skips_declared_generated_evidence(tmp_path) -> None:
    generated = tmp_path / "artifacts"
    generated.mkdir()
    generated.joinpath("verification.json").write_text(
        "local_path: /" + "Users" + "/example/project\n",
        encoding="utf-8",
    )
    tmp_path.joinpath(".coverage").write_text("generated binary-like evidence", encoding="utf-8")
    tmp_path.joinpath("safe.md").write_text("synthetic public documentation", encoding="utf-8")

    result = audit_paths([tmp_path])

    assert result.passed
    assert result.files_scanned == 1
