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
| One integrated synthetic demo could not demonstrate distinct decisions and failure modes | Fixed | Eight executable deterministic cases with explicit assertions and limitations |
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

## P2 / roadmap

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
