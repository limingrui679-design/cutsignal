"""Optional public-cohort benchmark using OpenPowerlifting bulk CSV files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd

from cutsignal.exceptions import DataValidationError, InsufficientDataError

DEFAULT_DATA_URL = "https://openpowerlifting.gitlab.io/opl-csv/files/openpowerlifting-latest.zip"


def download_snapshot(
    destination: Path,
    *,
    url: str = DEFAULT_DATA_URL,
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """Download a timestamped public snapshot and write a provenance manifest."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    byte_count = 0
    headers = {"User-Agent": "CutSignal/0.1 public-data importer"}
    with httpx.stream("GET", url, timeout=timeout_seconds, headers=headers, follow_redirects=True) as r:
        r.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in r.iter_bytes():
                handle.write(chunk)
                digest.update(chunk)
                byte_count += len(chunk)
    manifest = {
        "source": "OpenPowerlifting",
        "url": url,
        "sha256": digest.hexdigest(),
        "bytes": byte_count,
        "license_note": "meet-data CSV is dedicated to the public domain by the provider",
        "identity_caveat": "Name|Sex keys are not verified unique persons",
    }
    manifest_path = destination.with_suffix(destination.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def cohort_percentile(
    csv_path: Path,
    *,
    total_kg: float,
    bodyweight_kg: float,
    sex: str,
    equipment: str = "Raw",
    tested_only: bool = True,
    bodyweight_band_kg: float = 5.0,
    chunk_size: int = 250_000,
) -> dict[str, float | int | str]:
    """Compare a competition total with a transparent local body-weight cohort."""
    required = {"Sex", "Equipment", "BodyweightKg", "TotalKg"}
    totals: list[np.ndarray] = []
    try:
        iterator = pd.read_csv(csv_path, usecols=lambda column: column in required | {"Tested"}, chunksize=chunk_size)
        for chunk in iterator:
            if not required <= set(chunk.columns):
                raise DataValidationError(f"OpenPowerlifting CSV is missing {sorted(required - set(chunk.columns))}")
            mask = (
                chunk["Sex"].astype(str).str.casefold().eq(sex.casefold())
                & chunk["Equipment"].astype(str).str.casefold().eq(equipment.casefold())
                & chunk["BodyweightKg"].between(bodyweight_kg - bodyweight_band_kg, bodyweight_kg + bodyweight_band_kg)
                & chunk["TotalKg"].notna()
                & (chunk["TotalKg"] > 0)
            )
            if tested_only and "Tested" in chunk.columns:
                mask &= chunk["Tested"].astype(str).str.casefold().eq("yes")
            selected = chunk.loc[mask, "TotalKg"].to_numpy(dtype=float)
            if selected.size:
                totals.append(selected)
    except (OSError, ValueError) as exc:
        raise DataValidationError(f"failed to read OpenPowerlifting CSV: {exc}") from exc
    if not totals:
        raise InsufficientDataError("no matching OpenPowerlifting cohort records")
    values = np.concatenate(totals)
    percentile = float((np.sum(values < total_kg) + 0.5 * np.sum(values == total_kg)) / values.size)
    return {
        "percentile": percentile,
        "cohort_rows": int(values.size),
        "cohort_median_total_kg": float(np.median(values)),
        "bodyweight_band_kg": bodyweight_band_kg,
        "sex": sex,
        "equipment": equipment,
        "tested_only": "yes" if tested_only else "no",
        "scope_note": "Competition benchmark only; acute weigh-in cuts are not longitudinal fat loss.",
    }
