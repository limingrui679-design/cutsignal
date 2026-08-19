# Machine scoring rubric

The versioned rubric totals 100 points. Every category is all-or-nothing so a partial score cannot
hide a failed safety or reproducibility gate.

| Category | Points | Evidence |
|---|---:|---|
| Automated core tests and branch coverage | 20 | Pytest passes; analytical/adapter core coverage ≥90%. |
| CutSignal uncertainty and sensitivity | 12 | Full 112-day state series, five scenarios, stable evidence action. |
| LeanGuard repeated-session evidence | 8 | At least three exercises, 40 session metrics, non-empty frontier. |
| BudgetCut robust weekly MILP | 15 | Seven days, nonnegative robust slack, five stress tests, disclosed gap ≤35%, frontier. |
| Device-independent inputs and provenance | 10 | Apple Health plus generic daily, strength, and food adapters and tests. |
| Privacy and report redaction | 10 | Public-tree heuristic scan and derived-report identifier checks. |
| Static analysis and formatting | 10 | Ruff lint/format and strict mypy. |
| CLI and local UI startup | 5 | CLI help plus Streamlit application-test startup. |
| Installable wheel | 5 | PEP 517 wheel build. |
| Documentation and source registry | 5 | Required architecture, method, adapter, source, privacy, limitation, validation, contribution, and security files. |

`verify_project.py` hashes the checkout (excluding generated artifacts) and records raw check status.
`score_project.py` refuses to reuse passing evidence after any source, test, configuration, or
documentation change. The score deliberately does not claim clinical validation.
