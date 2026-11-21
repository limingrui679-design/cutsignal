import pytest

from cutsignal.analysis.state_space import ParticleFilterConfig
from cutsignal.weight_benchmark import compare_weigh_ins


def test_benchmark_expires_long_gaps_and_returns_aggregate_errors(tmp_path):
    file = tmp_path / "weights.csv"
    file.write_text(
        "Id,Date,WeightKg\n"
        + "".join(f"a,04/{day}/2016 10:00:00 AM,{70 + day / 100}\n" for day in (1, 2, 3, 4, 15))
        + "b,04/01/2016 09:00:00 AM,64\n"
    )
    result = compare_weigh_ins(file, ParticleFilterConfig(particles=500))
    assert result["source_participants"] == 2
    assert result["evaluated_participants"] == result["evaluated_weigh_ins"] == 1
    assert result["persistence_mae_kg"] == pytest.approx(0.01)
    for content in ("other\n", "Id,Date,WeightKg\n", "Id,Date,WeightKg\na,04/01/2016 09:00:00 AM,0\n"):
        file.write_text(content)
        with pytest.raises(ValueError):
            compare_weigh_ins(file)
