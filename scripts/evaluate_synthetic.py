#!/usr/bin/env python3
"""Generate machine-readable, known-truth synthetic evaluation evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from cutsignal.evaluation import evaluate_synthetic_benchmark


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/synthetic-evaluation.json"))
    parser.add_argument("--particles", type=int, default=500)
    args = parser.parse_args()
    result = evaluate_synthetic_benchmark(particles=args.particles)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    for summary in result.summaries:
        print(
            f"{summary.method}: runs={summary.runs}; "
            f"MAE={summary.mean_absolute_error_kg_per_week:.4f} kg/week; "
            f"coverage={summary.interval_coverage:.1%}; Brier={summary.mean_brier_score:.4f}; "
            f"accuracy={summary.classification_accuracy:.1%}; "
            f"FP={summary.false_positives}; FN={summary.false_negatives}"
        )
    print(f"evidence: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
