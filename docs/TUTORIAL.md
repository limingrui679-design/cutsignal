# First analysis tutorial

This path reaches a complete result without personal data. Allow several minutes on first install;
the optimizer and plotting stack are substantial.

## 1. Install and diagnose

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip 'setuptools>=83,<85'
python -m pip install -e '.[ui]'
cutsignal doctor
```

`doctor` reports Python/dependency versions and optional UI availability. It does not inspect health
files, environment-variable values, or credentials.

## 2. Run the fixed synthetic workflow

```bash
cutsignal demo --output artifacts/demo
```

Open `artifacts/demo/report.html` locally. Read the profile warning first, then inspect:

1. the trend median and interval rather than one scale value;
2. the five logging/noise sensitivity scenarios and action stability;
3. exercise-level performance, training load, and fatigue agreement;
4. solver status, MIP gap, independent constraint validation, and failed stress scenarios;
5. the integrated gate and its requested next evidence.

Compare `report.share-safe.html` before sharing anything. It is minimized, not anonymous.

## 3. Exercise decision and failure cases

```bash
cutsignal cases run missing-intake-abstain
cutsignal cases run budget-shock
cutsignal cases run generic-schema-migration
cutsignal cases verify --output artifacts/cases.json
```

Each JSON result includes configuration, assertions, observations, duration, evidence type, and an
explicit limitation. A failing assertion is retained as evidence and returns a nonzero exit code.

## 4. Run the known-truth method stress benchmark

```bash
python scripts/evaluate_synthetic.py --output artifacts/synthetic-evaluation.json
```

The output compares linked particle trajectories with a simple recent-weight OLS baseline across a
fixed grid of clean, high-fluid, missing-data, outlier, and intake-bias conditions. Read every
scenario, not only aggregate scores. This benchmark is project-generated and cannot establish
external calibration or population accuracy.

## 5. Migrate a normalized daily CSV

Start with a synthetic copy of the expected shape:

```csv
date,weight_lb,calories,steps,sleep_hours
2026-01-01,176.4,2050,8200,7.2
2026-01-02,176.0,2100,9100,7.0
```

```bash
cutsignal import daily-csv daily.csv data/private/daily.jsonl --provider my-export
```

Then normalize strength and food records as described in [DEVICE_ADAPTERS.md](DEVICE_ADAPTERS.md)
and run `cutsignal analyze`. Never commit the private input or generated private-detail report.

## 6. Verify a development checkout

```bash
python -m pip install -e '.[dev]'
python scripts/verify_project.py
python scripts/score_project.py
```

The long verifier builds and installs the wheel in a temporary environment and queries an external
vulnerability service. A local pass proves only that the exact local checkout passed those gates.
For common failures, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
