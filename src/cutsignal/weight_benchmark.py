"""Prequential scale-weight comparison. Only aggregate errors leave this module."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from statistics import mean, median

from cutsignal.analysis.state_space import ParticleFilterConfig, run_particle_filter
from cutsignal.models import DailyObservation


def compare_weigh_ins(path: Path, config: ParticleFilterConfig | None = None) -> dict[str, float | int]:
    """Read a Fitabase weight CSV. Score after three past days, on gaps of at most seven days."""
    if path.stat().st_size > 10_000_000:
        raise ValueError("Weight CSV must be at most 10 MB")
    groups: dict[str, dict[date, list[float]]] = defaultdict(lambda: defaultdict(list))
    count = 0
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"Id", "Date", "WeightKg"} <= set(reader.fieldnames or []):
            raise ValueError("Expected Fitabase columns Id, Date and WeightKg")
        for row in reader:
            person = row["Id"].strip()
            day = datetime.strptime(row["Date"], "%m/%d/%Y %I:%M:%S %p").date()
            weight = float(row["WeightKg"])
            if not person or not 20 < weight < 400:
                raise ValueError("Invalid participant key or scale weight")
            groups[person][day].append(weight)
            count += 1
    model_errors: list[float] = []
    last_errors: list[float] = []
    paired: list[float] = []
    for days in groups.values():
        dates = sorted(days)
        if len(dates) < 4:
            continue
        # Long gaps start a new local history; a far-future row cannot inflate calendar allocation.
        segments: list[list[DailyObservation]] = []
        for day in dates:
            if not segments or (day - segments[-1][-1].date).days > 7:
                segments.append([])
            segments[-1].append(DailyObservation(date=day, weight_kg=median(days[day])))
        personal = []
        for segment in segments:
            if len(segment) < 4:
                continue
            states = {s.date: s for s in run_particle_filter(segment, config)}
            for idx in range(3, len(segment)):
                item, previous = segment[idx], segment[idx - 1]
                prior = states[item.date].prior_scale_weight_median_kg
                assert prior is not None and item.weight_kg is not None and previous.weight_kg is not None
                error = abs(item.weight_kg - prior)
                baseline = abs(item.weight_kg - previous.weight_kg)
                model_errors.append(error)
                last_errors.append(baseline)
                personal.append(baseline - error)
        if personal:
            paired.append(mean(personal))
    if not paired:
        raise ValueError("No eligible participant has four qualifying weigh-in days")
    return {
        "source_records": count,
        "source_participants": len(groups),
        "evaluated_participants": len(paired),
        "evaluated_weigh_ins": len(model_errors),
        "particle_mae_kg": mean(model_errors),
        "persistence_mae_kg": mean(last_errors),
        "participant_balanced_mae_gain_kg": mean(paired),
    }
