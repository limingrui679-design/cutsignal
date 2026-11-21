"""Prequential scale-weight comparison. Only aggregate errors leave this module."""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from statistics import mean, median

from cutsignal.analysis.state_space import ParticleFilterConfig, run_particle_filter
from cutsignal.models import DailyObservation


def _online_particle_weight(reference_loss_kg: float, particle_loss_kg: float) -> float:
    """Equal starting odds; a one-kg cumulative loss difference changes odds by e."""
    gap = reference_loss_kg - particle_loss_kg
    odds = math.exp(-abs(gap))
    return 1 / (1 + odds) if gap >= 0 else odds / (1 + odds)


def _hindsight_selector_losses(errors: list[tuple[float, float]]) -> tuple[float, float]:
    """Minimum cumulative loss for a hard selector with zero or at most one switch."""
    total_first = sum(first for first, _ in errors)
    total_second = sum(second for _, second in errors)
    fixed = best = min(total_first, total_second)
    prefix_difference = 0.0
    for first, second in errors:
        prefix_difference += first - second
        best = min(best, total_second + prefix_difference, total_first - prefix_difference)
    return fixed, best


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
    online_errors: list[float] = []
    equal_mix_errors: list[float] = []
    online_person_gains: list[float] = []
    oracle_fixed = oracle_switch = 0.0
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
        personal_online = []
        for segment in segments:
            if len(segment) < 4:
                continue
            states = {s.date: s for s in run_particle_filter(segment, config)}
            # Start fresh after a gap. The current outcome is revealed after choosing the weight.
            cumulative_reference = 0.0
            cumulative_particle = 0.0
            segment_errors: list[tuple[float, float]] = []
            for idx in range(3, len(segment)):
                item, previous = segment[idx], segment[idx - 1]
                prior = states[item.date].prior_scale_weight_median_kg
                assert prior is not None and item.weight_kg is not None and previous.weight_kg is not None
                error = abs(item.weight_kg - prior)
                baseline = abs(item.weight_kg - previous.weight_kg)
                weight = _online_particle_weight(cumulative_reference, cumulative_particle)
                delta = prior - previous.weight_kg
                online_error = abs(item.weight_kg - (previous.weight_kg + weight * delta))
                online_errors.append(online_error)
                equal_mix_errors.append(abs(item.weight_kg - (previous.weight_kg + 0.5 * delta)))
                personal_online.append(baseline - online_error)
                cumulative_particle += error
                cumulative_reference += baseline
                segment_errors.append((baseline, error))
                model_errors.append(error)
                last_errors.append(baseline)
                personal.append(baseline - error)
            fixed_loss, switch_loss = _hindsight_selector_losses(segment_errors)
            oracle_fixed += fixed_loss
            oracle_switch += switch_loss
        if personal:
            paired.append(mean(personal))
            online_person_gains.append(mean(personal_online))
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
        "online_mix_mae_kg": mean(online_errors),
        "equal_mix_mae_kg": mean(equal_mix_errors),
        "online_participant_balanced_gain_vs_persistence_kg": mean(online_person_gains),
        "participants_improved_by_online_mix": sum(gain > 0 for gain in online_person_gains),
        "hindsight_fixed_selector_mae_kg": oracle_fixed / len(model_errors),
        "hindsight_one_switch_selector_mae_kg": oracle_switch / len(model_errors),
    }
