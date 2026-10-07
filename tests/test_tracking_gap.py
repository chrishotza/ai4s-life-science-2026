import pandas as pd

from ai4s_tracking import TrackingConfig, track_detections


def test_gap_hungarian_can_bridge_one_missing_frame():
    detections = pd.DataFrame(
        [
            (0, 0.0, 0.0, 0.0),
            (2, 0.0, 1.5, 0.0),
        ],
        columns=["t", "z", "y", "x"],
    )

    nodes, edges = track_detections(
        detections,
        TrackingConfig(
            max_distance_um=2.0,
            method="gap_hungarian",
            max_frame_gap=2,
        ),
    )

    assert nodes["track_id"].nunique() == 1
    assert len(edges) == 1
    assert int(edges.iloc[0]["frame_gap"]) == 2
    assert bool(edges.iloc[0]["link_confidence"] < 1.0)


def test_gap_hungarian_default_constraint_rejects_gap_setting_on_other_methods():
    import pytest

    with pytest.raises(ValueError, match="gap_hungarian"):
        TrackingConfig(
            method="mutual_nn",
            max_frame_gap=2,
        )
