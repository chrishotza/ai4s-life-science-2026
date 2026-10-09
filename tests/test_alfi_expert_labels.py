"""Offline tests of expert-track integrity and past-only ALFI feature computation."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.evaluate_alfi_expert_labels import engineer_features, evaluate


def test_past_only_features_do_not_look_ahead():
    records = []
    for frame, width in [(1, 10), (3, 12), (6, 100)]:
        records.append(dict(sequence="MI01", track_id=1, frame=frame,
                            label="EarlyMitosis", xmin=10 + frame,
                            ymin=20, width=width, height=10))
    complete = engineer_features(pd.DataFrame(records))
    truncated = engineer_features(pd.DataFrame(records[:2]))
    # Altering the future frame cannot change features on prior frames.
    cols = [c for c in complete if c not in ("sequence", "track_id", "frame", "label")]
    np.testing.assert_allclose(
        complete.loc[:1, cols].to_numpy(dtype=float),
        truncated.loc[:, cols].to_numpy(dtype=float),
    )
    assert complete.loc[0, "speed_cell_sizes"] == 0
    assert complete.loc[0, "time_age"] == 0


def test_sequence_group_holdout_and_four_class_smoke():
    records = []
    labels = ["EarlyMitosis", "LateMitosis", "CellDeath", "Multipolar"]
    for index in range(10):
        for label_id, name in enumerate(labels):
            for frame in range(1, 7):
                records.append(dict(
                    sequence=f"MI{index:02d}", track_id=label_id, frame=frame,
                    label=name, xmin=10 + label_id*10 + frame,
                    ymin=label_id*10, width=8 + label_id*2 + frame/4,
                    height=8+label_id*2,
                ))
    features = engineer_features(pd.DataFrame(records))
    result = evaluate(features, n_splits=5, bootstrap=20)
    assert result["n_sequences"] == 10
    assert result["n_tracks"] == 40
    assert result["rows"] == 240
    assert len(result["cluster_bootstrap_delta_macro_f1_95pct"]) == 2
    assert set(result["models"]) == {"static_bbox", "static_plus_past_temporal"}
