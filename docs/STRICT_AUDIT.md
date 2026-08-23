# Independent strict audit

This review applies an independent technical, domain-method, product, evidence, and portfolio rubric.
It is deliberately separate from the repository's all-or-nothing machine engineering score.

## A. Final conclusion

- Version reviewed: `0.2.0` alpha.
- Baseline: `0c0c664`, **64/100** under this strict rubric.
- Current prepublication candidate: **84/100 provisional**, contingent on the full checkout-bound
  verifier.
- Candidate improvement: **+20 points**; it becomes verified only after that verifier passes.
- Goal status: targeted method, privacy, UI, case, and E2E checks pass; the full verifier, public
  verification, and external-validity goals are not yet complete.
- Confidence: high for E1/E2 local claims; no confidence is assigned to absent external outcomes.
- Positioning: local-first, device-independent decision analytics that connects noisy fat-loss trends,
  strength-retention evidence, and robust food-plan feasibility without claiming diagnosis or outcomes.

The separate machine rubric may report 100/100 when every versioned repository gate passes. The
strict score remains lower because synthetic cases, publication state, usability evidence, external
validation, real users, adoption, and impact are separate dimensions.

## B. Project identity and review scope

| Field | Value |
|---|---|
| Path | `/Users/li/Documents/Codex/2026-08-20/w-x/outputs/cutsignal` |
| Branch | `main` |
| Baseline | `0c0c664` |
| Reviewed base HEAD | `54b5241c2b4e7b15448aec6766ce61f21af451f4` plus this strict-review change set |
| Remote | not configured in the prepublication state |
| Tags | none |
| Audit date | 2026-08-23–24, Asia/Shanghai |
| Runtime | macOS; Python 3.12.13 in the project virtual environment |
| Included | source, tests, methods, cases, CLI/UI, reports, privacy, build, docs, claims, baseline worktree, packaging |
| Not established | public CI result, signed release, controlled health/strength validation, real users, independent review, adoption, impact |

The baseline was checked in a detached temporary worktree. It passed Ruff, formatting, strict Mypy,
and package build, but produced 31 passing tests plus one failed optimizer test. Its full verifier
failed both `pytest_coverage` and E2E. Combined coverage was 91.9341%, statement coverage 93.6831%,
and branch-only coverage 85.4%; coverage did not offset the behavioral failures.

## C. Evidence inventory

| ID | Capability or conclusion | Level | Evidence | Verified | Limitation |
|---|---|---|---|---|---|
| C01 | Three connected analytical engines | E1 | `src/cutsignal/pipeline.py`; `scripts/e2e_smoke.py` | yes | synthetic integrated input |
| C02 | Linked particle-trajectory recent-rate posterior | E1 | `analysis/state_space.py`; `tests/test_state_and_cut.py` | yes | no external calibration |
| C03 | Uncertainty-weighted strength trends and empirical-Bayes shrinkage | E1 | `analysis/strength.py`; strength tests | yes | no controlled 1RM validation |
| C04 | Robust multi-day MILP with independent hard-constraint reconstruction | E1 | `optimization/diet.py`; optimizer tests | yes | local prices, availability, and adherence not established |
| C05 | Eight executable failure/decision cases | E1 | `resources/cases.yml`; `cases.py`; case tests | yes | deterministic synthetic fixtures |
| C06 | Structurally separate private and share-safe reports | E1 | `reporting/profiles.py`; privacy/report tests | yes | share-safe does not guarantee anonymity |
| C07 | Bounded adapters and atomic writes/downloads | E1 | `input_safety.py`; importers; IO tests | yes | not every vendor has a native adapter |
| C08 | Reproducible distribution and isolated install | E1 | `fresh_install_smoke.py`; verifier evidence | yes | local execution is not public CI |
| C09 | Dependency and public-tree credential audit | E1 | `pip-audit`; `privacy.py`; adversarial tests | yes | scanners and vulnerability databases are incomplete |
| C10 | Evidence-bound public claims | E2 | `data/registry/claims.yml`; `verify_claims.py` | yes | registry validates boundaries, not external truth |
| C11 | Public repository and CI | E5 | workflow definitions only | no | no verified remote in this state |
| C12 | Users, adoption, external review, or impact | E5 | explicit zero/not-observed registry | no | requires genuine external records |

