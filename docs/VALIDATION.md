# Validation strategy

Validation is layered so that a green UI does not substitute for analytical evidence.

## Automated gates

1. Pydantic validation tests ranges, missing fields, and model invariants.
2. Fixture adapters test kg/lb/kJ conversion, duplicate dates, phone/watch overlap, sleep interval
   merging, malformed exports, ZIP traversal, and provider detection.
3. Statistical tests check fixed-seed reproducibility, missing calendar days, heavy-tailed updates,
   known synthetic change points, evidence-gate branches, and local outlier exclusion.
4. Strength tests check e1RM behavior, warm-up exclusion, short-history gating, body-weight
   normalization, and combined decline/fatigue recovery review.
5. Optimization tests require every modeled robust constraint to pass, verify solver status/gap,
   exercise infeasibility paths, and independently construct the SciPy matrix form.
6. Pipeline/report tests verify decision precedence and absence of source identifiers.
7. Streamlit receives a separate application startup test; core branch coverage remains ≥90%.
8. Wheel build, CLI help, privacy scan, deterministic end-to-end synthetic run, and artifact hashes
   are recorded in `artifacts/verification.json`.

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
