# Methods

CutSignal is a decision-support prototype. Its uncertainty intervals describe this model under its
assumptions; they are not clinical reference intervals and do not prove a biological mechanism.

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

The recent weekly rate is calculated from the beginning and end of a configurable window. Because
the stored public result contains marginal quantiles rather than full particle paths, the displayed
rate interval and plateau probability use a documented normal approximation to those marginals.
This approximation is a limitation, not a posterior identity.

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

Repeated sessions yield an exercise-specific percentage slope. The reported hierarchical slope is
a reliability-weighted combination of the raw exercise slope and median cross-exercise slope. The
reliability weight increases with session count and time span. This is empirical shrinkage, not a
fully generative hierarchical Bayesian model.

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

The objective is a user-visible weighted sum of robust cost, preparation time, calorie-target
deviation, preference penalty, and food-count penalty. Separate lowest-cost, fast-prep,
preference-first, and simple profiles are solved and dominated points removed. HiGHS status and the
relative MIP gap are retained. A time-limited feasible plan is never labelled globally optimal.

## 6. Reproducibility

Synthetic generators and particle filters use fixed seeds. HiGHS is run with one worker and a fixed
random seed. Floating-point and solver versions can still change the exact incumbent, so CI checks
feasibility, disclosed status/gap, invariant gates, and artifact hashes rather than requiring one
specific menu.
