# Project audit ledger

This ledger records the stricter second-pass audit used after the initial prototype rubric. A fixed
item means the repository now has an implementation and a machine gate; it does not mean external
validation or adoption.

## P0

| Finding | Status | Resolution and gate |
|---|---|---|
| Report copy said raw records were omitted while serialized daily states still contained observed weight and intake | Fixed | Explicit `private` and `share-safe` schemas; tests forbid dates, daily states, exact observations, exercise names, and food names in the minimized profile |

## P1

| Finding | Status | Resolution and gate |
|---|---|---|
| Plateau rate used an independence/normal approximation from two marginal intervals | Fixed | Direct weighted rate posterior from linked particle histories; fixed-seed tests |
| Strength slope ignored formula uncertainty and “hierarchical” wording exceeded the heuristic | Fixed | Uncertainty-weighted regression and explicitly named empirical Bayes random-effects shrinkage |
| Volume, intensity, RPE, and frequency were not first-class outputs | Fixed | Session and weekly summaries plus dashboard views |
| Diet solver output lacked a complete independent constraint audit | Fixed | Post-solve reconstruction of nutrition, cost, time, serving, variety, tag, and allergen constraints |
| Five objective profiles were described too broadly as a Pareto frontier | Fixed | Described and labeled as a sampled non-dominated trade-off set, not an exhaustive Pareto frontier |
| One integrated synthetic demo could not demonstrate distinct decisions and failure modes | Fixed | Nine executable deterministic cases with explicit assertions and limitations |
| Detailed and shareable report surfaces were not structurally distinct | Fixed | Separate payload builders, HTML labels, CLI option, demo artifacts, and tests |
| Input readers had no uniform size/row/line limits | Fixed | Shared file, row, line, and UI-upload limits with tests |
| Wheel build did not prove isolated installation or packaged case resources | Fixed | Temporary-venv wheel installation, public-API import, packaged case execution, and `pip check` |
| Public capability statements were not bound to a machine-readable evidence registry | Fixed | `data/registry/claims.yml` plus registry validator |
| Runtime method parameters relied on unenforced type annotations | Fixed | Explicit recent-window and plateau-band bounds with rejection tests |
| Expected CLI/UI input failures surfaced implementation tracebacks | Fixed | Stable exit code and concise input errors for the CLI; user-facing errors in the upload UI |
| Setup metadata asserted a public remote that has not been verified | Fixed | Removed clone, homepage, issue, and citation URLs until publication is independently confirmed |
| Verification fingerprint included ignored virtual-environment state | Fixed | Fingerprint now covers Git-tracked and non-ignored untracked files only |
| Independent diet validation accepted out-of-range days and ambiguous food identifiers | Fixed | Explicit invalid-day, nonpositive-serving, and duplicate-ID checks with mutation tests |
| JSONL export materialized every record before writing | Fixed | Same-directory streamed temporary writes with `fsync`, atomic replace, and a failure-preservation test |
| MILP symmetry coefficients grew exponentially with catalog width and optimizer inputs were unbounded | Fixed | Removed nonessential exponential ordering constraints; retained deterministic objective perturbation plus 500-food and one-hour API limits |
| Unknown report-profile strings silently selected the minimized branch | Fixed | Runtime allowlist validation and rejection test |
| README screenshots and local documentation links had no machine gate | Fixed | Repository-local link and image validator included in the full verifier |
| Statistical sensitivity scenarios changed both assumptions and Monte Carlo seeds | Fixed | Common random numbers across scenarios, exposed scenario seeds, and a regression assertion |
| Optional cohort download could leave a partial file and had no byte cap | Fixed | 2 GiB streaming cap, atomic replacement, checksum manifest, and failure-preservation test |
| Security policy pointed to an unverified external reporting feature | Fixed | Unpublished support state is explicit; enabling a confidential channel remains a release condition |
| Constraint JSON bypassed the shared local/UI input-size controls | Fixed | 1 MiB constraint limit in both CLI and upload UI with a rejection test |
| Renamed text files above the privacy scanner's byte limit could pass without content review | Fixed | Prefix scan plus a failing manual-review finding for every incompletely scanned text file |
| Casebook assertions changed with an unrelated UI particle-count slider | Fixed | Case-owned 500-particle configuration, recorded in evidence and decoupled from demo controls |
| Privacy verification scanned ignored bytecode caches and produced false positives | Fixed | Tool/cache directories and compiled Python artifacts are excluded from publication scans |
| Documentation called the combined coverage percentage “branch coverage” | Fixed | Separate combined ≥90% and branch-only ≥80% gates and evidence labels |
| Citation metadata supplied a release date despite no verified published release | Fixed | Kept software/version citation fields but removed the unsupported release date |
| Semantic documentation gate treated ordinary Markdown line wraps as missing content | Fixed | Case-folded whitespace normalization before phrase matching |
| Integrated tests treated a ≤20% MIP objective gap as if it proved or disproved hard-constraint feasibility | Fixed | Feasibility is now gated by independent reconstruction; solver status and finite nonnegative gap remain mandatory and visible, without an arbitrary pass threshold |
| A seven-day high-constraint vegetarian fixture could fail to find any incumbent under a two-second cross-machine gate | Fixed | Three-day case still exercises nutrition, budget, time, variety, vegetarian tags, soy exclusion, and independent validation; repeated case verification required |
| Case verification aborted at the first expected domain exception | Fixed | Per-case domain failures are retained as structured failed evidence and covered by a regression test |
| Long decimal metrics could be misclassified as uninterrupted phone numbers | Fixed | Hex/decimal boundary exclusions and a metrics/commit regression test |
| Fixed synthetic inputs were described in a way that could imply byte-identical time-limited solver output | Fixed | Documentation now separates deterministic fixture inputs from variable feasible incumbents and report hashes |
| Default dependency-audit transport failed on a 15-second PyPI TLS/read timeout | Fixed | Local and CI checks use pip-audit's supported OSV service with a 60-second socket timeout and still fail closed on service errors |
| Fresh-wheel verification was silent and could hit a 420-second aggregate timeout under a slow runtime | Fixed | Binary-only dependency install, per-phase timings, captured timeout output, and bounded 600-second command / 900-second aggregate limits |
| USDA energy could be misread when an explicit kJ value was below the old magnitude threshold | Fixed | Nutrient-ID priority, explicit unit conversion, unsupported-unit rejection, and regression tests |
| A diet stress label said “plus 5 points” while coefficients compounded 5% after modeled uncertainty | Fixed | Additive percentage-point stress helper shared by macro and micronutrient checks, with an exact-formula test |
| Optional food APIs buffered unbounded bodies and accepted unsafe path identifiers | Fixed | Numeric identifier allowlists, streamed 5 MiB cap, invalid JSON/object rejection, and boundary tests |
| The core trend model had no executable comparator on a declared truth grid | Fixed within internal evidence scope | Fixed 12-run generator, recent-weight OLS baseline, scenario-level error/coverage/Brier output, and explicit external-validity boundary |
| The casebook had no migration-shaped input crossing the generic schema boundary | Fixed within synthetic scope | Ninth case checks aliases, lb-to-kg conversion, duplicate aggregation, and provenance; native vendor conformance remains unestablished |
| Streamlit AppTest could reject a valid cold start at its old 45-second phase limit | Fixed | Explicit 120-second phase bounds remain inside the verifier's 300-second outer timeout; slow starts remain visible rather than unbounded |
| The UI default could underfund optional trade-off solves and display a solver traceback | Fixed | Safer default/profile time budgets plus an actionable expected-domain-error boundary; UI smoke still requires a complete result |
| A failed optional trade-off profile aborted a valid primary pipeline run | Fixed | Primary balanced point reuse plus structured failure retention; forced-failure regression and E2E output prove partial comparison does not hide missing points |
| Named method families had no single authoritative provenance map or transfer boundary | Fixed | Ten primary/authoritative references record the mechanism used and what the source cannot establish; the registry-to-document map is machine validated |
| DOI article identifiers could be misclassified as phone numbers, while host-specific home paths were not rejected | Fixed | URL-path-aware phone matching, explicit local-home-path detection, sanitized audit metadata, and adversarial regression tests |
| The verifier's “public-tree” privacy scan enumerated selected paths instead of the complete publishable checkout | Fixed | The scan and checkout fingerprint now share every Git-tracked plus non-ignored untracked file, including workflows and top-level governance files |
| Package, build metadata, citation metadata, and changelog versions could drift without failing verification | Fixed | A version-consistency gate checks all four plus the installed distribution; isolated-wheel smoke also compares runtime and distribution versions |
| The source registry omitted explicit version/snapshot boundaries and had no machine validator | Fixed | Five sources now declare access date, version/snapshot semantics, bundling, license/terms, caveats, and local evidence paths; the full verifier checks the schema |

