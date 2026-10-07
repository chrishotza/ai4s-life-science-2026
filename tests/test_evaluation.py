import pandas as pd

from ai4s_tracking import link_metrics


def test_link_metrics_reports_exact_match():
    truth = pd.DataFrame(
        {"source_id": [0, 1], "target_id": [2, 3]}
    )
    predicted = pd.DataFrame(
        {"source_id": [0, 1], "target_id": [2, 3]}
    )

    metrics = link_metrics(predicted, truth)

    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0


def test_link_metrics_penalizes_false_links():
    truth = pd.DataFrame({"source_id": [0], "target_id": [1]})
    predicted = pd.DataFrame(
        {"source_id": [0, 2], "target_id": [1, 3]}
    )

    metrics = link_metrics(predicted, truth)

    assert metrics["true_positive"] == 1.0
    assert metrics["false_positive"] == 1.0
    assert metrics["false_negative"] == 0.0
    assert metrics["precision"] == 0.5


def test_tracking_error_profile_detects_fragmentation():
    from ai4s_tracking import tracking_error_profile

    truth_nodes = pd.DataFrame(
        {
            "node_id": [0, 1, 2],
            "track_id": [0, 0, 0],
            "t": [0, 1, 2],
        }
    )
    predicted_nodes = truth_nodes.assign(track_id=[0, 0, 1])
    truth_edges = pd.DataFrame(
        {"source_id": [0, 1], "target_id": [1, 2]}
    )
    predicted_edges = pd.DataFrame(
        {"source_id": [0], "target_id": [1]}
    )

    profile = tracking_error_profile(
        truth_nodes,
        predicted_nodes,
        truth_edges,
        predicted_edges,
    )

    assert profile["fragmented_truth_tracks"] == 1.0
    assert profile["oversegmentation_events"] == 1.0
    assert profile["missed_links"] == 1.0
    assert profile["mean_track_purity"] == 1.0


def test_tracking_error_profile_detects_merge_and_cross_identity_link():
    from ai4s_tracking import tracking_error_profile

    truth_nodes = pd.DataFrame(
        {
            "node_id": [0, 1, 2, 3],
            "track_id": [0, 0, 1, 1],
            "t": [0, 1, 0, 1],
        }
    )
    predicted_nodes = truth_nodes.assign(track_id=[0, 0, 0, 0])
    truth_edges = pd.DataFrame(
        {"source_id": [0, 2], "target_id": [1, 3]}
    )
    predicted_edges = pd.DataFrame(
        {"source_id": [0, 1, 2], "target_id": [1, 2, 3]}
    )

    profile = tracking_error_profile(
        truth_nodes,
        predicted_nodes,
        truth_edges,
        predicted_edges,
    )

    assert profile["merged_predicted_tracks"] == 1.0
    assert profile["merge_events"] == 1.0
    assert profile["cross_identity_false_links"] == 1.0
    assert profile["identity_switches"] == 1.0


def test_tracking_error_profile_reports_gap_links():
    from ai4s_tracking import tracking_error_profile

    truth_nodes = pd.DataFrame(
        {
            "node_id": [0, 1],
            "track_id": [0, 0],
            "t": [0, 2],
        }
    )
    predicted_nodes = truth_nodes.copy()
    edges = pd.DataFrame(
        {
            "source_id": [0],
            "target_id": [1],
        }
    )

    profile = tracking_error_profile(
        truth_nodes,
        predicted_nodes,
        pd.DataFrame(columns=["source_id", "target_id"]),
        edges,
    )

    assert profile["gap_link_count"] == 1.0
    assert profile["gap_link_correct_identity"] == 1.0
