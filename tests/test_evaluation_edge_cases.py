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
