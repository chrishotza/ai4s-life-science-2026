"""Contracts for CTC empirical phenotype-stability benchmark (no new datasets)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.benchmark_ctc_real_phenotype_stability import stability_for_cohort


def test_seed_and_track_bootstrap_stability_has_bounded_ari():
    rows = []
    for seq in ("01", "02"):
        for i in range(15):
            rows.append({
                "sequence": seq, "track_id": i,
                "duration": 2+i, "observations": 3+i,
                "displacement": 0.1+i/2, "path_length": 1+i,
                "mean_speed": .2+i/4, "directional_persistence": i/15,
                "parent_count": i%2, "child_count": (i//3)%2,
                "descendant_count": (i//4)%2,
            })
    data = pd.DataFrame(rows)
    report = stability_for_cohort(data, n_seeds=3, n_bootstrap=6)
    assert report["n_profiles"] == 30
    assert report["n_sequences"] == 2
    assert sum(report["cluster_counts"]) == 30
    assert report["n_shorter_than_three"] == 0
    for key in ("seed_ari", "stratified_track_bootstrap_ari"):
        scores = report[key]
        for stat in ("min", "median", "max"):
            assert np.isfinite(scores[stat])
            assert -1 <= scores[stat] <= 1
