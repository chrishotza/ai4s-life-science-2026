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
