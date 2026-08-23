# From-zero deep audit — 2026-08-24

This review supersedes the historical `STRICT_AUDIT.md`. Its rubric was defined from the project's
actual problem, data, methods, product surface, and evidence risks before assigning scores. The old
64/84 scores, release language, and completion statements were treated only as claims to recheck.

## A. Conclusion and positioning

**Positioning:** CutSignal is local-first, device-agnostic decision analytics for people who already
record weight, intake, strength training, and food constraints and want uncertainty-aware evidence
gates—not an automated diet prescription.

**One-line value:** Turn noisy personal fitness records into an auditable “continue, collect more
data, review recovery, validate food data, or consider human review” decision while exposing model
uncertainty, sensitivity, solver quality, and privacy boundaries.

The frozen checkout was a strong engineering alpha, but it still had two result-correctness/method
copy mismatches, an unbounded optional API response path, no executable alternative baseline, no
migration-shaped case, and fragmented onboarding/data documentation. The upgraded local checkout
fixes every identified P1 and passed the complete verifier. Publication evidence remains a separate
gate.

## B. Scope and inferred users

| Field | Audited value |
|---|---|
| Project path | repository root of the audited local checkout; the host-specific path is intentionally not versioned |
| Frozen baseline | `bd876648a151030340aae413f6566d8af2d9eeb7` |
| Baseline fingerprint | `114e1fc851e10b2ae60302f5678683b3afdfc9d9ec7a3209abcc320941b21900` |
| Audit date | 2026-08-24, Asia/Shanghai |
| Theme, inferred | personal fitness/weight/strength/food decision analytics; inferred because the user left the template field blank |
| Target users, inferred | technically comfortable self-trackers and analysts; not clinicians or autonomous-care operators |
| Main use, inferred | local exploration, method demonstration, portfolio evidence, and human-reviewed decisions |
| Capabilities expected, inferred | data normalization/provenance, statistical uncertainty, robust optimization, decision policy, testing, privacy, and evidence discipline |

All source, tests, configuration, registries, docs, workflows, generated screenshots, and historical
audits were read. The CLI, UI test runtime, cases, E2E path, distribution build, isolated install,
dependency audit, privacy scan, and synthetic workflow were executed rather than inferred from the
README.

## C. Frozen baseline

Before edits, `scripts/verify_project.py` passed all 16 then-versioned checks. Combined coverage was
91.4879%, statement coverage 93.3108%, and branch-only coverage 84.5659%. The isolated wheel install,
eight cases, Streamlit application test, and 112-day E2E run passed. Baseline evidence was copied to
ignored `artifacts/deep-audit-baseline/` before modification.

That green baseline did not settle domain correctness. Executable counterexamples showed:

- an explicit `1500 kJ` USDA energy value became `1500 kcal` because the old code guessed kJ only
  above 2000; the correct conversion is 358.508604 kcal;
- a declared “nutrition uncertainty +5 percentage points” stress used `(1-u)*(1-.05)`; for `u=.08`
  it produced .874 instead of the stated .87;
- an optional food endpoint could buffer an arbitrarily large response and accepted unsafe path
  identifiers;
- the recent-rate model had sensitivity scenarios but no executable known-truth alternative-method
  comparison.

## D. Independent benchmark review

The dated [benchmark matrix](BENCHMARKS.md) contains 4 direct, 5 adjacent, and 3 engineering/documentation
exemplars, each with an official link, access date, version/commit reference, maintenance signal,
mechanism to absorb, fit, and an explicit non-copy boundary.

Actual absorptions were limited to project-appropriate mechanisms: local-first/adaptor boundaries,
separate tutorial/how-to/explanation material, dual human/machine evidence, explicit solver status,
data-source caveats, a diagnostic command, and pinned workflow dependencies. Multi-user servers,
mobile collectors, cloud monitoring, incompatible licenses, and large-team governance promises were
not copied.

## E. Finding ledger and remediation

