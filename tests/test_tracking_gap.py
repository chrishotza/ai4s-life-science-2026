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

def test_gap_hungarian_does_not_bridge_beyond_configured_gap():
    detections = pd.DataFrame(
        [
            (0, 0.0, 0.0, 0.0),
            (3, 0.0, 1.5, 0.0),
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

    assert nodes["track_id"].nunique() == 2
    assert edges.empty



def test_gap_hungarian_maximizes_valid_links_when_tracks_have_different_gaps():
    # At t=2 the recent track can link to either detection, while the older
    # track can only reach x=0.1. Unconstrained assignment prefers the invalid
    # older-track -> x=0.9 pair and then drops it, losing a valid second link.
    detections = pd.DataFrame(
        [
            (0, 0.0, 0.0, -1.9),  # older track
            (0, 0.0, 0.0, 0.0),   # recent track
            (1, 0.0, 0.0, 0.1),   # only the recent track is observed
            (2, 0.0, 0.0, 0.1),
            (2, 0.0, 0.0, 0.9),
        ],
        columns=["t", "z", "y", "x"],
    )

    nodes, edges = track_detections(
        detections,
        TrackingConfig(
            max_distance_um=1.0,
            method="gap_hungarian",
            max_frame_gap=2,
        ),
    )

    assert len(edges) == 3
    assert nodes.loc[nodes["t"].eq(2), "track_id"].nunique() == 2
    assert set(edges["frame_gap"].astype(int)) == {1, 2}

    older_track = int(nodes.loc[nodes["t"].eq(0) & nodes["x"].eq(-1.9), "track_id"].iloc[0])
    recent_track = int(nodes.loc[nodes["t"].eq(1) & nodes["x"].eq(0.1), "track_id"].iloc[0])
    t2 = nodes.loc[nodes["t"].eq(2)].sort_values("x")
    assert t2["track_id"].astype(int).tolist() == [older_track, recent_track]
