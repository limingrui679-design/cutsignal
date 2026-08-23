# Executable casebook

CutSignal ships eight deterministic synthetic cases. Each case names one decision question, the
capabilities exercised, executable assertions, actual observations, and a limitation. These cases
test software behavior; they are not real users, population samples, clinical validation, external
review, adoption, or impact.

```bash
cutsignal cases list
cutsignal cases run missing-intake-abstain
cutsignal cases verify --output artifacts/cases.json
```

| Case | Decision or failure mode | Main capability evidence |
|---|---|---|
| `plateau-sensitivity-gate` | A plateau-looking posterior changes under plausible assumptions | linked particle rate, sensitivity, abstention |
| `missing-intake-abstain` | Intake coverage is below the interpretation gate | missingness and data-quality precedence |
| `water-spike-resilience` | One injected scale excursion should not reverse the fixture action | Student-t likelihood and robust decision comparison |
| `strength-fatigue-gate` | Decline, volume, and RPE agree | weighted trend, empirical Bayes, recovery-first gate |
| `stable-strength-cut` | Multi-exercise performance remains broadly retained | e1RM, volume, intensity, RPE, frequency, relative strength |
| `budget-shock` | Modeled bounds pass but stronger price/nutrition shocks can fail | robust MILP, independent validation, stress tests |
| `vegetarian-allergen-plan` | Tags and a declared soy allergen interact with all plan constraints | filtering, feasibility, variety, post-solve audit |
| `device-overlap-reconciliation` | Phone and watch step streams overlap | streaming import, max-source reconciliation, quality flag |

The catalog is versioned in `src/cutsignal/resources/cases.yml`; dispatch lives in
`src/cutsignal/cases.py`. `tests/test_cases.py` requires every catalog entry to have an executable
implementation and makes failures visible rather than silently dropping a case.
Particle-based cases use a fixed, machine-visible 500-particle configuration so changing a UI demo
slider cannot silently redefine a case. Solver time limits remain recorded with optimization cases.
The fixture inputs and assertions are deterministic; a time-limited MILP may select a different
feasible incumbent, so exact objective values, gaps, and report hashes are not reproducibility gates.

## How to add a case

1. Use wholly synthetic values or a public source whose license and privacy permit redistribution.
2. State the decision question before the expected result.
3. Add assertions that can fail and retain the observed values in machine-readable output.
4. State what the fixture does not establish.
5. Add the catalog entry, executable dispatch, and automated test in the same change.
