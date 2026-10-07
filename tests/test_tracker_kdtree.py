import pandas as pd

from ai4s_tracking import TrackingConfig, track_detections


def test_kdtree_mutual_nn_matches_exact_mutual_nn_on_non_tied_geometry():
    detections = pd.DataFrame(
        [
            (0, 0.0, 0.0, 0.0),
            (0, 0.0, 10.0, 0.0),
            (1, 0.0, 0.5, 0.0),
            (1, 0.0, 10.6, 0.0),
            (2, 0.0, 1.0, 0.0),
            (2, 0.0, 11.2, 0.0),
        ],
        columns=["t", "z", "y", "x"],
    )

    exact_nodes, exact_edges = track_detections(
        detections,
        TrackingConfig(max_distance_um=2.0, method="mutual_nn"),
    )
    tree_nodes, tree_edges = track_detections(
        detections,
        TrackingConfig(max_distance_um=2.0, method="mutual_nn_tree"),
    )

    assert exact_nodes[["t", "track_id"]].equals(tree_nodes[["t", "track_id"]])
    assert exact_edges[["source_id", "target_id"]].equals(
        tree_edges[["source_id", "target_id"]]
    )
