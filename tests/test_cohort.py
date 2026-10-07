import pandas as pd
import pytest

from ai4s_phenotype import compare_cohorts


def test_compare_cohorts_reports_effect_and_bootstrap_interval():
    frame = pd.DataFrame(
        [
            {"condition": "control", "mean_speed": 0.5, "directional_persistence": 0.8, "displacement": 2.0, "path_length": 2.2, "observation_fraction": 1.0},
            {"condition": "control", "mean_speed": 0.6, "directional_persistence": 0.75, "displacement": 2.5, "path_length": 2.8, "observation_fraction": 0.9},
            {"condition": "treated", "mean_speed": 1.0, "directional_persistence": 0.5, "displacement": 4.0, "path_length": 5.0, "observation_fraction": 0.95},
            {"condition": "treated", "mean_speed": 1.1, "directional_persistence": 0.45, "displacement": 4.5, "path_length": 5.5, "observation_fraction": 0.85},
        ]
    )

    result = compare_cohorts(
        frame,
        group_column="condition",
        group_a="treated",
        group_b="control",
        n_bootstrap=200,
        random_state=7,
    )

    assert set(result.table["feature"]) == {
        "mean_speed",
        "directional_persistence",
        "displacement",
        "path_length",
        "observation_fraction",
    }
    assert result.table["bootstrap_ci_low"].notna().all()
    assert result.table["bootstrap_ci_high"].notna().all()


def test_compare_cohorts_requires_both_groups():
    frame = pd.DataFrame(
        [
            {"condition": "control", "mean_speed": 0.5, "directional_persistence": 0.8, "displacement": 2.0, "path_length": 2.2, "observation_fraction": 1.0},
            {"condition": "control", "mean_speed": 0.6, "directional_persistence": 0.75, "displacement": 2.5, "path_length": 2.8, "observation_fraction": 0.9},
        ]
    )

    with pytest.raises(ValueError, match="both cohorts"):
        compare_cohorts(
            frame,
            group_column="condition",
            group_a="treated",
            group_b="control",
        )