| ID | Priority | Finding | Implemented resolution | Verification state |
|---|---|---|---|---|
| DA-P1-001 | P1 | USDA magnitude-based energy-unit guessing could change nutrition constraints incorrectly | nutrient-ID priority; explicit kcal/kJ and g/mg/µg conversion; unsupported-unit rejection | full verifier passed |
| DA-P1-002 | P1 | stress math contradicted the “additional percentage points” label | shared additive uncertainty helper for macro and micronutrient stress | full verifier passed |
| DA-P1-003 | P1 | no executable alternative baseline on declared truth | fixed 12-run scenario grid vs same-window observed-weight OLS | full verifier passed |
| DA-P1-004 | P1 | optional food APIs had unsafe identifiers and no response-byte limit | numeric identifier allowlists, streamed 5 MiB cap, JSON-object validation | full verifier passed |
| DA-P1-005 | P1 | stale historical score could anchor this audit | historical review preserved and explicitly superseded; new machine-validated rubric | full verifier passed |
| DA-P1-006 | P1 | a valid cold Streamlit start could exceed the old 45-second AppTest bound | all AppTest phases now have explicit 120-second bounds within the 300-second outer verifier limit | full verifier passed |
| DA-P1-007 | P1 | the UI default could starve optional trade-off solves and surface a solver traceback | 8-second default main solve, at least 3 seconds per trade-off profile, and actionable expected-error rendering | full verifier passed |
| DA-P1-008 | P1 | an optional time-limited comparison profile could abort an independently validated primary analysis | reuse the primary balanced point; retain every skipped profile's label/type/reason in result, reports, UI, and E2E | full verifier passed |
| DA-P1-009 | P1 | named method families had no authoritative provenance/transfer registry | ten primary or authoritative sources map the borrowed mechanism and explicitly non-transferable validity | full verifier passed |
| DA-P1-010 | P1 | the publication scan misclassified a DOI identifier and did not reject host-specific home paths | URL-aware phone boundary, local-home-path rule, sanitized audit metadata, and regression tests | full verifier passed with zero findings |
| DA-P1-011 | P1 | the “public-tree” scan omitted workflows and some top-level publishable files | share the exact tracked/non-ignored checkout file set between fingerprinting and privacy audit | full verifier passed across the publishable checkout |
| DA-P1-012 | P1 | package, metadata, citation, and changelog versions could drift silently | add a five-surface consistency gate and isolated-install assertion | full verifier passed |
| DA-P1-013 | P1 | source records lacked explicit version/snapshot boundaries and machine validation | enrich all five records and validate roles, URLs, licenses, caveats, versions, and evidence paths | full verifier passed |
| DA-P1-014 | P1 | scoring consumed mutable generated files and the distribution directory could expose a stale wheel | reset verifier-owned outputs, require one rebuilt wheel, bind seven artifacts by SHA-256/size, and match the installed-wheel hash | complete implementation regression and 7/7 manifest gate passed; status gate then closed |
| DA-P2-001 | P2 | console evaluation output hid classification failures unless the JSON was opened | print accuracy/FP/FN and document 83.3% coverage plus three linked-method false negatives | full verifier passed |
| DA-P2-002 | P2 | documented root privacy command failed on generated local evidence after verification | separate broad-walk generated/cache exclusions from exact publishable-checkout enumeration | full verifier passed |

No known P0 was found, and no locally fixable P0/P1 remains open. DA-P1-014 was found during
post-verifier manual review. With the finding still marked pending, the next complete regression
passed every implementation check and the 7/7 artifact-manifest gate while only the audit-status
gate failed; the finding was closed afterward.

## F. Vertical method and case depth

- **Problem type:** exploratory/decision-support inference plus constraint optimization. It is not a
  causal estimator, diagnostic, or autonomous intervention.
- **Data:** `DATA_CARD.md` now records schema, units, duplicate/missing rules, lineage, source/license
  boundaries, bias/leakage checks, privacy, and fitness for use.
- **Baseline comparison:** `evaluation.py` fixes three true rates across clean, high-fluid,
  missing-data, and recent-outlier/intake-bias conditions. It reports per-scenario rate error, 95%
  interval coverage, plateau Brier score, threshold errors, and fixed-grid bootstrap intervals for
  both methods. It retains failure cases and states that grid bootstrap is not population inference.
- **Diet robustness:** explicit units prevent input-scale corruption, and additional nutrient stress
  is now additive as documented. Independent post-solve validation still remains the feasibility
  gate; a MIP gap remains an objective-quality disclosure. Optional trade-off solves cannot erase a
  valid primary plan, and their failures remain machine-visible rather than being treated as dominance.
- **Cases:** nine complementary fixtures now cover typical success, abstention, outlier/boundary
  behavior, recovery-first failure, optimization stress failure, diet eligibility, device overlap,
  and schema migration. The migration input is synthetic and vendor-neutral, not a native-vendor
  conformance claim.

## G. Horizontal engineering and product depth

- `cutsignal doctor` gives a no-data runtime/dependency diagnosis in human or JSON form.
- The verifier now runs the known-truth benchmark and records Git HEAD/dirty state; isolated-install
  evidence records the exact wheel SHA-256 and installed distribution inventory.
- Optional food requests validate identifiers, stream bodies, enforce a 5 MiB cap, and reject invalid
  JSON/non-object responses.
- HTML reports have a skip link, keyboard-focus treatment, chart title/description, labeled
  horizontally scrollable tables, mobile layout, and print styling. Streamlit Plotly figures have
  explicit titles; sensitivity bars include numeric labels and diet bounds include annotations.
