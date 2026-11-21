# Data sources and licenses

CutSignal ships no third-party dataset and no personal export. The adapters below retrieve or parse
data only when the user explicitly runs them.
The dated machine-readable registry records each source's rolling/fixed version boundary, bundling
state, license/terms, caveat, and implementation evidence. Run `python scripts/verify_sources.py` to
validate it; URL reachability is not treated as evidence of data correctness.

## User-controlled health and training exports

- Apple Health XML/ZIP is user-provided. Apple documents health-data sharing and export in its
  [iPhone User Guide](https://support.apple.com/guide/iphone/share-your-health-and-fitness-data-iph5ede58c3d/ios).
  Apple does not endorse this project.
- Hevy and Strong CSVs are user-provided. Their marks and export formats remain their owners'.
- Garmin, Fitbit, and COROS currently use the generic schema boundary; this repository makes no
  claim of native vendor API support.

## Food records

- [USDA FoodData Central API](https://fdc.nal.usda.gov/api-guide/) data are published by the United
  States Department of Agriculture. FoodData Central data are public domain/CC0. API keys stay in
  environment variables; default rate limits and terms may change, so consult the official guide.
  CutSignal selects declared nutrient IDs, reads `unitName`, converts kJ to kcal and g/mg/µg mass
  units explicitly, and rejects unsupported units instead of guessing from magnitude.
- [Open Food Facts API](https://openfoodfacts.github.io/openfoodfacts-server/api/) records are
  crowdsourced. Database reuse is governed by ODbL and associated content licenses described on the
  [Open Food Facts data page](https://world.openfoodfacts.org/data). Completeness and accuracy are
  not guaranteed; CutSignal propagates a lower confidence score.

The user supplies price, serving, preference, allergen, and preparation assumptions. Neither source
is evidence that a local product is available or safe for a particular person.
Responses are streamed with a 5 MiB limit, and path identifiers are restricted to expected numeric
forms. These controls do not establish upstream availability or correctness.

## Optional strength cohort

[OpenPowerlifting bulk CSV](https://openpowerlifting.gitlab.io/opl-csv/) is optional and not bundled.
The provider dedicates meet data to the public domain. The adapter stores URL, resolved URL,
retrieval time, available ETag/Last-Modified values, SHA-256, byte count, and license note beside a
downloaded snapshot. Downloads are streamed through a same-directory
temporary file, capped at 2 GiB, and atomically replace the destination only after completion.

Competition results are a performance benchmark only. Meet weigh-ins can involve acute weight cuts
and must not be interpreted as longitudinal body-fat outcomes. `Name|Sex` is not a verified unique
person identifier, so CutSignal performs row-level cohort summaries rather than athlete linkage.

## Validation datasets not redistributed

Future external validation can use controlled wearable-energy/heart-rate studies and population
surveys, but licensing, participant-level privacy, device placement, and ground-truth definitions
must be reviewed separately. A public filename or download button is not sufficient permission to
redistribute participant data.

### Real weigh-in forecast check

Furberg, Brinton, Keating and colleagues published the Fitabase MTurk exports on [Zenodo](https://zenodo.org/records/53894) under CC BY 4.0. The April 12–May 12 archive has MD5 `7afbecdce29814e1be2e9a7c94f8f165`. Extract its `weightLogInfo_merged.csv` locally and run `cutsignal benchmark-weight weightLogInfo_merged.csv`. The command combines same-day entries by median and starts a new history after a gap above seven days. Starting with the fourth qualifying date, it scores the scale-weight prediction made before that day's measurement against the last observed weight.

Of 67 records from eight people, 50 weigh-ins from three people qualified. Pooled MAE was 0.328 kg for the particle prediction and 0.350 kg for persistence. Giving each person equal weight instead favoured persistence by 0.056 kg. The target is the next observed scale reading. The study supplies no independent fat-mass trajectory or energy-expenditure truth. Only aggregates are reported.

### Choosing a forecaster before the next weigh-in

The benchmark gives the particle forecast and the last observed weight equal starting odds. Before each new weigh-in it mixes them in proportion to their past accuracy for that person. The odds multiply by `exp(reference absolute error − particle absolute error)` after the measurement, with errors in kilograms and a fixed scale of 1 kg. A gap over seven days restarts the comparison. A separate hindsight calculation finds the lowest attainable absolute error for choosing one method throughout a segment or switching once. These two retrospective values quantify the room available to a method selector.

On the April–May Fitabase file (SHA-256 `50b40176f926562e1a522dcb4e75f30c4f04441a7d5b8e570f704b1fbab2b738`), 50 eligible predictions came from three participants. MAE was 0.3500 kg for persistence, 0.3283 for the particle filter, 0.3328 for a constant half mix, and 0.3321 for the online mix. The hindsight fixed and one-switch selectors achieved 0.3188 and 0.3102 kg. Two people improved with online mixing; weighting the three people equally yielded a **0.0232 kg loss** relative to persistence. Run `cutsignal benchmark-weight weightLogInfo_merged.csv` to reproduce the aggregate comparison. The evaluated outcome is the next scale reading.
