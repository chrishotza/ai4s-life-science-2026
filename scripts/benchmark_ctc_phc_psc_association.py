from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai4s_core import runtime_metadata
from ai4s_io import (
    PHC_C2DL_PSC_VOXEL_SIZE_UM,
    ensure_ctc_phc_psc_dataset,
    load_ctc_tracking,
)
from ai4s_tracking import TrackingConfig, link_metrics, track_detections

DISTANCES_UM = (1.6, 3.2, 4.8, 6.4, 8.0, 9.6, 12.8, 16.0)
SEQUENCES = ("01", "02")
METHOD = "mutual_nn"


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


def evaluate_sequence(dataset_root: Path, sequence: str) -> list[dict[str, object]]:
    truth_dir = dataset_root / f"{sequence}_GT" / "TRA"
    truth_nodes, _, metadata = load_ctc_tracking(truth_dir)
    detections = (
        truth_nodes[["t", "z", "y", "x", "track_id"]]
        .sort_values(["t", "z", "y", "x"])
        .reset_index(drop=True)
    )
    truth_edges: set[tuple[int, int]] | None = None
    rows: list[dict[str, object]] = []

    for distance_um in DISTANCES_UM:
        predicted_nodes, predicted_edges = track_detections(
            detections[["t", "z", "y", "x"]],
            TrackingConfig(
                max_distance_um=distance_um,
                method=METHOD,
                voxel_size_um=PHC_C2DL_PSC_VOXEL_SIZE_UM,
            ),
        )
        if truth_edges is None:
            truth_edges, _ = link_sets(detections, pd.DataFrame(columns=["source_id", "target_id"]))
        _, predicted_edge_set = link_sets(detections, predicted_edges)
        metrics = score(truth_edges, predicted_edge_set)
        rows.append(
            {
                "dataset": "PhC-C2DL-PSC",
                "sequence": sequence,
                "method": METHOD,
                "max_distance_um": distance_um,
                "voxel_size_um": PHC_C2DL_PSC_VOXEL_SIZE_UM,
                "detections": int(len(detections)),
                "ground_truth_tracks": int(metadata["track_id"].nunique()),
                "predicted_tracks": int(predicted_nodes["track_id"].nunique()),
                **metrics,
            }
        )
    return rows


def select_gate(rows: list[dict[str, object]], sequence: str) -> float:
    candidates = [row for row in rows if row["sequence"] == sequence]
    best = max(
        candidates,
        key=lambda row: (
            float(row["f1"]),
            float(row["precision"]),
            float(row["recall"]),
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
    for train_sequence, test_sequence in (("01", "02"), ("02", "01")):
        selected_gate = select_gate(rows, train_sequence)
        test_row = next(
            row for row in rows
            if row["sequence"] == test_sequence
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

    fixed_gate_rows = [
        row for row in rows if float(row["max_distance_um"]) == 8.0
    ]
    fixed_gate = {
        "mean_precision": float(pd.DataFrame(fixed_gate_rows)["precision"].mean()),
        "mean_recall": float(pd.DataFrame(fixed_gate_rows)["recall"].mean()),
        "mean_f1": float(pd.DataFrame(fixed_gate_rows)["f1"].mean()),
    }
    holdout_frame = pd.DataFrame(holdout)
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
            "method": METHOD,
            "distance_sweep_um": list(DISTANCES_UM),
            "selection": "cross-sequence gate selection; fit/select on one sequence, report on the other",
            "fixed_gate_control": "canonical 8.0 µm gate reported without per-sequence tuning",
            "claim_boundary": (
                "Temporal association generalization only. This benchmark does not evaluate "
                "image segmentation, autonomous lineage detection, or biological phenotype classification."
            ),
        },
        "candidate_results": rows,
        "fixed_8um_control": fixed_gate,
        "cross_sequence_holdout": holdout,
        "holdout_aggregate": {
            "mean_precision": float(holdout_frame["precision"].mean()),
            "mean_recall": float(holdout_frame["recall"].mean()),
            "mean_f1": float(holdout_frame["f1"].mean()),
        },
    }
    (ROOT / "ctc_phc_psc_association_results.json").write_text(json.dumps(output, indent=2))
    (ROOT / "ctc_phc_psc_association_summary.csv").write_text(
        pd.DataFrame(rows).to_csv(index=False)
    )
    print(json.dumps(output["fixed_8um_control"], indent=2))
    print(json.dumps(output["cross_sequence_holdout"], indent=2))
    print(json.dumps(output["holdout_aggregate"], indent=2))


if __name__ == "__main__":
    main()
