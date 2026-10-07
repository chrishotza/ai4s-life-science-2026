import pandas as pd

from ai4s_tracking import TrackingConfig, track_detections


def test_tracking_edges_include_normalized_link_confidence():
    detections = pd.DataFrame(
        [
            (0, 0.0, 0.0, 0.0),
            (1, 0.0, 1.0, 0.0),
            (2, 0.0, 2.0, 0.0),
        ],
        columns=["t", "z", "y", "x"],
    )

    _, edges = track_detections(
        detections,
        TrackingConfig(max_distance_um=2.0, method="mutual_nn"),
    )

    assert "link_confidence" in edges.columns
    assert (edges["link_confidence"] >= 0.0).all()
    assert (edges["link_confidence"] <= 1.0).all()
    assert edges["link_confidence"].iloc[0] == 0.5
