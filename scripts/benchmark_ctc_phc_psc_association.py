from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai4s_core import runtime_metadata
from ai4s_io import (
    PHC_C2DL_PSC_VOXEL_SIZE_UM,
    ensure_ctc_phc_psc_dataset,
    load_ctc_tracking,
)
from ai4s_tracking import link_metrics
from ai4s_tracking.tracker import _assign_pairs, _hungarian_pairs

DISTANCES_UM = (1.6, 3.2, 4.8, 6.4, 8.0, 9.6, 12.8, 16.0)
SEQUENCES = ("01", "02")
METHODS = ("mutual_nn", "mutual_rescue", "hungarian", "velocity_hungarian")


def link_sets(
    truth: pd.DataFrame,
    predicted_edges: pd.DataFrame,
) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
    ordered = truth.sort_values(["t", "z", "y", "x"]).reset_index(drop=True)
    truth_edges: set[tuple[int, int]] = set()

    for _, group in ordered.groupby("track_id", sort=False):
        indexes = sorted(group.index.to_list(), key=lambda i: int(ordered.loc[i, "t"]))
        for a, b in zip(indexes, indexes[1:]):
            if int(ordered.loc[b, "t"]) == int(ordered.loc[a, "t"]) + 1:
                truth_edges.add((int(a), int(b)))

    pred_edges = {
        (int(row.source_id), int(row.target_id))
        for row in predicted_edges.itertuples(index=False)
    }
    return truth_edges, pred_edges


def score(
    truth: set[tuple[int, int]],
    predicted: set[tuple[int, int]],
) -> dict[str, float]:
    truth_frame = pd.DataFrame(list(truth), columns=["source_id", "target_id"])
    pred_frame = pd.DataFrame(list(predicted), columns=["source_id", "target_id"])
    metrics = link_metrics(pred_frame, truth_frame)
    return {
        "true_links": float(metrics["true_links"]),
        "predicted_links": float(metrics["predicted_links"]),
        "tp": float(metrics["true_positive"]),
        "fp": float(metrics["false_positive"]),
        "fn": float(metrics["false_negative"]),
        "precision": float(metrics["precision"]),
        "recall": float(metrics["recall"]),
        "f1": float(metrics["f1"]),
    }