Evidence levels: E1 reproduced in the reviewed checkout; E2 direct versioned evidence; E3 visible
only; E4 author/readme assertion; E5 planned or absent; NA not applicable.

## D. Strict 100-point scorecard

| Dimension | Max | Baseline | Current | Change | Main evidence | Remaining deduction |
|---|---:|---:|---:|---:|---|---|
| Problem definition and target user | 8 | 7 | 8 | +1 | README, limitations | none for the declared scope |
| Implementation and system completeness | 12 | 9 | 12 | +3 | pipeline, E2E, executable cases | none for local alpha |
| Method and domain correctness | 12 | 8 | 11 | +3 | linked trajectories, weighted strength, independent MILP audit | no external calibration |
| Data and case quality | 10 | 5 | 7 | +2 | eight distinct synthetic cases, source registry | no bundled observed longitudinal benchmark |
| Evidence chain and reproducibility | 13 | 9 | 13 | +4 | fingerprinted verifier, claims, fresh install | none locally |
| Testing, reliability, engineering | 11 | 8 | 11 | +3 | failure tests, coverage, build, E2E | none locally |
| Security, privacy, governance | 8 | 4 | 8 | +4 | distinct profiles, credential scan, pip-audit | no external security review |
| UX, accessibility, documentation | 7 | 6 | 6 | 0 | Streamlit AppTest, browser review, bilingual docs | no independent usability/accessibility study |
| Release, portability, public verifiability | 6 | 3 | 3 | 0 | wheel/fresh install and workflow definitions | no verified remote, CI, tag, or release |
| External validity, real use, independent validation | 8 | 0 | 0 | 0 | explicit limitations/zero registry | all qualifying external evidence absent |
| Claim discipline and portfolio value | 5 | 5 | 5 | 0 | claims registry, scope notes, case boundaries | none |
| **Total** | **100** | **64** | **84** | **+20** | versioned registry validated by script | external and publication evidence remain |

The values and cap arithmetic are machine-checked in `data/registry/strict_audit.yml` by
`scripts/verify_strict_audit.py`. This does not turn judgment-based scoring into model accuracy.

## E. Score-cap review

| Cap condition | Baseline | Current | Evidence |
|---|---|---|---|
| Core flow cannot run: cap 69 | triggered | not triggered | baseline E2E raised on solver time limit; current E2E passes |
| Core test/build failure: cap 79 | triggered | not triggered | baseline 31 passed/1 failed; current full gate required |
| Core conclusions not traceable: cap 79 | not triggered | not triggered | code, tests, registries, and receipts exist |
| README main capability not implemented: cap 74 | not triggered | not triggered | core paths are executable |
| Serious privacy/security issue: cap 69 | triggered | not triggered | baseline serialized sensitive daily fields despite copy; distinct schemas now tested |
| Synthetic represented as real: cap 69 | not triggered | not triggered | every bundled case is labeled synthetic |
| Correlation represented as causation: cap 69 | not triggered | not triggered | no causal outcome claim |
| Internal test represented as external impact: cap 84 | not triggered | not triggered | explicit claim separation |
| No external review/domain evidence/public artifact/real impact: cap 93 | triggered | triggered prepublication | current 84 is below the cap |
| Page without core logic: cap 59 | not triggered | not triggered | analytical core and CLI are implemented |

## F. Issue ledger

