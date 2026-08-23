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
