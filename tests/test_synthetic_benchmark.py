from ai4s_tracking import TrackingConfig, link_metrics, track_detections
from ai4s_tracking.synthetic import SyntheticConfig, generate_synthetic


def test_synthetic_benchmark_recovers_clean_links():
    truth, truth_edges = generate_synthetic(
        SyntheticConfig(frames=10, cells=5, step_um=0.2, seed=11)
    )
    detections = truth[["t", "z", "y", "x"]]

    nodes, predicted_edges = track_detections(
        detections,
        TrackingConfig(max_distance_um=2.0),
    )
    predicted_edges = predicted_edges[["source_id", "target_id"]]
    metrics = link_metrics(predicted_edges, truth_edges)

    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert nodes["track_id"].nunique() == 5
