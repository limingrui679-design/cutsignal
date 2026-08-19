# CutSignal

CutSignal is a privacy-first, device-agnostic analytics project that combines three decisions
people often evaluate separately:

1. **CutSignal** estimates trend weight and latent total daily energy expenditure (TDEE), then
   asks whether an apparent plateau is distinguishable from fluid and measurement noise.
2. **LeanGuard** estimates whether strength change exceeds normal session-to-session variation
   while body weight is changing.
3. **BudgetCut** builds a robust weekly food plan under user-supplied calorie, protein, fiber,
   price, preparation-time, preference, allergy, and variety constraints.

The software does **not** diagnose a plateau, prescribe calories, recommend rapid weight loss,
or replace a clinician or registered dietitian. Its output is an evidence gate:
`continue`, `collect more data`, `review recovery first`, or `consider reviewing the plan`.

## Why this project is different

- A bootstrap particle filter models trend weight, latent TDEE, fluid shifts, heavy-tailed scale
  noise, missing intake, and an uncertain energy-density coefficient.
- Every TDEE result includes a 95% interval and five logging/noise sensitivity scenarios.
- Change points use globally selected piecewise-linear segments with a BIC complexity penalty.
- Exercise trends shrink noisy per-exercise slopes toward a cross-exercise prior and retain
  formula uncertainty for estimated one-repetition maximum (e1RM).
- The diet planner is a genuine mixed-integer linear program (MILP), not a greedy recipe list.
  Robust constraints use conservative nutrition and price coefficients.
- Apple Health, Hevy, Strong, generic CSV, USDA FoodData Central, Open Food Facts, and optional
  OpenPowerlifting adapters all feed the same validated domain models.
- Reports are self-contained and offline. Raw records, device identifiers, and source IDs are
  omitted.

## Quick start

CutSignal requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'

# Generate synthetic data, run all three engines, and create an offline report.
cutsignal demo --output artifacts/demo

# Launch the local interface. No cloud account is required.
cutsignal ui
```

The demo is deterministic and contains no personal information. Open
`artifacts/demo/report.html` after it finishes.

## Supported inputs

### Daily health data

The normalized daily schema supports:

- body weight;
- logged energy intake;
- active energy;
- steps;
- sleep duration;
- training minutes;
- resting heart rate;
- heart-rate variability.

Apple Health `.zip` and `.xml` exports are parsed as streams without extracting the archive.
For additive measures such as steps, records from a phone and a watch are **not blindly added**.
CutSignal aggregates each source separately and uses the largest source-day total, while adding a
quality flag that records the reconciliation. This is a transparent heuristic, not a claim that
the selected source is always correct.

```bash
cutsignal import apple-health ~/Downloads/export.zip data/private/daily.jsonl
cutsignal import daily-csv daily.csv data/private/daily.jsonl
```

Generic daily CSV aliases include `date`, `weight_kg`, `weight_lb`, `calories`, `steps`,
`sleep_hours`, `training_minutes`, `resting_hr_bpm`, and `hrv_ms`.

### Strength data

Hevy and Strong exports are auto-detected. A generic file needs date, exercise, weight, and reps;
RPE, set type, body weight, and duration are optional.

```bash
cutsignal import strength hevy-export.csv data/private/strength.jsonl
```

Warm-up sets and sets above the configured repetition ceiling are retained at import but excluded
from e1RM trend estimation. They are counted in the quality report.

### Food data

Food candidates can be stored as validated JSONL. Helper functions normalize official USDA FoodData
Central details responses and Open Food Facts products. USDA records receive a stronger default
confidence prior; crowdsourced Open Food Facts completeness is scored and propagated into the plan.
Users supply local prices and serving assumptions.

API keys are read from the environment and are never written to reports. Do not commit `.env`.

## Statistical methods

### Trend weight and TDEE

For particle `i` on day `t`, the simplified latent dynamics are:

```text
TDEE[i,t]         = TDEE[i,t-1] + process noise
trend_weight[i,t] = trend_weight[i,t-1]
                    + (logged_intake[t] - TDEE[i,t]) / energy_density[i]
                    + process noise
