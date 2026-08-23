# Methods

CutSignal is a decision-support prototype. Its uncertainty intervals describe this model under its
assumptions; they are not clinical reference intervals and do not prove a biological mechanism.
Algorithm provenance and transfer limits are mapped in [Method references](REFERENCES.md) and the
machine-readable [`method_references.yml`](../data/registry/method_references.yml). A citation
supports the named method family or upstream contract; it does not externally validate CutSignal's
adaptation, parameter values, intervals, or decisions.

## 1. Latent trend weight and TDEE

For particle `i` and day `t`:

```text
TDEE(i,t)   = clip(TDEE(i,t-1) + Normal(0, sigma_tdee))
trend(i,t)  = trend(i,t-1) + (intake(t) - TDEE(i,t)) / rho(i) + process noise
fluid(i,t)  = phi * fluid(i,t-1) + Normal(0, sigma_fluid)
weight(t)   ~ StudentT(df, trend(i,t) + fluid(i,t), sigma_measurement)
```

`rho`, the effective energy density, is sampled from a truncated distribution. It is intentionally
not hard-coded as an exact conversion between energy and tissue. Missing intake uses a wider random
walk rather than imputing a precise meal total. A bootstrap particle filter updates normalized
weights and uses systematic resampling below the effective-sample-size threshold.

The recent weekly rate is calculated from linked particle start/end trajectories over a configurable
window. Particle histories are re-indexed whenever systematic resampling occurs, so the rate
posterior preserves the temporal covariance represented by those lineages. Its 2.5/50/97.5%
quantiles and plateau probability are computed directly from weighted rate draws; they are not
reconstructed from independent daily marginal intervals. This preserves covariance inside the
stored window, but it does not establish external calibration.

## 2. Plateau evidence gate

The default plateau band is ±0.10 kg/week. A plan-review signal is allowed only if all of the
following pass:

- minimum observation duration;
- weight coverage;
- intake-log coverage;
- maximum TDEE interval width;
- stable decision under recorded intake, +10% intake, +20% intake, higher fluid variance, and
  locally detected weight-outlier exclusion.

The output says `consider_review`, not “reduce calories.” The next step is to review adherence,
measurement conditions, recovery, medication, and professional context.

## 3. Change points

Equally spaced series are segmented by dynamic programming. Each segment is a least-squares linear
trend. The number of segments minimizes Bayesian information criterion (BIC), with three parameters
per added segment/boundary. Minimum segment length blocks one-day anomalies from becoming regimes.

## 4. Strength retention

For each eligible working set, LeanGuard computes Epley, Brzycki, and Lombardi e1RM estimates and
uses their median. When RPE is present, up to four estimated repetitions in reserve are added to
effective repetitions. Formula spread, high repetitions, and absent RPE influence uncertainty or
quality flags.

Repeated sessions yield an exercise-specific percentage slope. Regression weights are the inverse
of the heuristic e1RM-formula variance, with residual overdispersion retained. A normal
random-effects prior is estimated across eligible exercises using a DerSimonian-Laird between-
exercise variance, followed by empirical Bayes posterior shrinkage. With only one eligible
exercise, no cross-exercise shrinkage is claimed. This is empirical Bayes, not a fully generative
hierarchical Bayesian model, and the formula-derived measurement variance is not externally
calibrated.

The analysis also reports weekly session frequency, working sets, volume, mean percentage of e1RM,
RPE, and body weight. Baseline/latest changes use short multi-session windows rather than a single
session when enough observations exist.

A fatigue flag requires a recent e1RM drop plus either an RPE rise or volume drop. A
`review_recovery` decision requires both fatigue and high probability that the slope crosses the
configured material-decline threshold. Causality is never assigned to the energy deficit.

## 5. Robust weekly food optimization

Integer `x[d,f]` selects servings. Binary `y[d,f]` indicates use on a day; binary `z[f]` indicates
use anywhere in the week. Constraints include daily energy, protein, fiber, optional sodium and
micronutrients, cost, preparation time, repetition, variety, allergies, and dietary tags.

Robust lower coefficients are `nominal × (1 - uncertainty)`. Robust upper coefficients and prices
are `nominal × (1 + uncertainty)`. This is a transparent box-uncertainty model, not a probabilistic
guarantee. After solving, the chosen plan is stress-tested under an additional 5/10 percentage
points of nutrient uncertainty and 10/20% price shocks without re-optimization.

An independent post-solve validator reconstructs all hard constraints from the selected menu and
the original food records. It checks daily calories, protein, fiber, optional sodium and
micronutrients, robust price, preparation time, per-day serving limits, weekly repetition, variety,
allergens, and dietary tags without reading solver variables. A solver incumbent that fails this
validator is rejected.

The objective is a user-visible weighted sum of robust cost, preparation time, calorie-target
deviation, preference penalty, and food-count penalty. Separate lowest-cost, fast-prep,
preference-first, and simple profiles are solved and dominated points removed. HiGHS status and the
relative MIP gap are retained. A time-limited feasible plan is never labelled globally optimal.
The retained profiles are a sampled non-dominated trade-off set, not an exhaustive Pareto frontier;
weighted-sum sampling can miss discrete non-convex trade-offs.
The primary balanced plan is reused as the balanced comparison point. If a time-limited optional
profile produces no incumbent, the core analysis continues with the independently validated primary
plan and successful points while retaining the failed profile label, error type, and reason. A
missing optional point is never interpreted as dominance.

## 6. Reproducibility

Synthetic generators and particle filters use fixed seeds. HiGHS is run with one worker and a fixed
random seed. Statistical sensitivity scenarios use the same particle-filter seed (common random
numbers) so intended parameter/data changes are not deliberately confounded with different random
streams. Floating-point and solver versions can still change the exact incumbent, so CI checks
feasibility, disclosed status/gap, invariant gates, and artifact hashes rather than requiring one
specific menu.

Nine executable deterministic synthetic cases test typical, abstention, boundary, stress-failure,
and schema-migration behaviors. They are software
fixtures with stated expectations, not population samples or external-validation evidence.

A separate fixed known-truth scenario grid compares the recent-rate posterior with an
observed-weight OLS baseline. It reports error, interval coverage, Brier score, and classification
failures, including high-fluid, missing-data, recent-outlier, and intake-bias stress. Because the
generator belongs to this project, those metrics are internal method checks—not external
calibration, subgroup validity, or clinical evidence.

## 7. Method provenance and non-transfer boundary

The method registry links the particle-filter family, dynamic energy-balance context, BIC,
repetition-to-1RM/RIR evidence, random-effects variance estimator, robust-optimization framework,
diet linear programming, and USDA field contract to primary or authoritative sources. It also
records how each source differs from this implementation. In particular:

- the Hall/NIDDK physiological model motivates dynamic thinking but is not implemented here;
- DerSimonian-Laird is adapted from study-level meta-analysis to exercise slopes, whose
  exchangeability is unverified;
- Bertsimas-Sim is a conceptual robustness reference, while CutSignal uses a more conservative
  simultaneous box set rather than a budgeted uncertainty set;
- e1RM and RIR papers motivate uncertainty and effort fields but do not calibrate longitudinal
  estimates for an arbitrary user.

These distinctions are executable documentation requirements, not optional caveats. Run
`python scripts/verify_method_references.py` to validate registry completeness and its documentation
mapping. URL reachability is intentionally not a build gate because CI must not turn third-party
availability into evidence about local method correctness.
