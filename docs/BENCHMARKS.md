# Benchmark review

Accessed **2026-08-24**. This review uses official repositories, documentation, releases, and
security/advisory pages. Popularity was not a selection gate. The versions below are research
anchors, not vendored dependencies, endorsements, or claims that CutSignal matches their community
scale. No code, copy, or visual identity was mechanically copied.

## Comparison matrix

| Category | Project and reference | Core workflow and visible maintenance evidence | Mechanism absorbed by CutSignal | Why it applies | What is intentionally not copied |
|---|---|---|---|---|---|
| Direct | [FitTrackee](https://github.com/SamR1/FitTrackee), [v1.3.4](https://github.com/SamR1/FitTrackee/releases/tag/v1.3.4), mirror HEAD `538418239054e8c6f372aa9c7c50e9cf11c18058` | Self-hosted workout import/view workflow, API/CLI, active 2026 release line, feature and troubleshooting docs | Explicit first-run workflow, adapter boundaries, troubleshooting navigation | Both normalize personal fitness exports into inspectable local analysis | Social/multi-user server scope; GPX/FIT-first architecture; AGPL code |
| Direct | [wger](https://github.com/wger-project/wger), [v2.6](https://github.com/wger-project/wger/releases/tag/2.6) | Workout, nutrition, and weight management; OpenAPI; Docker; translations; 2026 release; a visible [stored-XSS advisory](https://github.com/wger-project/wger/security/advisories/GHSA-6f54-qjvm-wwq3) shows disclosure and remediation | Explicit security boundary, structured API/data contracts, contribution surface | Covers the same health/training/food neighborhood at product scale | Hosted multi-user stack, medical-goal semantics, AGPL implementation |
| Direct | [openScale](https://github.com/oliexdev/openScale), [v3.1.2](https://github.com/oliexdev/openScale/releases/tag/v3.1.2) | Local weight tracking, device-driver catalog, Kotlin/Compose rewrite, current release and public [beta feedback](https://github.com/oliexdev/openScale/issues/1139) | Device adapter contract and honest hardware-support caveats | Demonstrates how device diversity should end at a stable domain model | Android/Bluetooth driver architecture and device-specific UI |
| Direct | [OpenTracks](https://codeberg.org/OpenTracksApp/OpenTracks), v4.28.2; [archived GitHub mirror](https://github.com/OpenTracksApp/OpenTracks) v4.22.0 | Offline activity tracking and export interoperability; upstream visibly moved to active Codeberg | Offline-first language, export interoperability, repository-move transparency | Strong privacy and portable-record precedent | GPS recorder/background-service architecture and Android UI |
| Adjacent | [ActivityWatch](https://github.com/ActivityWatch/activitywatch), [v0.13.2](https://github.com/ActivityWatch/activitywatch/releases/tag/v0.13.2) | Local data ownership, modular watchers/server/web UI, signed binary releases | Local-first value proposition and modular ingestion/core separation | A mature precedent for sensitive self-tracking without a required cloud | Passive surveillance/event model and always-on collection |
| Adjacent | [ArviZ](https://python.arviz.org/en/latest/), [v1.3.0](https://github.com/arviz-devs/arviz/releases/tag/v1.3.0) | Statistical diagnostics/plots, modular package, [Diátaxis content structure](https://python.arviz.org/en/latest/contributing/content_structure.html), minimal/full/nightly and visual tests | Separate tutorial/how-to/reference/explanation; expose uncertainty diagnostics | Closest documentation and uncertainty-expression benchmark | Treating generic MCMC diagnostics as domain validation |
| Adjacent | [Evidently](https://github.com/evidentlyai/evidently), [v0.7.21](https://github.com/evidentlyai/evidently/releases/tag/v0.7.21) | Visual reports, test gates, saved snapshots/JSON, local workspace, early input failures | Human report plus machine evidence, assertion-oriented failure output | Same need to make analytical state inspectable and automatable | ML/LLM monitoring taxonomy, telemetry/cloud product scope |
| Adjacent | [OR-Tools](https://github.com/google/or-tools), [v9.15](https://github.com/google/or-tools/releases/tag/v9.15) | Solver examples across languages and explicit status semantics | Preserve status/gap and independently validate hard constraints | Direct benchmark for optimization result discipline | Replacing a working small Python MILP layer solely for brand parity |
| Adjacent | [Open Food Facts server](https://github.com/openfoodfacts/openfoodfacts-server), [v2.102.0](https://github.com/openfoodfacts/openfoodfacts-server/releases/tag/v2.102.0), API v3.6 | OpenAPI, versioned API docs, explicit crowdsourced-data, rate-limit, and license caveats | Propagate provenance/quality; bound response size; reject unsafe identifiers | One of CutSignal's optional food-record sources | Treating crowd records as verified nutrition/local availability; AGPL server code |
| Exemplar | [scikit-learn](https://github.com/scikit-learn/scikit-learn), [1.9.0](https://github.com/scikit-learn/scikit-learn/releases/tag/1.9.0) | Governance, runnable release examples, compatibility/deprecation policy, minimal reproductions | Evidence-oriented examples, explicit compatibility and contribution rules | Mature scientific Python maintenance benchmark | Broad estimator API or release cadence unsupported by one maintainer |
| Exemplar | [pandas](https://github.com/pandas-dev/pandas), [3.0.5](https://github.com/pandas-dev/pandas/releases/tag/v3.0.5) | Test-driven development, cross-platform CI, documentation builds, maintenance/release policy | Regression-first changes and platform matrix | Mature data-engineering quality benchmark | Large-team governance structure or unsupported stability promises |
| Exemplar | [FastAPI](https://github.com/fastapi/fastapi), [0.141.1](https://github.com/fastapi/fastapi/releases/tag/0.141.1) | Progressive tested tutorials, explicit error contracts, generated reference | First-success tutorial and actionable input errors | Strong onboarding pattern for a typed Python product | Web-service/API-server scope; CutSignal remains local-first |

## Review findings and actual absorption

- Direct projects are strongest on device/file interoperability and ongoing user-facing workflows;
  CutSignal therefore adds a schema-migration case, a data card, a `doctor` command, and a short
  tutorial rather than pretending to support every vendor natively.
- ArviZ and FastAPI demonstrate why tutorials, how-to material, explanation, and reference should not
  be one README. CutSignal now routes those jobs to separate documents.
- Evidently and OR-Tools reinforce dual human/machine evidence and explicit solver/result status.
  CutSignal keeps JSON receipts, scenario assertions, solver gaps, and independent feasibility checks.
- wger's public advisory and Open Food Facts' data caveats reinforce that privacy/security and source
  quality need operational controls. CutSignal bounds food API bodies and preserves unit/source fields.
- None of these projects can supply CutSignal's missing external calibration, controlled strength
  validation, regional food verification, real-user usability evidence, or prospective outcomes.
  Repository polish cannot close those evidence gaps.

## Selection limits

This is a dated, qualitative benchmark review, not a systematic literature review or permanent
ranking. Issue activity and releases can change after the access date. Repository visibility does
not prove adoption, outcome quality, security, or methodological validity.
