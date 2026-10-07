from __future__ import annotations

import pandas as pd


def _edge_set(edges: pd.DataFrame) -> set[tuple[int, int]]:
    required = {"source_id", "target_id"}
    if not required.issubset(edges.columns):
        raise ValueError("edges must contain source_id and target_id")
    return {
        (int(source_id), int(target_id))
        for source_id, target_id in edges[["source_id", "target_id"]].to_numpy()
    }


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



def tracking_error_profile(
    truth_nodes: pd.DataFrame,
    predicted_nodes: pd.DataFrame,
    true_edges: pd.DataFrame,
    predicted_edges: pd.DataFrame,
) -> dict[str, float]:
    """Return deterministic temporal-tracking error diagnostics.

    Truth and predicted node tables must share the same node_id space. The
    reference track identity is taken from truth_nodes while predicted_nodes
    supplies the inferred track identity.
    """
    required_nodes = {"node_id", "track_id", "t"}
    for name, frame in (("truth_nodes", truth_nodes), ("predicted_nodes", predicted_nodes)):
        if not required_nodes.issubset(frame.columns):
            raise ValueError(f"{name} must contain node_id, track_id and t")
        if frame["node_id"].duplicated().any():
            raise ValueError(f"{name} contains duplicate node_id values")

    truth = truth_nodes.set_index("node_id")[["track_id", "t"]]
    pred = predicted_nodes.set_index("node_id")[["track_id", "t"]]
    if set(truth.index) != set(pred.index):
        raise ValueError("truth_nodes and predicted_nodes must share the same node_id set")

    truth_edge_set = _edge_set(true_edges)
    pred_edge_set = _edge_set(predicted_edges)
    false_positive_edges = pred_edge_set - truth_edge_set
    false_negative_edges = truth_edge_set - pred_edge_set

    identity_switches = 0
    ordered = predicted_nodes.sort_values(["track_id", "t", "node_id"])
    for _, group in ordered.groupby("track_id", sort=False):
        labels = truth.loc[group["node_id"], "track_id"].to_numpy()
        if len(labels) > 1:
            identity_switches += int((labels[1:] != labels[:-1]).sum())

    predicted_for_truth = (
        predicted_nodes.set_index("node_id")["track_id"]
        .reindex(truth.index)
        .groupby(truth["track_id"])
        .nunique()
    )
    truth_fragmented = int((predicted_for_truth > 1).sum())
    oversegmentation_events = int(predicted_for_truth.clip(lower=1).sub(1).sum())

    truth_for_predicted = (
        truth_nodes.set_index("node_id")["track_id"]
        .reindex(pred.index)
        .groupby(pred["track_id"])
        .nunique()
    )
    predicted_merged = int((truth_for_predicted > 1).sum())
    merge_events = int(truth_for_predicted.clip(lower=1).sub(1).sum())

    purities: list[float] = []
    for _, group in predicted_nodes.groupby("track_id", sort=False):
        labels = truth.loc[group["node_id"], "track_id"]
        majority = int(labels.value_counts().iloc[0])
        purities.append(majority / max(1, len(labels)))

    cross_identity_false_links = 0
    temporal_invalid_false_links = 0
    gap_link_count = 0
    gap_link_correct_identity = 0
    for source_id, target_id in pred_edge_set:
        source_t = int(pred.loc[source_id, "t"])
        target_t = int(pred.loc[target_id, "t"])
        frame_gap = target_t - source_t
        correct_identity = int(truth.loc[source_id, "track_id"]) == int(
            truth.loc[target_id, "track_id"]
        )
        if (source_id, target_id) in false_positive_edges:
            if not correct_identity:
                cross_identity_false_links += 1
            if frame_gap != 1:
                temporal_invalid_false_links += 1
        if frame_gap > 1:
            gap_link_count += 1
            if correct_identity:
                gap_link_correct_identity += 1

    return {
        "identity_switches": float(identity_switches),
        "fragmented_truth_tracks": float(truth_fragmented),
        "oversegmentation_events": float(oversegmentation_events),
        "merged_predicted_tracks": float(predicted_merged),
        "merge_events": float(merge_events),
        "mean_track_purity": float(sum(purities) / len(purities)) if purities else 1.0,
        "true_positive_links": float(len(truth_edge_set & pred_edge_set)),
        "false_positive_links": float(len(false_positive_edges)),
        "missed_links": float(len(false_negative_edges)),
        "false_link_rate": float(len(false_positive_edges) / max(1, len(pred_edge_set))),
        "missed_link_rate": float(len(false_negative_edges) / max(1, len(truth_edge_set))),
        "cross_identity_false_links": float(cross_identity_false_links),
        "temporal_invalid_false_links": float(temporal_invalid_false_links),
        "gap_link_count": float(gap_link_count),
        "gap_link_correct_identity": float(gap_link_correct_identity),
    }
