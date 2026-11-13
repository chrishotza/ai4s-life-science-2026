import pandas as pd

from ai4s_tracking import link_metrics


def test_empty_prediction_against_nonempty_truth_does_not_score_precision_as_perfect():
    truth = pd.DataFrame({"source_id": [0], "target_id": [1]})
    predicted = pd.DataFrame(columns=["source_id", "target_id"])

    metrics = link_metrics(predicted, truth)

    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["f1"] == 0.0


def test_both_empty_sets_are_perfect():
    empty = pd.DataFrame(columns=["source_id", "target_id"])
    metrics = link_metrics(empty, empty)
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0


def test_link_metrics_rejects_fractional_id_instead_of_fabricating_exact_match():
    import pytest

    truth = pd.DataFrame({"source_id": [1], "target_id": [2]})
    invented = pd.DataFrame({"source_id": [1.9], "target_id": [2.0]})
    with pytest.raises(ValueError, match="integer identifiers"):
        link_metrics(invented, truth)


def test_link_metrics_rejects_boolean_nonfinite_and_unrepresentable_ids():
    import pytest

    empty = pd.DataFrame(columns=["source_id", "target_id"])
    for id_value in (True, False, float("nan"), float("inf"), -float("inf"),
                     2**53, "1"):
        edges = pd.DataFrame({"source_id": [id_value], "target_id": [2]})
        with pytest.raises(ValueError, match="integer identifiers"):
            link_metrics(edges, empty)


def test_tracking_error_profile_rejects_fractional_edge_identifiers():
    import pytest
    from ai4s_tracking import tracking_error_profile

    nodes = pd.DataFrame({
        "node_id": [0, 1], "track_id": [0, 0], "t": [0, 1]
    })
    truth = pd.DataFrame({"source_id": [0], "target_id": [1]})
    predicted = pd.DataFrame({"source_id": [0.9], "target_id": [1]})
    with pytest.raises(ValueError, match="integer identifiers"):
        tracking_error_profile(nodes, nodes.copy(), truth, predicted)


def test_valid_integer_valued_float_edges_keep_previous_metrics():
    truth = pd.DataFrame({"source_id": [0, 2], "target_id": [1, 3]})
    as_float = truth.astype(float)
    assert link_metrics(as_float, truth)["f1"] == 1.0
