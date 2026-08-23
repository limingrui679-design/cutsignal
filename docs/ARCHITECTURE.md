# Architecture

CutSignal separates ingestion, validated domain records, analytical engines, decision policy, and
presentation. The statistical code never depends on a specific wearable SDK.

```mermaid
flowchart LR
  A[Apple Health XML or ZIP] --> N[DailyObservation]
  B[Generic health CSV] --> N
  C[Hevy Strong or generic CSV] --> S[StrengthSet]
  D[USDA OFF or food JSONL] --> F[FoodItem]
  N --> CUT[CutSignal particle filter]
  N --> LEAN[LeanGuard]
  S --> LEAN
  F --> BUDGET[BudgetCut robust MILP]
  CUT --> P[Evidence policy]
  LEAN --> P
  BUDGET --> P
  P --> CLI[CLI and explicit report profiles]
  P --> UI[Local Streamlit UI]
  P --> E[Run receipt and machine evidence]
```

## Module boundaries

- `importers/` converts external formats and attaches provenance. Adapters may reconcile duplicate
  devices, but they may not make health decisions.
- `models.py` is the contract between adapters and engines. Pydantic rejects impossible ranges and
  unknown fields.
- `analysis/state_space.py` owns latent weight/TDEE inference. `analysis/cut.py` owns sensitivity
  scenarios and evidence gates.
- `analysis/strength.py` owns e1RM, uncertainty-weighted regression, empirical-Bayes shrinkage,
  fatigue, weekly load summaries, and the body-weight/strength non-dominated set.
- `optimization/diet.py` owns eligibility filtering, robust constraints, solver status, stress
  tests, independent post-solve validation, and sampled objective profiles.
- `pipeline.py` is the only cross-engine policy layer. The ordering is explicit: insufficient data,
  then recovery risk, then food-data quality, then possible plan review.
- `reporting/` has no access to source export paths or credentials. The private profile includes
  observed daily fields carried by state estimates; the share-safe builder structurally removes
  daily series, dates, exact metrics, exercise/food names, and menus.
- `cases.py` and the packaged YAML catalog define executable, synthetic decision/failure cases.
- `pipeline.py` emits a typed run receipt with counts, configurations, constraints, and solver limits.

## Extension rule

A new wearable or app adapter is complete only when it:

1. maps units and dates into `DailyObservation` or `StrengthSet`;
2. attaches provider and record-type provenance;
3. documents whether duplicate values are summed, averaged, selected, or rejected;
4. adds fixture-based tests for missing values, duplicates, and unit conversion;
5. does not add a cloud dependency to the analytical core.

See [DEVICE_ADAPTERS.md](DEVICE_ADAPTERS.md) for the format contract.