| ID | Priority | Issue | Location | Impact | Status | Verification |
|---|---|---|---|---|---|---|
| B-P0-01 | P0 | Report copy and serialized daily health fields disagreed | reporting pipeline | privacy, claims | fixed | negative-field report tests |
| B-P1-01 | P1 | Time-limited MILP incumbent was required/labeled as optimal | optimizer and old test | correctness, E2E | fixed | status/gap tests and independent validation |
| B-P1-02 | P1 | Recent-rate approximation ignored linked trajectory covariance | state-space analysis | method validity | fixed | ancestry-preserving fixed-seed tests |
| B-P1-03 | P1 | Strength method language exceeded the implemented heuristic | strength/docs | method claims | fixed | explicit empirical-Bayes naming and tests |
| B-P1-04 | P1 | Solver output lacked a full independent hard-constraint audit | diet optimizer | feasibility evidence | fixed | mutation and reconstruction tests |
| B-P1-05 | P1 | One happy-path demo did not cover abstention/failure modes | cases/README | data/case evidence | fixed | 8/8 executable cases |
| S-P2-01 | P2 | Full local gate lacked dependency-vulnerability auditing | verifier/workflow | security | fixed | pip-audit gate |
| S-P2-02 | P2 | Publication scanner omitted common credentials/private keys | privacy scanner | security | fixed | adversarial token/key/.env tests |
| S-P2-03 | P2 | Internal 100/100 could be confused with a portfolio/external score | scoring docs | claim discipline | fixed | separate strict registry/document |
| V-P1-01 | P1 | Integrated gates still treated an arbitrary ≤20% objective gap as a feasibility requirement; the seven-day vegetarian case could time out without an incumbent | cases/tests/E2E/score | hardware-dependent failures and method confusion | fixed, final verification pending | feasibility now requires independent hard-constraint reconstruction plus a finite nonnegative disclosed gap; constrained case reduced to three days while retaining all declared constraint types; 3 × 8/8 case preflights and 2 × E2E passes |
| V-P2-01 | P2 | Phone scanner matched long decimal metrics | privacy scanner | false publication failure | fixed, final verification pending | decimal/commit regression test and zero-finding 74-file scan |
| V-P2-02 | P2 | “Deterministic demo” language implied byte-stable MILP output | CLI/README/E2E docs | reproducibility overclaim | fixed | fixed inputs are separated from time-limited incumbent variability |
| V-P2-03 | P2 | Default dependency-audit service timed out during the second full verifier | verifier/CI | network-dependent false failure | fixed, final verification pending | OSV service with explicit 60-second socket timeout; network errors still fail closed |
| V-P1-02 | P1 | Fresh-wheel verification had no phase telemetry and a 420-second total timeout that failed under a slow local runtime | fresh-install/verifier | reproducibility gate instability and stale-artifact risk | fixed, final verification pending | binary-only install, phase timings, captured timeout output, 600-second command and 900-second total bounds |
| R-P2-01 | P2 | No public remote or completed CI evidence | release | public verification | pending external publication | remote SHA and Actions required |
| X-P2-01 | P2 | No observed longitudinal benchmark suitable for core outcome validation | data/method | external validity | external dependency | governed licensed cohort required |
| X-P2-02 | P2 | No independent usability/accessibility or method review | external evidence | UX/validity | external dependency | real reviewers/participants required |

No known unresolved P0 or P1 remains after targeted preflight. That conclusion is conditional until
the complete verifier passes. Remaining external P2 items cannot be closed by rewriting
documentation or adding more synthetic tests.

## G. Iteration record

### Round 0 — frozen baseline

- Goal: independently reproduce the initial state rather than infer it from later documentation.
- Checkout: detached `0c0c664` temporary worktree.
- Commands: Ruff check/format, strict Mypy, pytest with branch coverage, build, old verifier, E2E.
- Result: lint/type/build passed; 31 tests passed and one failed; full verifier and E2E failed.
- Score: 64/100, with core-flow and privacy caps applicable.
- Regression boundary: temporary worktree was removed; current `main` was not modified.