def fast_track_detections(
    detections: pd.DataFrame,
    max_distance_um: float,
    method: str = "mutual_nn",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fast benchmark path whose association methods are parity-tested with production."""
    if method not in METHODS:
        raise ValueError(f"unsupported benchmark association method: {method}")
    ordered = (
        detections.copy()
        .sort_values(["t", "z", "y", "x"])
        .reset_index(drop=True)
    )
    ordered["node_id"] = np.arange(len(ordered), dtype=np.int64)
    if ordered.empty:
        ordered["track_id"] = pd.Series(dtype="int64")
        return ordered, pd.DataFrame(
            columns=["source_id", "target_id", "distance_um", "link_confidence", "edge_type"]
        )

    scale = np.asarray(PHC_C2DL_PSC_VOXEL_SIZE_UM, dtype=float)
    positions = ordered[["z", "y", "x"]].to_numpy(dtype=float) * scale
    track_ids = np.full(len(ordered), -1, dtype=np.int64)
    edge_rows: list[tuple[int, int, float, float, str]] = []
    history: dict[int, list[tuple[int, np.ndarray]]] = {}
    next_track_id = 0
    previous_idx: np.ndarray | None = None

    for frame_t, frame in ordered.groupby("t", sort=True):
        current_idx = frame.index.to_numpy(dtype=np.int64)
        if previous_idx is None:
            for node_idx in current_idx:
                track_ids[node_idx] = next_track_id
                history[next_track_id] = [(int(frame_t), positions[node_idx])]
                next_track_id += 1
            previous_idx = current_idx
            continue

        # Production orders active source observations by track ID.
        previous_idx = previous_idx[np.argsort(track_ids[previous_idx], kind="stable")]
        previous_positions = positions[previous_idx]
        current_positions = positions[current_idx]

        if method == "velocity_hungarian":
            predicted_positions = []
            previous_track_ids = track_ids[previous_idx]
            for track_id in previous_track_ids:
                hist = history.get(int(track_id), [])
                if len(hist) >= 2:
                    t0, p0 = hist[-2]
                    t1, p1 = hist[-1]
                    dt = max(1, t1 - t0)
                    predicted_positions.append(
                        p1 + (p1 - p0) / dt * (int(frame_t) - t1)
                    )
                else:
                    predicted_positions.append(hist[-1][1])
            pairs = _hungarian_pairs(
                np.asarray(predicted_positions, dtype=float),
                current_positions,
                max_distance_um,
            )
        else:
            pairs = _assign_pairs(
                previous_positions,
                current_positions,
                max_distance_um,
                method,
            )

        matched_current: set[int] = set()
        for previous_position, current_position, distance in pairs:
            source_id = int(previous_idx[previous_position])
            target_id = int(current_idx[current_position])
            track_id = int(track_ids[source_id])
            track_ids[target_id] = track_id
            matched_current.add(current_position)
            confidence = max(0.0, 1.0 - distance / max_distance_um)
            edge_rows.append((source_id, target_id, distance, confidence, "link"))
            history.setdefault(track_id, []).append((int(frame_t), positions[target_id]))
            history[track_id] = history[track_id][-3:]

        for current_position, target_id in enumerate(current_idx):
            if current_position in matched_current:
                continue
            track_ids[target_id] = next_track_id
            history[next_track_id] = [(int(frame_t), positions[target_id])]
            next_track_id += 1
        previous_idx = current_idx

    ordered["track_id"] = track_ids
    edges = pd.DataFrame(
        edge_rows,
        columns=["source_id", "target_id", "distance_um", "link_confidence", "edge_type"],
    )
    if edges.empty:
        edges = edges.astype({
            "source_id": "int64",
            "target_id": "int64",
            "distance_um": "float64",
            "link_confidence": "float64",
            "edge_type": "object",
        })
    return ordered, edges


def fast_mutual_nn_track(
    detections: pd.DataFrame,
    max_distance_um: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Backwards-compatible MNN helper for identity-metric unit tests."""
    return fast_track_detections(detections, max_distance_um, method="mutual_nn")


def trajectory_identity_metrics(
    predicted_nodes: pd.DataFrame,
    reference_column: str = "reference_track_id",
) -> dict[str, float | int]:
    """Score preservation of annotated track identity using pairwise co-assignment."""
    if reference_column not in predicted_nodes or "track_id" not in predicted_nodes:
        raise ValueError("predicted nodes must include reference and predicted track IDs")
    if predicted_nodes.empty:
        raise ValueError("identity metrics require at least one annotated detection")

    contingency = pd.crosstab(
        predicted_nodes[reference_column].astype(int),
        predicted_nodes["track_id"].astype(int),
    ).to_numpy(dtype=np.int64)

    def choose_two(values: np.ndarray) -> int:
        return int(np.sum(values * (values - 1) // 2))

    true_positive_pairs = choose_two(contingency.ravel())
    predicted_positive_pairs = choose_two(contingency.sum(axis=0))
    reference_positive_pairs = choose_two(contingency.sum(axis=1))
    precision = (
        true_positive_pairs / predicted_positive_pairs
        if predicted_positive_pairs
        else 0.0
    )
    recall = (
        true_positive_pairs / reference_positive_pairs
        if reference_positive_pairs
        else 0.0
    )
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    predicted_track_count = int(contingency.shape[1])
    reference_track_count = int(contingency.shape[0])
    return {
        "identity_precision": float(precision),
        "identity_recall": float(recall),
        "identity_f1": float(f1),
        "track_count_ratio": float(predicted_track_count / max(1, reference_track_count)),
        "merged_predicted_tracks": int(np.sum(np.count_nonzero(contingency, axis=0) > 1)),
        "fragmented_reference_tracks": int(np.sum(np.count_nonzero(contingency, axis=1) > 1)),
    }


def evaluate_sequence(dataset_root: Path, sequence: str) -> list[dict[str, object]]:
    truth_dir = dataset_root / f"{sequence}_GT" / "TRA"
    truth_nodes, _, metadata = load_ctc_tracking(truth_dir)
    detections = (
        truth_nodes[["t", "z", "y", "x", "track_id"]]
        .rename(columns={"track_id": "reference_track_id"})
        .sort_values(["t", "z", "y", "x"])
        .reset_index(drop=True)
    )
    truth_edge_nodes = detections.rename(columns={"reference_track_id": "track_id"})
    truth_edges, _ = link_sets(
        truth_edge_nodes,
        pd.DataFrame(columns=["source_id", "target_id"]),
    )
    rows: list[dict[str, object]] = []

    for method in METHODS:
        for distance_um in DISTANCES_UM:
            predicted_nodes, predicted_edges = fast_track_detections(
                detections[["t", "z", "y", "x", "reference_track_id"]],
                max_distance_um=distance_um,
                method=method,
            )
            _, predicted_edge_set = link_sets(truth_edge_nodes, predicted_edges)
            edge_metrics = score(truth_edges, predicted_edge_set)
            identity_metrics = trajectory_identity_metrics(predicted_nodes)
            rows.append(
                {
                    "dataset": "PhC-C2DL-PSC",
                    "sequence": sequence,
                    "method": method,
                    "max_distance_um": distance_um,
                    "voxel_size_um": PHC_C2DL_PSC_VOXEL_SIZE_UM,
                    "detections": int(len(detections)),
                    "ground_truth_tracks": int(metadata["track_id"].nunique()),
                    "predicted_tracks": int(predicted_nodes["track_id"].nunique()),
                    **edge_metrics,
                    "edge_f1": float(edge_metrics["f1"]),
                    **identity_metrics,
                }
            )
            print(
                f"[ctc-cross-domain] sequence={sequence} method={method} "
                f"gate_um={distance_um} identity_f1={identity_metrics['identity_f1']:.4f} "
                f"edge_f1={edge_metrics['f1']:.4f}",
                flush=True,
            )
    return rows


def select_gate(rows: list[dict[str, object]], sequence: str, method: str) -> float:
    """Select gate by track-identity F1, using edge F1 as a secondary criterion."""
    candidates = [
        row for row in rows
        if row["sequence"] == sequence and row["method"] == method
    ]
    best = max(
        candidates,
        key=lambda row: (
            float(row["identity_f1"]),
            float(row["edge_f1"]),
            float(row["identity_precision"]),
        ),
    )
    return float(best["max_distance_um"])


def main() -> None:
    dataset_root = ensure_ctc_phc_psc_dataset(ROOT / ".benchmark_cache")
    rows: list[dict[str, object]] = []
    for sequence in SEQUENCES:
        print(f"[ctc-cross-domain] sequence={sequence}", flush=True)
        rows.extend(evaluate_sequence(dataset_root, sequence))

    holdout = []
    for method in METHODS:
        for train_sequence, test_sequence in (("01", "02"), ("02", "01")):
            selected_gate = select_gate(rows, train_sequence, method)
            test_row = next(
                row for row in rows
                if row["sequence"] == test_sequence
                and row["method"] == method
                and float(row["max_distance_um"]) == selected_gate
            )
            holdout.append(
                {
                    "train_sequence": train_sequence,
                    "test_sequence": test_sequence,
                    "selected_gate_um": selected_gate,
                    **test_row,
                }
            )

    fixed_frame = pd.DataFrame([
        row for row in rows if float(row["max_distance_um"]) == 8.0
    ])
    def aggregate_metrics(frame: pd.DataFrame) -> dict[str, float]:
        return {
            "mean_edge_precision": float(frame["precision"].mean()),
            "mean_edge_recall": float(frame["recall"].mean()),
            "mean_edge_f1": float(frame["edge_f1"].mean()),
            "mean_identity_precision": float(frame["identity_precision"].mean()),
            "mean_identity_recall": float(frame["identity_recall"].mean()),
            "mean_identity_f1": float(frame["identity_f1"].mean()),
            "mean_track_count_ratio": float(frame["track_count_ratio"].mean()),
        }

    fixed_by_method = {
        method: aggregate_metrics(fixed_frame[fixed_frame["method"] == method])
        for method in METHODS
    }
    fixed_gate = fixed_by_method["mutual_nn"]
    holdout_frame = pd.DataFrame(holdout)
    holdout_by_method = {
        method: aggregate_metrics(holdout_frame[holdout_frame["method"] == method])
        for method in METHODS
    }
    output = {
        "runtime": runtime_metadata(),
        "benchmark": {
            "dataset": "PhC-C2DL-PSC",
            "sequences": list(SEQUENCES),
            "microscopy": "phase contrast, pancreatic stem cells",
            "pixel_size_um": [1.6, 1.6],
            "time_step_min": 10,
            "voxel_size_um": PHC_C2DL_PSC_VOXEL_SIZE_UM,
            "input": "CTC reference track centroids as detections",
            "methods": list(METHODS),
            "distance_sweep_um": list(DISTANCES_UM),
            "selection": (
                "cross-sequence gate selection; maximize pairwise trajectory identity F1 on one "
                "sequence, use edge F1 as tie-breaker, report on the other"
            ),
            "fixed_gate_control": "canonical 8.0 µm gate reported without per-sequence tuning",
            "claim_boundary": (
                "Temporal association generalization only. This benchmark does not evaluate "
                "image segmentation, autonomous lineage detection, or biological phenotype classification."
            ),
        },
        "candidate_results": rows,
        "fixed_8um_control": fixed_gate,
        "fixed_8um_control_by_method": fixed_by_method,
        "cross_sequence_holdout": holdout,
        "holdout_aggregate_by_method": holdout_by_method,
    }
    (ROOT / "ctc_phc_psc_association_results.json").write_text(json.dumps(output, indent=2))
    (ROOT / "ctc_phc_psc_association_summary.csv").write_text(
        pd.DataFrame(rows).to_csv(index=False)
    )
    print(json.dumps(output["fixed_8um_control_by_method"], indent=2))
    print(json.dumps(output["cross_sequence_holdout"], indent=2))
    print(json.dumps(output["holdout_aggregate_by_method"], indent=2))


if __name__ == "__main__":
    main()
