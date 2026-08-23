# Validation strategy

Validation is layered so that a green UI does not substitute for analytical evidence.

## Automated gates

1. Pydantic validation tests ranges, missing fields, and model invariants.
2. Fixture adapters test kg/lb/kJ conversion, duplicate dates, phone/watch overlap, sleep interval
   merging, malformed exports, ZIP traversal, and provider detection.
3. Statistical tests check fixed-seed reproducibility, linked particle histories, missing calendar
   days, heavy-tailed updates, known synthetic change points, evidence-gate branches, and local
   outlier exclusion.
4. Strength tests check e1RM behavior, uncertainty-weighted regression, empirical-Bayes output,
   warm-up exclusion, weekly load summaries, short-history gating, body-weight normalization, and
   combined decline/fatigue recovery review.
5. Optimization tests require every modeled robust constraint to pass, independently reconstruct
   all constraints from the selected menu, verify solver status/gap and infeasibility paths, and
   construct a separate SciPy matrix form. A regression test also forces every optional trade-off
   solve to fail and requires the validated primary point plus all four failure records to survive.
6. Pipeline/report tests verify decision precedence and structural separation between sensitive
   private reports and data-minimized share-safe reports.
7. Streamlit receives a separate click-level application test. Core combined statement-and-branch
   coverage remains ≥90%, and branch-only coverage remains ≥80%; both are reported separately.
8. Nine executable synthetic cases cover typical, abstention, boundary, stress-failure, and
   schema-migration behaviors.
9. A fixed 12-run known-truth simulation grid compares the linked-particle rate with a recent-weight
   OLS baseline and reports per-scenario errors, interval coverage, Brier score, false positives,
   false negatives, and fixed-grid bootstrap intervals.
10. sdist/wheel build, isolated temporary-venv installation, public API and packaged resources,
   `pip check`, `pip-audit`, CLI help, claims registry, local documentation links/images,
   privacy/credential scan,
   end-to-end run, and artifact hashes are recorded in `artifacts/verification.json`.

The full verifier may take 15–25 minutes on a cold or slow machine. It prints bounded gate and
fresh-install phase progress. Network-dependent checks fail closed and do not reuse stale evidence.

## What “100” means

`scripts/score_project.py` awards 100 only when all versioned gates pass for the current checkout
fingerprint. It means the repository satisfies its declared engineering rubric. It does not mean
the model is 100% accurate, clinically validated, bias-free, or suitable for deployment.

## External validation roadmap

- Compare wearable energy and heart-rate fields against controlled indirect-calorimetry studies,
  stratified by device and activity.
- Evaluate measurement error and missingness across skin tone, device placement, age, and activity
  without treating a convenient cohort as representative.
- Pre-register plateau-detection simulation conditions and report calibration, false positives,
  detection delay, and abstention rate.
- Validate e1RM trends against protocol-controlled test sessions rather than only competition totals.
- Run diet feasibility with region-specific prices and verified food records; report how often robust
  plans remain feasible under held-out label/price shocks.

External data are never bundled until license, consent, participant privacy, and redistribution
rights have been reviewed.

The local verifier is evidence of local execution only. GitHub workflow files are not reported as
passing CI until a public remote actually executes them.

## Internal synthetic evaluation result boundary

Run `python scripts/evaluate_synthetic.py`. The generator fixes true linear trend rates and applies
clean, high-fluid, missing-data, outlier, and intake-bias conditions. Both methods see the same daily
stream and recent rate window; OLS intentionally ignores intake and earlier history. The scenario
grid is declared in code before scoring and failed scenarios remain in JSON.

These results test behavior against truths defined by this project's own generator. They do not
establish external calibration, population calibration, subgroup performance, causal validity,
detection delay under real behavior, or benefit to users. Bootstrap intervals describe resampling
of the fixed grid only.

The fixed-grid result is deliberately not a success-only exhibit. At 500 particles, the current
linked-trajectory method misses three of four true plateau classifications at the declared 0.75
threshold and its nominal model interval contains the fixed truth in 10 of 12 scenarios (83.3%).
The OLS comparator misses all four plateaus and contains truth in 8 of 12 scenarios (66.7%). Those
failures remain in the JSON. They are evidence for abstention and further calibration work, not a
reason to tune the generator or threshold after observing this grid.
