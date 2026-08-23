# Changelog

All notable changes follow a lightweight Keep a Changelog format. The project uses semantic
versioning while the public API stabilizes.

## [Unreleased]

### Added

- Fixed 12-run known-truth recent-rate evaluation with a same-window OLS baseline, per-scenario
  errors, interval coverage, Brier score, classification failures, and bounded claims.
- Ninth schema-migration case, data card, benchmark matrix, first-analysis tutorial,
  troubleshooting guide, support boundary, and `cutsignal doctor` diagnostics.
- Verified public repository metadata, CI/security badges, typed issue routing, and confidential
  vulnerability-reporting links with a consistency gate.
- Fail-closed OSV audit evidence with transport-only bounded retries and per-Python CI artifact
  retention.
- Accessible report navigation, chart descriptions, responsive labeled tables, chart titles, and
  print/mobile styles.

### Fixed

- USDA nutrition normalization now uses explicit nutrient IDs and units, including kJ/kcal and
  mass conversion, instead of magnitude-based energy guessing.
- Diet stress scenarios now apply additional nutrition uncertainty as declared additive percentage
  points.
- Food API helpers now validate path identifiers and enforce a streamed 5 MiB response limit.
- CI now prints failed verifier output directly and preserves dependency-audit evidence for every
  supported Python matrix.
- Python 3.11 and isolated-install environments now replace vulnerable bootstrap `setuptools`
  versions with the audited `>=83,<85` range; duplicate service records share one package/advisory
  finding.

### Security

- GitHub Actions are pinned to verified full commit SHAs while Dependabot retains update coverage.
- Verification now clears only verifier-owned outputs, rejects ambiguous wheel directories, records
  hashes for eight score-critical artifacts, and refuses a score when any recorded artifact changes.

## [0.2.0] - 2026-08-20

### Added

- Linked-particle recent-rate posterior, explicit report profiles, and stricter evidence gates.
- e1RM uncertainty-weighted regression, empirical-Bayes trends, weekly training-load
  summaries, fatigue, change points, relative strength, and body-weight/strength trade-offs.
- Robust weekly food MILP, true solver status/MIP gap, independent post-solve checks, coefficient
  stress tests, and sampled non-dominated objective profiles.
- Eight executable decision/failure cases, explicit private/share-safe report profiles, bounded
  inputs, run receipts, claims registry, isolated-wheel smoke test, local Streamlit interface,
  privacy scanner, CI definitions, and machine-evidence project score.

### Changed

- Core installation no longer pulls Streamlit/Plotly; the dashboard is the `ui` extra.
- CSV/JSONL importers now enforce shared size/row/line limits and food CSV accepts JSON source data.
- Public wording distinguishes synthetic/internal evidence from external validation and adoption.

## [0.1.0] - 2026-08-20

### Added

- Device-independent daily, strength, food, and constraint models.
- Secure Apple Health streaming import plus generic health, Hevy, and Strong CSV adapters.
- Particle-filter weight/TDEE inference, plateau probability, BIC change points, five sensitivity
  scenarios, and evidence gates.
- e1RM consensus, empirical shrinkage, fatigue, change points, and relative-strength analysis.
- Robust weekly food MILP, solver status/gap, coefficient stress tests, and objective profiles.
- CLI, local Streamlit interface, synthetic demo, offline report, privacy scanner, and initial
  machine-evidence score.
