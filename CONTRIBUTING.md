# Contributing

Thanks for improving CutSignal. Keep changes small, testable, and explicit about evidence boundaries.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
mypy src/cutsignal
pytest --cov=cutsignal --cov-report=term-missing
cutsignal cases verify --output artifacts/cases.json
python scripts/verify_project.py
python scripts/score_project.py
```

Do not commit a real health, nutrition, or training export. New fixtures must be synthetic and must
not preserve a real person's exact dates or values.

## Pull requests

- State the decision or failure mode the change addresses.
- Add tests for both the expected path and at least one boundary/failure path.
- Document any new assumption, source, license, reconciliation rule, or output interpretation.
- Do not turn a model output into medical advice or a causal claim.
- For a new adapter, follow the checklist in `docs/DEVICE_ADAPTERS.md`.
- For a new public dataset, add a registry record and verify downloadability, license, deduplication,
  identity, target definition, and split leakage separately.
- For a new public capability statement, update `data/registry/claims.yml` with direct evidence and
  an explicit list of what the evidence does not establish.
- Report profiles are security-relevant: add negative tests for every field that must not appear in
  `share-safe` output.

The code of conduct applies to all project spaces.
