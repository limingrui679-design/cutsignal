# Changelog

All notable changes follow a lightweight Keep a Changelog format. The project uses semantic
versioning while the public API stabilizes.

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
