from __future__ import annotations

import pandas as pd


def greedy_track_overlap(
    truth_nodes: pd.DataFrame,
    predicted_nodes: pd.DataFrame,
) -> list[tuple[int, int, int, float]]:
    """Match predicted tracks to reference tracks by maximum shared node count.

    Node IDs are assumed to be aligned between the two node tables.
    """
    required = {"node_id", "track_id", "t"}
    if not required.issubset(truth_nodes.columns):
        raise ValueError("truth_nodes missing node alignment columns")
    if not required.issubset(predicted_nodes.columns):
        raise ValueError("predicted_nodes missing node alignment columns")

    truth = truth_nodes[["node_id", "track_id", "t"]].copy()
    pred = predicted_nodes[["node_id", "track_id", "t"]].copy()

    aligned = truth.merge(pred, on=["node_id", "t"], suffixes=("_truth", "_pred"))
    overlap = (
        aligned.groupby(["track_id_truth", "track_id_pred"])
        .size()
        .reset_index(name="overlap")
        .sort_values(
            ["overlap", "track_id_truth", "track_id_pred"],
            ascending=[False, True, True],
        )
    )

    if overlap.empty:
        return []

    truth_sizes = truth.groupby("track_id").size().to_dict()
    used_truth: set[int] = set()
    used_pred: set[int] = set()
    matches: list[tuple[int, int, int, float]] = []

    for row in overlap.itertuples(index=False):
        truth_id = int(row.track_id_truth)
        pred_id = int(row.track_id_pred)
        if truth_id in used_truth or pred_id in used_pred:
            continue

        shared = int(row.overlap)
        coverage = shared / max(1, int(truth_sizes[truth_id]))
        matches.append((truth_id, pred_id, shared, coverage))
        used_truth.add(truth_id)
        used_pred.add(pred_id)

    return matches
