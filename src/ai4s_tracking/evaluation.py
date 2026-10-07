from __future__ import annotations

import pandas as pd


def link_metrics(predicted_edges: pd.DataFrame, true_edges: pd.DataFrame) -> dict[str, float]:
    """Score predicted consecutive-frame links against ground-truth links."""
    required = {"source_id", "target_id"}
    if not required.issubset(predicted_edges.columns):
        raise ValueError("predicted_edges must contain source_id and target_id")
    if not required.issubset(true_edges.columns):
        raise ValueError("true_edges must contain source_id and target_id")

    pred = set(map(tuple, predicted_edges[["source_id", "target_id"]].astype(int).to_numpy()))
    true = set(map(tuple, true_edges[["source_id", "target_id"]].astype(int).to_numpy()))

    tp = len(pred & true)
    fp = len(pred - true)
    fn = len(true - pred)

    predicted_count = tp + fp
    truth_count = tp + fn
    precision = tp / predicted_count if predicted_count else (1.0 if truth_count == 0 else 0.0)
    recall = tp / truth_count if truth_count else (1.0 if predicted_count == 0 else 0.0)
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 1.0
    )

    return {
        "true_links": float(len(true)),
        "predicted_links": float(len(pred)),
        "true_positive": float(tp),
        "false_positive": float(fp),
        "false_negative": float(fn),
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }
