import pandas as pd
import pytest

from ai4s_tracking import TrackingConfig, track_detections


def test_hungarian_produces_one_to_one_links():
    detections = pd.DataFrame(
        [
            {"t": 0, "z": 0.0, "y": 0.0, "x": 0.0},
            {"t": 0, "z": 0.0, "y": 0.0, "x": 2.0},
            {"t": 1, "z": 0.0, "y": 0.0, "x": 0.9},
            {"t": 1, "z": 0.0, "y": 0.0, "x": 1.1},
        ]
    )

    nodes, edges = track_detections(
        detections,
        TrackingConfig(max_distance_um=2.0, method="hungarian"),
    )

    assert len(edges) == 2
    assert edges["target_id"].nunique() == 2
    assert nodes["track_id"].nunique() == 2


def test_velocity_hungarian_follows_constant_velocity():
    detections = pd.DataFrame(
        [
            {"t": 0, "z": 0.0, "y": 0.0, "x": 0.0},
            {"t": 0, "z": 0.0, "y": 0.0, "x": 10.0},
            {"t": 1, "z": 0.0, "y": 0.0, "x": 1.0},
            {"t": 1, "z": 0.0, "y": 0.0, "x": 9.0},
            {"t": 2, "z": 0.0, "y": 0.0, "x": 2.0},
            {"t": 2, "z": 0.0, "y": 0.0, "x": 8.0},
        ]
    )

    nodes, edges = track_detections(
        detections,
        TrackingConfig(
            max_distance_um=2.0,
            method="velocity_hungarian",
        ),
    )

    assert len(edges) == 4
    assert nodes["track_id"].nunique() == 2


def test_voxel_scaling_is_used_for_physical_distance():
    detections = pd.DataFrame(
        [
            {"t": 0, "z": 0.0, "y": 0.0, "x": 0.0},
            {"t": 1, "z": 0.0, "y": 0.0, "x": 10.0},
        ]
    )

    nodes, edges = track_detections(
        detections,
        TrackingConfig(
            max_distance_um=2.0,
            method="hungarian",
            voxel_size_um=(1.0, 0.1, 0.1),
        ),
    )

    assert len(edges) == 1
    assert float(edges.iloc[0]["distance_um"]) == 1.0
    assert nodes["track_id"].nunique() == 1


def test_mutual_rescue_recovers_unclaimed_assignment():
    detections = pd.DataFrame(
        [
            {"t": 0, "z": 0.0, "y": 0.0, "x": 0.0},
            {"t": 0, "z": 0.0, "y": 0.0, "x": 0.5},
            {"t": 1, "z": 0.0, "y": 0.0, "x": 0.1},
            {"t": 1, "z": 0.0, "y": 0.0, "x": 2.0},
        ]
    )

    _, mutual_edges = track_detections(
        detections,
        TrackingConfig(max_distance_um=2.0, method="mutual_nn"),
    )
    _, rescue_edges = track_detections(
        detections,
        TrackingConfig(max_distance_um=2.0, method="mutual_rescue"),
    )

    assert len(mutual_edges) == 1
    assert len(rescue_edges) == 2
    assert rescue_edges["target_id"].nunique() == 2



def test_hungarian_maximizes_valid_links_before_minimizing_total_distance():
    # Direct assignment costs 0 + sqrt(2), but one edge violates the gate.
    # The crossed assignment provides two admissible links, each at distance 1.
    detections = pd.DataFrame(
        [
            (0, 0.0, 0.0, 0.0),
            (0, 0.0, 1.0, 0.0),
            (1, 0.0, 0.0, 0.0),
            (1, 0.0, 0.0, 1.0),
        ],
        columns=["t", "z", "y", "x"],
    )
    _, edges = track_detections(
        detections,
        TrackingConfig(max_distance_um=1.0, method="hungarian"),
    )

    assert len(edges) == 2
    assert sorted(edges["distance_um"].tolist()) == pytest.approx([1.0, 1.0])


def test_default_trackers_do_not_link_across_a_missing_frame():
    detections = pd.DataFrame(
        [(0, 0.0, 0.0, 0.0), (2, 0.0, 0.5, 0.0)],
        columns=["t", "z", "y", "x"],
    )
    for method in (
        "mutual_nn",
        "mutual_nn_tree",
        "mutual_rescue",
        "hungarian",
        "velocity_hungarian",
    ):
        nodes, edges = track_detections(
            detections,
            TrackingConfig(max_distance_um=2.0, method=method),
        )
        assert nodes["track_id"].nunique() == 2, method
        assert edges.empty, method


@pytest.mark.parametrize(
    "config_kwargs",
    [
        {"max_distance_um": float("nan")},
        {"max_distance_um": float("inf")},
        {"voxel_size_um": (1.0, float("nan"), 1.0)},
        {"voxel_size_um": (1.0, float("inf"), 1.0)},
        {"max_frame_gap": 1.5},
    ],
)
def test_tracking_config_rejects_nonfinite_or_invalid_geometry(config_kwargs):
    with pytest.raises(ValueError):
        TrackingConfig(**config_kwargs)
