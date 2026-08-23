# Method references and transfer boundaries

Accessed **2026-08-24**. This is a provenance map, not a literature-based validation claim.
Each source identifies an algorithm family, upstream contract, or important limitation. CutSignal's
implementation and parameters remain testable repository artifacts; citations do not establish
clinical validity, external calibration, individual benefit, or correct transfer to a new
population. The machine-readable source is
[`data/registry/method_references.yml`](../data/registry/method_references.yml).

## Latent trend and model selection

### `gordon-bootstrap-filter-1993`

[Gordon, Salmond, and Smith (1993)](https://doi.org/10.1049/ip-f-2.1993.0015)
introduced the bootstrap-filter family used here for sequential weighted particles and resampling.
CutSignal supplies its own state equations, priors, parameter bounds, heavy-tailed observation
model, and evidence gate. The paper therefore does not validate CutSignal's intervals or health
decisions.

### `hall-energy-balance-2011`

[Hall et al. (2011)](https://pubmed.ncbi.nlm.nih.gov/21872751/) model body-weight response to energy
imbalance as a dynamic process. CutSignal borrows only that high-level discipline: it avoids an exact
static energy-to-tissue conversion and exposes an uncertain effective energy density. It does not
implement the Hall physiological compartments and cannot prescribe intake or predict an
individual's long-run response.

### `niddk-body-weight-planner-model`

The [NIDDK model page](https://www.niddk.nih.gov/research-funding/at-niddk/labs-branches/laboratory-biological-modeling/integrative-physiology-section/research/body-weight-planner)
links the equations and simulator behind its Body Weight Planner. It is included to make the
non-equivalence explicit: CutSignal's smaller latent-state prototype is not a reimplementation or
clinical substitute.

### `schwarz-bic-1978`

[Schwarz (1978)](https://doi.org/10.1214/aos/1176344136) supplies the model-dimension penalty behind
BIC. CutSignal applies a declared three-parameter penalty to candidate piecewise-linear segments;
the selected boundary is a descriptive regime marker, not evidence of mechanism or causation.

## Strength estimation and shrinkage

### `lesuer-e1rm-equations-1997`

[LeSuer et al. (1997)](https://doi.org/10.1519/1533-4287%281997%29011%3C0211%3ATAOPEF%3E2.3.CO%3B2)
compared repetition-based 1RM equations across bench press, squat, and deadlift and found
exercise-dependent error. This motivates retaining formula disagreement and high-repetition flags;
it does not calibrate CutSignal's median-of-three estimate or its heuristic uncertainty.

### `zourdos-rir-rpe-2016`

[Zourdos et al. (2016)](https://pubmed.ncbi.nlm.nih.gov/26049792/) studied a resistance-training RPE
scale tied to repetitions in reserve. CutSignal uses this as an optional effort adjustment and caps
the adjustment at four repetitions. Subjective RPE, exercise, training age, technique, and whether
the set was taken near failure remain transfer risks.

### `dersimonian-laird-1986`

[DerSimonian and Laird (1986)](https://pubmed.ncbi.nlm.nih.gov/3802833/) introduced the
method-of-moments random-effects variance estimator. CutSignal adapts it to slopes from eligible
exercises for transparent empirical-Bayes shrinkage. Exercises are not clinical studies; their
exchangeability and the resulting intervals have not been externally established.

## Food optimization and normalization

### `bertsimas-sim-2004`

[Bertsimas and Sim (2004)](https://doi.org/10.1287/opre.1030.0065) formalize a tunable trade-off
between nominal performance and conservatism. CutSignal intentionally uses a simpler simultaneous
box-uncertainty set. It does not implement their budgeted uncertainty set and makes no probabilistic
constraint guarantee.

### `ferguson-diet-lp-2004`

[Ferguson et al. (2004)](https://pubmed.ncbi.nlm.nih.gov/15051853/) demonstrate an explicit
nutrient- and palatability-constrained diet linear program and worst-case robustness check for a
specific study setting. CutSignal borrows the constraint-first product pattern, not that study's
targets, foods, population assumptions, or evidence of acceptability and benefit.

### `usda-fdc-api-2026`

The [USDA FoodData Central API specification](https://fdc.nal.usda.gov/api-spec/fdc_api.html)
defines the identifiers, values, and unit fields consumed by the optional adapter. The adapter
normalizes explicit units and preserves source provenance, but an upstream record still cannot
establish local serving size, price, availability, or dietary suitability.

## What these references establish

- a traceable reason for each algorithm family or upstream field contract;
- the differences between the cited method and CutSignal's implementation;
- transfer assumptions that must remain visible in interpretation and future validation.

## What they do not establish

- external calibration, clinical validity, causal identification, subgroup fairness, or safety;
- a correct calorie target, diagnosis, treatment, food recommendation, or training prescription;
- independent reproduction, expert review, real users, adoption, deployment, or impact.
