# Privacy and threat model

Fitness and weight histories are sensitive even when they do not contain a medical diagnosis.
CutSignal therefore defaults to a local, single-user workflow.

## Data flow

- Native exports are read locally.
- Apple Health ZIP members are streamed; the archive is not extracted.
- Normalized private JSONL should remain under ignored directories such as `data/private/`.
- Statistical and optimization engines receive validated records in memory.
- The `private` HTML/JSON profile contains dates, observed weight/intake, latent daily states,
  exercise aggregates, menu details, limitations, and decisions. It omits source/device identifiers,
  credentials, raw strength sets, and provenance objects, but it is still sensitive.
- The `share-safe` profile removes dates, daily observed/latent series, exact health metrics,
  exercise and food names, menu entries, and exact constraints. It keeps coarse categories and
  decision gates, including a coarse solver-gap category. Data minimization reduces disclosure;
  it does not guarantee anonymity.
- There is no telemetry, account, hosted database, advertising SDK, or model API.

## Threats addressed

| Threat | Control |
|---|---|
| Accidental Git commit of an export | Ignore rules plus `cutsignal privacy-audit`. |
| ZIP path traversal or decompression bomb | No extraction, path validation, size and compression-ratio limits. |
| Oversized normalized/constraint input | File, row, line, upload, optimizer-catalog, and solver-time limits. |
| Phone and watch double-counting | Per-source totals and explicit max-source reconciliation flag. |
| Credential leakage | API keys come from environment variables and are absent from reports. |
| Accidental sharing of detailed series | Explicit `private` warning plus structurally minimized `share-safe` profile. |
| Overconfident health action | Coverage/uncertainty gates and non-prescriptive output vocabulary. |

## Threats not solved

- A compromised computer or browser can read local files.
- A private HTML report reveals dates, weight/intake observations, estimated energy expenditure,
  training trends, and menu details.
- A share-safe report can still reveal sensitive derived categories and is not an anonymity proof.
- The scanner uses heuristics and cannot certify anonymization.
- Text files above the complete-scan limit fail the audit for manual review; binary formats are
  skipped except for sensitive filename checks.
- A broad local directory walk skips declared generated/tool directories such as `artifacts/`,
  `dist/`, and `.venv`; the release verifier separately enumerates every tracked and non-ignored
  file, so a publishable file cannot hide behind those directory names.
- Git history retains a secret after deletion from the working tree.
- The publication scan rejects common GitHub-token, AWS access-key, private-key, `.env`, and key-file
  signatures, but it remains heuristic and cannot prove that every credential or identifier is absent.
- `pip-audit` queries the OSV vulnerability service with a bounded network timeout. A service error
  fails the gate; a clean result only means no known vulnerability was returned for that environment
  at that time and is not a security audit.
- Cloud-synced folders may upload local files independently of CutSignal.

## Safe publication checklist

1. Put real exports outside the repository or under an ignored private directory.
2. Run `cutsignal privacy-audit .` before committing.
3. Inspect `git status` and staged diffs.
4. Treat `private` reports as sensitive. Prefer `share-safe`, then inspect every retained category
   for the intended audience before sharing.
5. If sensitive data ever entered Git, rewrite history using an appropriate tool, invalidate all
   exposed credentials, and follow the host's cached-fork removal process.

Security reports should follow [SECURITY.md](../SECURITY.md), not a public issue.