### Round 1 — method, privacy, case, and reproducibility hardening

- Goal: remove every locally fixable P0/P1.
- Main changes: linked posterior histories; uncertainty-weighted/empirical-Bayes strength analysis;
  independent MILP validation; eight cases; private/share-safe schemas; bounded inputs; atomic IO;
  claims registry; fresh install; UI and documentation hardening.
- Base result: `54b5241` passed the repository verifier and machine score at 100/100.
- Strict score before the current security pass: 82/100.

### Round 2 — strict security and score-separation pass

- Goal: close high-value P2 gaps identified by the independent rubric.
- Changes: pip-audit in local/CI gates; common credential/private-key filename/content detection;
  adversarial tests; a versioned strict score registry with cap validation.
- First complete-verifier result: failed. It exposed two optimizer-gate failures, a Streamlit startup
  timeout, and a privacy-phone false positive. Ruff, Mypy, build, isolated install, dependency audit,
  API, claims, strict-audit, link, CLI, and documentation checks passed.

### Round 3 — verifier-driven reliability correction

- Goal: correct the new failures without hiding solver quality or weakening hard constraints.
- Changes: feasibility is based on independently reconstructed hard constraints; solver status and a
  finite nonnegative gap remain mandatory and visible, but no arbitrary gap threshold is called a
  feasibility rule. The high-constraint vegetarian fixture is three days while retaining nutrition,
  budget, time, variety, tag, and allergen checks. Expected domain errors are retained per case.
- Additional changes: longer bounded UI smoke timeouts; decimal/commit phone-scanner exclusions;
  explicit warning that a time-limited solver does not promise byte-identical reports.
- Targeted result: 10 tests passed with one slow case test deselected; three consecutive case runs
  passed 8/8; two consecutive E2E runs passed; Streamlit AppTest passed; strict Mypy passed; the
  dependency audit found no known vulnerabilities; the 74-file public-tree scan found no findings.
- Remaining gate: complete checkout-bound verifier and machine score.

### Round 3b — dependency-audit transport hardening

- Second complete-verifier result: every local gate passed except dependency audit; its captured
  traceback showed a PyPI TLS/read timeout, not a vulnerability finding.
- Change: local and CI audits now use pip-audit's supported OSV service with a 60-second socket
  timeout. The gate remains fail-closed on service errors.
- Targeted result: OSV audit completed and reported no known vulnerabilities.
- Remaining gate: rerun the complete checkout-bound verifier after this configuration change.

### Round 3c — isolated-install observability and time budget

- Third complete-verifier result: all gates except fresh install passed. The fresh install was killed at
  its 420-second outer limit before it could replace an older evidence file; ordinary CLI/UI startup
  was also much slower on that run, while the prior full run had completed fresh install in 311 seconds.
- Change: require dependency wheels, emit virtual-environment/install/API/pip-check phase timings,
  retain captured output on timeout, and use bounded 600-second command / 900-second total limits.
- Targeted result: fresh-wheel verification passed in 470.007 seconds (venv 44.722, wheel install
  297.183, packaged resources/API 119.651, pip check 5.196).
- Remaining gate: rerun the complete checkout-bound verifier; stale `fresh-install.json` is not proof.

### Round 4 — publication

- Goal: create the authorized public repository, push the exact local commit, and wait for terminal CI.
- Status in this document: pending; public evidence must not be scored until remote SHA equality and
  workflow conclusions are observed.

## H. Final verification results

