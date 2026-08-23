# Machine scoring rubric

The versioned rubric totals 100 points. Every category is all-or-nothing so a strong demo cannot
hide a failed privacy, method, or reproducibility gate.

| Category | Points | Machine evidence |
|---|---:|---|
| Automated tests and branch coverage | 16 | Pytest passes; combined statement-and-branch coverage ≥90% and branch-only coverage ≥80% |
| Trajectory posterior, sensitivity, and evidence gates | 14 | 112-day run, linked-particle rate, five scenarios, instability gate, eight cases |
| Strength uncertainty and training-load evidence | 10 | Three exercises, repeated sessions/weeks, uncertainty-weighted empirical Bayes |
| Robust diet MILP and independent validation | 14 | Seven days, all post-solve checks, five shocks, gap ≤20%, sampled trade-offs |
| Device-independent adapters and bounded inputs | 8 | Apple Health, generic, strength, food, and safety-limit tests |
| Privacy profiles and public-tree audit | 10 | Private label, structurally minimized share-safe bundle, heuristic tree scan |
| Static analysis and formatting | 8 | Ruff lint/format and strict mypy |
| CLI, casebook, and local UI | 5 | CLI help, eight executable cases, Streamlit application-test startup |
| Build and isolated-install reproducibility | 10 | sdist/wheel, temporary-venv install, package resources/API, `pip check` |
| Documentation, sources, and claims | 5 | Required/semantic docs, source registry, evidence-bound claims registry |

`verify_project.py` fingerprints the checkout (excluding generated artifacts and local caches) and
records command, return code, duration, output tail, platform, Python version, coverage, privacy
scan, documentation checks, and end-to-end results. `score_project.py` refuses to reuse evidence
after any source, test, configuration, or documentation change.

A score of 100 means the repository passed this engineering rubric for that exact checkout. It does
not mean the model is clinically accurate, externally validated, unbiased, deployment-ready,
adopted, or impactful. CI is a workflow definition until a remote actually runs it.
