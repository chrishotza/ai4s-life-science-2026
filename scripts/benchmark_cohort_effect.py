from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai4s_phenotype import compare_cohorts


def make_synthetic_cohorts(seed: int = 123, n_per_group: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    control = pd.DataFrame(
        {
            "condition": "control",
            "mean_speed": rng.normal(0.55, 0.08, n_per_group),
            "directional_persistence": np.clip(rng.normal(0.80, 0.06, n_per_group), 0.0, 1.0),
            "displacement": rng.normal(3.0, 0.45, n_per_group),
            "path_length": rng.normal(3.6, 0.5, n_per_group),
            "observation_fraction": np.clip(rng.normal(0.95, 0.03, n_per_group), 0.0, 1.0),
        }
    )
    treated = pd.DataFrame(
        {
            "condition": "treated",
            "mean_speed": rng.normal(0.90, 0.10, n_per_group),
            "directional_persistence": np.clip(rng.normal(0.58, 0.08, n_per_group), 0.0, 1.0),
            "displacement": rng.normal(5.0, 0.60, n_per_group),
            "path_length": rng.normal(6.0, 0.75, n_per_group),
            "observation_fraction": np.clip(rng.normal(0.91, 0.04, n_per_group), 0.0, 1.0),
        }
    )
    return pd.concat([control, treated], ignore_index=True)


def main() -> None:
    frame = make_synthetic_cohorts()
    result = compare_cohorts(
        frame,
        group_column="condition",
        group_a="treated",
        group_b="control",
        random_state=17,
        n_bootstrap=2000,
    )

    table = result.table.sort_values(
        "standardized_mean_difference",
        key=lambda series: series.abs(),
        ascending=False,
    ).reset_index(drop=True)

    output = {
        "benchmark": "cohort phenotype effect recovery",
        "purpose": (
            "demonstrate uncertainty-aware comparison of phenotype cohorts; "
            "this synthetic benchmark is not biological validation"
        ),
        "group_a": result.group_a,
        "group_b": result.group_b,
        "n_per_group": 60,
        "results": table.to_dict(orient="records"),
        "strongest_effect": table.iloc[0].to_dict(),
    }

    (ROOT / "cohort_effect_results.json").write_text(json.dumps(output, indent=2))
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
