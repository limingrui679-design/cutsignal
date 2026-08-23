# Troubleshooting

## Start with diagnostics

```bash
cutsignal doctor --json
cutsignal --help
```

The doctor output is safe to share only after you inspect it; it contains runtime and platform
versions, not health rows or secrets.

| Symptom | Likely boundary | Recovery |
|---|---|---|
| `Python ... unsupported` | Python is older than 3.11 | Create a new 3.11–3.13 virtual environment and reinstall |
| `cutsignal: command not found` | The intended environment is inactive or the package is not installed | Activate the venv and run `python -m pip install -e .`; `python -m cutsignal --help` is an equivalent check |
| UI asks for an optional dependency | Core was installed without the UI extra | Run `python -m pip install -e '.[ui]'` |
| `Input error:` during import | Column aliases, unit values, date parsing, size, row, or schema validation failed | Reduce to a synthetic minimal file; compare with the schema in `DATA_CARD.md`; do not post the real export |
| `collect_more_data` | A deliberate evidence gate, not a crash | Inspect completeness/TDEE interval and collect the listed next evidence |
| Diet optimization is infeasible | No menu satisfies all declared hard bounds | Review solver explanation; relax one user-selected constraint at a time; never hide infeasibility |
| `feasible_time_limit` with a nonzero gap | A validated incumbent was found before optimality was proved | Treat feasibility and objective optimality separately; increase the time limit if objective quality matters |
| Dependency audit times out | OSV/network service was unavailable | Retry later; do not describe the failed audit as “no vulnerabilities” |
| Dependency audit names `setuptools` | A Python bootstrap tool in the active environment is vulnerable even if CutSignal does not import it | Use a clean venv and run `python -m pip install --upgrade pip 'setuptools>=83,<85'`; do not ignore an environment package |
| Full verifier appears slow | It creates a fresh venv, installs a wheel, runs UI/E2E/cases, and audits dependencies | Follow printed phase progress; preserve the first failing gate and its output |
| Share-safe report still feels identifying | Minimization does not guarantee anonymity | Do not share it; manually review derived categories and context |

## Minimal reproduction rule

Create a new synthetic file with the fewest rows and fields that still reproduces the behavior.
Keep exact dates, names, device IDs, foods, paths, and values from a real person out of public issues.
See [SUPPORT.md](../SUPPORT.md) and [SECURITY.md](../SECURITY.md).
