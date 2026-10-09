"""Offline ALFI expert-cell-identity tracking edge contract tests."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.benchmark_alfi_oracle_tracking import (
    evaluate_sequence, oracle_edges,
)


def synthetic_two_tracks():
    records = []
    for t in range(1, 5):
        for ident, initial_x in ((1, 20), (2, 220)):
            records.append(dict(
                ImNo=t, ID=ident,
                xmin=initial_x + 2*t, ymin=15 + t,
                width=20, height=20,
                observation_id=len(records),
            ))
    return pd.DataFrame(records)


def test_oracle_adjacent_edges_and_mapped_association():
    expert = synthetic_two_tracks()
    assert len(oracle_edges(expert)) == 6
    for method in ("mutual_nn", "hungarian", "velocity_hungarian"):
        result = evaluate_sequence(expert, method)
        assert result["oracle_detections"] == 8
        assert result["oracle_temporal_edges"] == 6
        assert result["matched_edges"] == 6
        assert result["precision"] == result["recall"] == 1.0
        assert result["f1"] == 1.0


def test_oracle_edges_disallow_gaps():
    expert = synthetic_two_tracks()
    after = expert[~((expert["ImNo"] == 2) & (expert["ID"] == 1))]
    assert len(oracle_edges(after)) == 4
