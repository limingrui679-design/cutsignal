# Privacy and threat model

Fitness and weight histories are sensitive even when they do not contain a medical diagnosis.
CutSignal therefore defaults to a local, single-user workflow.

## Data flow

- Native exports are read locally.
- Apple Health ZIP members are streamed; the archive is not extracted.
- Normalized private JSONL should remain under ignored directories such as `data/private/`.
- Statistical and optimization engines receive validated records in memory.
- HTML/JSON reports contain derived daily states, exercise aggregates, menu aggregates, limitations,
  and decisions. They omit source IDs, device strings, raw strength sets, and provenance objects.
- There is no telemetry, account, hosted database, advertising SDK, or model API.

## Threats addressed

| Threat | Control |
|---|---|
| Accidental Git commit of an export | Ignore rules plus `cutsignal privacy-audit`. |
| ZIP path traversal or decompression bomb | No extraction, path validation, size and compression-ratio limits. |
| Phone and watch double-counting | Per-source totals and explicit max-source reconciliation flag. |
| Credential leakage | API keys come from environment variables and are absent from reports. |
| Re-identification through raw records | Public demo is synthetic; reports receive derived models only. |
| Overconfident health action | Coverage/uncertainty gates and non-prescriptive output vocabulary. |

## Threats not solved

- A compromised computer or browser can read local files.
- An HTML report can still reveal weight, estimated energy expenditure, and training trends.
- The scanner uses heuristics and cannot certify anonymization.
- Git history retains a secret after deletion from the working tree.
- Cloud-synced folders may upload local files independently of CutSignal.

## Safe publication checklist

1. Put real exports outside the repository or under an ignored private directory.
2. Run `cutsignal privacy-audit .` before committing.
3. Inspect `git status` and staged diffs.
4. Open generated reports and decide whether their derived metrics are acceptable to share.
5. If sensitive data ever entered Git, rewrite history using an appropriate tool, invalidate all
   exposed credentials, and follow the host's cached-fork removal process.

Security reports should follow [SECURITY.md](../SECURITY.md), not a public issue.