| Check | Baseline | Current preflight / final requirement |
|---|---|---|
| Ruff lint/format | pass | pass |
| Strict Mypy | pass | targeted rerun passed; full gate must pass |
| Pytest | 31 passed, 1 failed | 10 targeted passed, one slow deselected; full suite must pass |
| Combined/statement/branch coverage | 91.9341 / 93.6831 / 85.4% | ≥90 / reported / ≥80% |
| Build | pass | sdist and wheel pass |
| Full verifier | failed | must pass |
| E2E | failed on diet solver time limit | 2/2 targeted runs passed with status/gap disclosure; full gate must pass |
| Isolated install and packaged resources | incomplete evidence | must pass |
| Dependency vulnerability audit | absent | preflight: no known vulnerabilities; full gate must pass |
| Credential/privacy scan | incomplete | preflight: 74 files, zero findings; full gate must pass |
| Browser/UI | startup evidence | AppTest preflight passed; full gate must pass; screenshots are documentation artifacts, not usability evidence |
| Documentation/links/claims | prose-heavy | semantic, link, image, claim, and strict-audit validators required |
| Public remote and Actions | absent | pending publication |

Generated evidence is intentionally ignored by Git. The authoritative local files are
`artifacts/verification.json`, `artifacts/score.json`, `artifacts/cases.json`, and
`artifacts/e2e/summary.json`, bound to the checkout fingerprint.

## I. Safe public claims

### Can be stated now

- CutSignal implements local decision analytics across trend weight, strength retention, and robust
  food-plan feasibility.
- The repository contains eight fixed-input synthetic cases with executable assertions and limits.
- The current methods and engineering gates can be described with their exact local evidence after
  the full verifier passes for the published commit.
- Private-detail and structurally minimized share-safe report schemas are distinct.

### Must include limitations

- Linked-particle plateau probability: a model summary without external calibration, not a diagnosis.
- Strength trends: heuristic formula uncertainty and empirical-Bayes shrinkage without controlled
  maximal-strength validation.
- Diet plan: feasibility under user-supplied bounds; a nonzero MIP gap limits optimality claims.
- Share-safe output: data minimized, not guaranteed anonymous.
- Dependency/credential scans: no known findings in the checked state, not a security certification.

### Cannot currently be stated

- Clinical validity, causal fat-loss effects, known individual calorie deficit, or expected weight loss.
- Real users, production deployment, institutional adoption, independent review, or real-world impact.
- Population fairness or performance across devices, activities, regions, and demographic groups.
- A public GitHub/CI/Release state until those exact remote records exist.
- A 10k-star community, community maturity, or any star count not directly observed.

## J. Remaining gaps

### Solvable through code

- None at P0/P1 after a successful full verifier. Additional adapters are conditional roadmap work,
  not a reason to widen current claims.

### Requires maintainer/user decision

- Whether and when to create a signed version tag and GitHub Release.
- Which confidential security-reporting channel to support.

### Requires domain experts

- Plateau calibration design, controlled strength protocol, nutrition appropriateness, subgroup/fairness
  review, and deployment boundaries.

### Requires real users or external validation

- Independent reproduction, usability/accessibility studies, real adherence, longitudinal outcomes,
  adoption, production reliability, and impact.

### Not obtainable from this repository alone

- Clinical approval, security certification, community scale, institutional trust, or causal outcomes.

## K. Highest-value next actions

| Rank | Action | Expected benefit | Cost | Risk | Dependency |
|---:|---|---|---|---|---|
| 1 | Publish exact commit and wait for terminal cross-platform/security Actions | raises public verifiability; validates workflow definitions | low | CI may expose portability/dependency failures | authenticated GitHub access |
| 2 | Pre-register simulations and calibration metrics for plateau decisions | strongest method-validity improvement | medium | poor calibration may narrow claims | statistical review |
| 3 | Obtain a governed, feature-compatible longitudinal cohort | observed external validity | high | privacy, consent, selection, licensing | external partner/data governance |
| 4 | Run controlled strength and structured usability/accessibility studies | validates two major product/method gaps | high | participant safety and recruitment | qualified reviewers/participants |
| 5 | Validate regional food prices, labels, availability, and adherence | improves optimizer realism | high | rapid data drift and heterogeneous behavior | regional data and real users |

Adding more synthetic screenshots or self-scored categories ranks below these actions because it would
not change external validity or real-use evidence.