- GitHub Actions are pinned to full SHAs while Dependabot retains update coverage.
- Documentation is split into README navigation, first-analysis tutorial, troubleshooting, data card,
  methods, ten-reference provenance/transfer map, validation, casebook, source registry, benchmark
  review, support, and privacy/security.

## H. Verification status

The complete modified-checkout implementation regression passed 21 of 22 executable checks plus
privacy, required-documentation, and the 7/7 artifact-manifest gate on macOS/Python 3.12.13. The
sole failure was the deliberately pending DA-P1-014 audit-status gate, which was closed only after
the run. It recorded 53 passing tests, 91.3095% combined
coverage, 93.2534% statement coverage, and 83.8150% branch-only coverage; a wheel and source
distribution build; an isolated wheel install; `pip check`; OSV dependency audit with no known
vulnerabilities found; 9/9 cases; Streamlit AppTest; and the 112-day E2E workflow. The rebuilt wheel
hash matched the isolated-install record. The exact
publishable checkout scan covered 104 files and returned zero privacy findings.

The 12-run synthetic grid produced linked-particle MAE 0.0557 kg/week, 83.3% interval coverage,
Brier 0.0778, 75.0% plateau classification accuracy, and three false negatives; OLS produced MAE
0.3324 kg/week, 66.7% coverage, Brier 0.2333, 66.7% accuracy, and four false negatives. These
aggregates describe only the fixed internal scenario grid and are not external calibration. The
screenshots were regenerated and visually inspected locally. Remote SHA and terminal CI remain
separate publication evidence and are not asserted here.

## I. Independent score

| Dimension | Max | Frozen baseline | Upgraded local | Main evidence for change |
|---|---:|---:|---:|---|
| Positioning and boundaries | 8 | 7 | 8 | benchmark-linked scope and clearer user/decision boundary |
| Data and provenance | 11 | 7 | 9 | data card; explicit nutrient IDs/units; response controls |
| Method depth | 15 | 11 | 13 | corrected stress semantics and known-truth comparator |
| Evaluation and cases | 10 | 6 | 9 | 12 runs, OLS baseline, ninth migration case, retained failures |
| Architecture/API/CLI | 9 | 9 | 9 | already strong; doctor improves UX but not architecture score |
| Testing/reliability | 9 | 8 | 9 | regression, malformed/oversize, evaluation, and accessibility tests |
| Reproducibility/release | 9 | 6 | 7 | richer install evidence and pinned Actions; remote still unverified |
| UX/demo/accessibility | 7 | 5 | 7 | doctor, tutorial, report/table/chart accessibility |
| Documentation/onboarding | 7 | 6 | 7 | data card, benchmarks, tutorial, troubleshooting, support |
| Privacy/security | 5 | 5 | 5 | strong baseline retained; no external assessment claimed |
| Governance/maintenance | 4 | 3 | 4 | support boundary and pinned/dependabot-managed workflows |
| External validity/use | 6 | 0 | 0 | no qualifying external evidence |
| **Total** | **100** | **73** | **87/100 local** | **+14; complete local verifier passed** |

The registry `data/registry/deep_audit.yml` validates the arithmetic, evidence paths, benchmark mix,
caps, and absence of open P0/P1. If the exact commit is pushed and required GitHub Actions reach a
successful terminal state, reproducibility/release becomes 8/9 and the score becomes 88/100. A tag
or README edit alone cannot raise external-validity points.

## J. Claim boundaries

**Internally reproducible after the complete verifier passes:** implemented algorithms, normalized
schemas, nine synthetic cases, fixed evaluation grid, report profiles, packaging/install path, and
machine gates for the exact checkout.

**External evidence currently present:** official third-party project/source documentation used for
benchmark and data-source review only. It does not validate CutSignal's methods or UX.

**Cannot be stated:** clinical or causal validity; individual calorie needs; subgroup fairness;
independent reproduction/review; native support for every named device; real users, adoption,
deployment, outcomes, impact, or stars.

## K. Remaining issues

### Current locally fixable

- If publication is authorized and authenticated access exists, push the exact commit and verify
  remote SHA and terminal Actions before claiming public CI.

### P2/P3 with insufficient current cost/benefit

- Native vendor adapters without vendor-owned conformance fixtures and stable export contracts.
- A separately hosted documentation site before a public release/maintenance plan exists.
- Exhaustive multi-objective enumeration beyond the declared sampled non-dominated profiles.

### Requires external conditions

- governed longitudinal cohort and preregistered calibration design;
- controlled strength protocol and qualified domain review;
- region-specific verified food labels/prices/availability and real adherence;
- independent usability/accessibility participants and security review;
- real users, longitudinal observation, external reproduction, adoption, deployment, and impact.