## P2 / roadmap

- Fixed in the strict-review pass: the local verifier and scheduled/push security workflow now run
  `pip-audit`, instead of relying only on `pip check`, CodeQL, and PR-only dependency review.
- Fixed in the strict-review pass: the public-tree scanner now detects common credential/private-key
  signatures and sensitive filenames, with adversarial tests. This is a heuristic guardrail, not a
  proof that secrets are absent.
- Fixed in the strict-review pass: `docs/STRICT_AUDIT.md` separates the repository's machine
  engineering score from a portfolio-wide score that deducts for synthetic-only cases, missing
  external validation, and publication state.
- Fixed in the deep-review pass: the synthetic benchmark command now prints classification accuracy,
  false positives, and false negatives; documentation retains the observed 83.3% fixed-grid interval
  coverage and three missed plateau classifications instead of presenting only relative wins.
- Fixed in the deep-review pass: a broad `privacy-audit .` walk skips declared generated/tool
  evidence that contains local paths, while the verifier still scans every publishable checkout file.

- Calibrate the trend/plateau decision on preregistered simulations and appropriately governed
  external cohorts.
- Validate e1RM changes against protocol-controlled maximal or submaximal sessions.
- Evaluate regional food availability, prices, label error, cooking yield, and adherence.
- Add more device adapters only with contract fixtures, reconciliation rules, and license review.
- Publish signed releases and hosted documentation after a public remote and maintainer decisions
  exist.

## External conditions

The repository alone cannot establish clinical validity, fairness across populations and devices,
prospective behavior change, user satisfaction, institutional adoption, external review, stars, or
real-world impact. Those require governed data, ethics/privacy review where applicable, real users,
external maintainers/reviewers, and time. The project makes none of those claims.