fluid[i,t]        = phi * fluid[i,t-1] + process noise
scale_weight[t]   = trend_weight[i,t] + fluid[i,t] + Student-t noise
```

The energy-density term is a distribution, not a fixed biological constant. Missing intake widens
the trend process. A Student-t likelihood limits the influence of an isolated scale outlier.
Systematic resampling occurs only when effective sample size falls below the configured threshold.

The plateau probability is the posterior-normal approximation that the recent weekly rate lies
inside a user-visible band, defaulting to ±0.10 kg/week. A plan-review signal is blocked unless
duration, weight coverage, intake coverage, interval width, and sensitivity stability pass their
gates.

### Strength retention

LeanGuard uses the median of Epley, Brzycki, and Lombardi e1RM formulas. If RPE exists, up to four
repetitions in reserve are incorporated. Formula disagreement, high repetitions, short histories,
and missing RPE widen uncertainty or create quality flags.

Per-exercise slopes are reliability-weighted toward the median cross-exercise slope. The output
includes absolute e1RM change, allometrically body-weight-normalized change, decline probability,
fatigue signals, exercise-level change points, and a body-weight/strength Pareto frontier.

### Robust food planning

BudgetCut chooses integer servings over multiple days. Binary variables represent whether a food is
used on a day and anywhere in the week. Constraints cover:

- lower and upper calories per day;
- lower protein, fiber, and optional micronutrients;
- optional upper sodium;
- upper daily cost and preparation time;
- maximum days per food and minimum unique foods;
- required/forbidden dietary tags and excluded allergens.

In robust mode, minimum nutrients use `value × (1 - uncertainty)`, while maximum nutrients and
prices use `value × (1 + uncertainty)`. Five explicit objective profiles produce a non-dominated
cost/preparation/preference frontier. PuLP builds the MILP and the open-source HiGHS backend solves
it. The report distinguishes a proven optimum from a time-limited feasible incumbent and always
discloses the MIP gap when the solver provides one.

## Privacy model

- Real exports belong under `data/raw`, `data/private`, or another ignored local directory.
- The repository ships only deterministic synthetic demo data.
- Apple Health XML is streamed and never extracted to a temporary folder.
- Generated HTML excludes source IDs, device IDs, raw records, credentials, and birth dates.
- `cutsignal privacy-audit PATH` scans a proposed public tree for likely health exports and common
  identifiers.
- There is no telemetry, user account, hosted database, advertising SDK, or model API call.

If sensitive data has ever been committed, `.gitignore` is not enough: remove it from Git history
and rotate any exposed credential.

## Reproducibility and quality

```bash
ruff check .
ruff format --check .
mypy src/cutsignal
pytest --cov=cutsignal --cov-report=term-missing  # analytical/adapter core >= 90%
python -m build --wheel
python scripts/verify_project.py
python scripts/score_project.py
```

The UI is verified separately with Streamlit's application test harness. The score is not an
aesthetic self-rating. `score_project.py` consumes machine-readable evidence
from the verifier and awards points only for passing functional, statistical, optimization,
privacy, test, static-analysis, packaging, documentation, and end-to-end gates. A score of 100
therefore means every published gate passed for that exact checkout; it does not mean the health
model is universally accurate.

## Data-source boundaries

- USDA FoodData Central data are public domain/CC0; attribution is retained in provenance.
- Open Food Facts uses ODbL/database-content licenses and explicitly warns that crowdsourced data
  may be incomplete or inaccurate.
- OpenPowerlifting meet-data CSV files are dedicated to the public domain. Competition weigh-ins,
  including acute weight cuts, are not treated as longitudinal fat-loss ground truth.
- Apple, Hevy, Strong, Garmin, Fitbit, COROS, USDA, Open Food Facts, and OpenPowerlifting do not
  endorse or sponsor CutSignal.

See `docs/DATA_SOURCES.md`, `docs/METHODS.md`, `docs/PRIVACY.md`, `docs/DEVICE_ADAPTERS.md`, and
`docs/LIMITATIONS.md` for the full evidence and interpretation boundaries.

## License

CutSignal code is released under the MIT License. Third-party datasets retain their own licenses
and are not redistributed unless a registry entry explicitly permits it.
