from datetime import date
from types import SimpleNamespace

import pytest

from cutsignal import weight_benchmark as wb


def test_hindsight_matches_exhaustive_single_switch():
    errors = [(1.0, 8.0), (2.0, 5.0), (6.0, 0.0), (6.0, 2.0)]
    fixed, switch = wb._hindsight_selector_losses(errors)
    assert fixed == min(sum(row[i] for row in errors) for i in (0, 1))
    expected = min(
        sum(row[i if k < split else 1 - i] for k, row in enumerate(errors))
        for split in range(len(errors) + 1)
        for i in (0, 1)
    )
    assert switch == expected == 5
    assert wb._online_particle_weight(0, 0) == 0.5
    assert wb._online_particle_weight(1e6, 0) == 1
    assert wb._online_particle_weight(0, 1e6) == 0


def test_chronological_weights_and_segment_reset(tmp_path, monkeypatch):
    path = tmp_path / "weights.csv"
    days = [1, 2, 3, 4, 5, 16, 17, 18, 19]
    observations = [70, 70, 70, 72, 72, 70, 70, 70, 72]
    path.write_text(
        "Id,Date,WeightKg\n"
        + "".join(f"a,04/{day}/2016 10:00:00 AM,{weight}\n" for day, weight in zip(days, observations, strict=True))
    )

    def fake(segment, config):
        return [
            SimpleNamespace(date=o.date, prior_scale_weight_median_kg=72 if o.date != date(2016, 4, 5) else 74)
            for o in segment
        ]

    monkeypatch.setattr(wb, "run_particle_filter", fake)
    report = wb.compare_weigh_ins(path)
    updated = wb._online_particle_weight(2, 0)
    assert report["online_mix_mae_kg"] == pytest.approx((1 + 2 * updated + 1) / 3)
    assert report["equal_mix_mae_kg"] == 1
