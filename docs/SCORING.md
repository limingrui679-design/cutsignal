# Machine scoring rubric

The versioned rubric totals 100 points. Every category is all-or-nothing so a strong demo cannot
hide a failed privacy, method, or reproducibility gate.

| Category | Points | Machine evidence |
|---|---:|---|
| Automated tests and branch coverage | 16 | Pytest passes; combined statement-and-branch coverage ≥90% and branch-only coverage ≥80% |
| Trajectory posterior, sensitivity, and evidence gates | 14 | 112-day run, linked-particle rate, five scenarios, instability gate, nine cases, 12-run known-truth benchmark |
| Strength uncertainty and training-load evidence | 10 | Three exercises, repeated sessions/weeks, uncertainty-weighted empirical Bayes |
| Robust diet MILP and independent validation | 14 | Seven days, all post-solve checks, five shocks, finite nonnegative disclosed gap, sampled trade-offs |
| Device-independent adapters and bounded inputs | 8 | Apple Health, generic, strength, food, and safety-limit tests |
| Privacy profiles and public-tree audit | 10 | Private label, structurally minimized share-safe bundle, heuristic tree scan |
| Static analysis and formatting | 8 | Ruff lint/format and strict mypy |
| CLI, casebook, and local UI | 5 | CLI help and doctor, nine executable cases, Streamlit application-test startup |
| Build and isolated-install reproducibility | 10 | sdist/wheel, temporary-venv install, package resources/API, `pip check`, `pip-audit` |
| Documentation, sources, and claims | 5 | Required/semantic docs, source registry, evidence-bound claims registry |

`verify_project.py` fingerprints the checkout (excluding generated artifacts and local caches),
clears only its declared output paths before rebuilding, and records command, return code, duration,
output tail, platform, Python version, coverage, privacy scan, documentation checks, and end-to-end
results. It also records SHA-256 and byte size for every score-critical artifact.
`score_project.py` refuses to reuse evidence after any source, test, configuration, documentation,
or recorded-artifact change.

This machine rubric deliberately measures only controls versioned inside the repository. The
independent deep review in `docs/DEEP_AUDIT_2026-08-24.md` uses a separate 100-point scale that includes
data realism, public release evidence, external validity, real use, and independent review. The two
scores answer different questions and must not be substituted for one another.

A score of 100 means the repository passed this engineering rubric for that exact checkout. It does
not mean the model is clinically accurate, externally validated, unbiased, deployment-ready,
adopted, or impactful. CI is a workflow definition until a remote actually runs it.
