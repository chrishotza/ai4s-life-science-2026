from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from ai4s_core import scale_coordinates

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai4s_io import DIC_C2DH_HELA_VOXEL_SIZE_UM, ensure_ctc_dataset, load_ctc_tracking
from ai4s_phenotype import analyze
from ai4s_tracking import TrackingConfig, track_detections


DATA_URL = "https://data.celltrackingchallenge.net/training-datasets/DIC-C2DH-HeLa.zip"
VOXEL_SIZE_UM = DIC_C2DH_HELA_VOXEL_SIZE_UM
FEATURES = [
    "duration",
    "observations",
    "displacement",
    "path_length",
    "mean_speed",
    "directional_persistence",
]


def match_tracks(
    truth_nodes: pd.DataFrame,
    predicted_nodes: pd.DataFrame,
) -> list[tuple[int, int, int, float]]:
    gt = truth_nodes[["node_id", "track_id", "t"]].copy()
    pred = predicted_nodes[["node_id", "track_id", "t"]].copy()

    aligned = gt.merge(pred, on=["node_id", "t"], suffixes=("_gt", "_pred"))
    overlap = (
        aligned.groupby(["track_id_gt", "track_id_pred"])
        .size()
        .reset_index(name="overlap")
    )
    if overlap.empty:
        return []

    gt_sizes = gt.groupby("track_id").size().to_dict()
    overlap = overlap.sort_values("overlap", ascending=False)

    used_gt: set[int] = set()
    used_pred: set[int] = set()
    matches = []

    for row in overlap.itertuples(index=False):
        gt_id = int(row.track_id_gt)
        pred_id = int(row.track_id_pred)
        if gt_id in used_gt or pred_id in used_pred:
            continue
        shared = int(row.overlap)
        coverage = shared / max(1, int(gt_sizes[gt_id]))
        matches.append((gt_id, pred_id, shared, coverage))
        used_gt.add(gt_id)
        used_pred.add(pred_id)

    return matches


def compare_features(
    truth: pd.DataFrame,
    predicted: pd.DataFrame,
    matches: list[tuple[int, int, int, float]],
) -> dict[str, float]:
    gt_by_id = truth.set_index("track_id")
    pred_by_id = predicted.set_index("track_id")

    rows = []
    for gt_id, pred_id, shared, coverage in matches:
        if gt_id not in gt_by_id.index or pred_id not in pred_by_id.index:
            continue
        g = gt_by_id.loc[gt_id]
        p = pred_by_id.loc[pred_id]
        row = {
            "coverage": coverage,
            "shared": shared,
        }
        for feature in FEATURES:
            row[f"{feature}_abs_error"] = abs(float(p[feature]) - float(g[feature]))
        rows.append(row)

    if not rows:
        return {"matched_tracks": 0.0, "mean_coverage": 0.0}

    frame = pd.DataFrame(rows)
    result: dict[str, float] = {
        "matched_tracks": float(len(frame)),
        "mean_coverage": float(frame["coverage"].mean()),
        "median_coverage": float(frame["coverage"].median()),
    }
    for feature in FEATURES:
        result[f"{feature}_mae"] = float(frame[f"{feature}_abs_error"].mean())
    return result


def main() -> None:
    dataset_root = ensure_ctc_dataset(ROOT / ".benchmark_cache")

    sequence_results = []

    for sequence in ("01", "02"):
        truth_dir = dataset_root / f"{sequence}_GT" / "TRA"
        truth_nodes, truth_edges, _ = load_ctc_tracking(truth_dir)

        truth_for_matching = (
            truth_nodes[["t", "z", "y", "x", "track_id"]]
            .sort_values(["t", "z", "y", "x"])
            .reset_index(drop=True)
        )
        truth_for_matching["node_id"] = np.arange(len(truth_for_matching))

        predicted_nodes, predicted_edges = track_detections(
            truth_for_matching[["t", "z", "y", "x"]],
            TrackingConfig(
                max_distance_um=8.0,
                method="mutual_nn",
                voxel_size_um=VOXEL_SIZE_UM,
            ),
        )

        truth_phenotypes = analyze(
            scale_coordinates(truth_nodes, VOXEL_SIZE_UM),
            truth_edges,
        )
        predicted_phenotypes = analyze(
            scale_coordinates(predicted_nodes, VOXEL_SIZE_UM),
            predicted_edges,
        )

        matches = match_tracks(truth_for_matching, predicted_nodes)
        metrics = compare_features(
            truth_phenotypes,
            predicted_phenotypes,
            matches,
        )
        metrics.update(
            {
                "dataset": "DIC-C2DH-HeLa",
                "sequence": sequence,
                "truth_tracks": int(truth_phenotypes["track_id"].nunique()),
                "predicted_tracks": int(predicted_phenotypes["track_id"].nunique()),
            }
        )
        sequence_results.append(metrics)

    numeric = pd.DataFrame(sequence_results).select_dtypes(include=[np.number])
    aggregate = {k: float(numeric[k].mean()) for k in numeric.columns}

    output = {
        "benchmark": {
            "dataset": "DIC-C2DH-HeLa",
            "sequences": ["01", "02"],
            "voxel_size_um": VOXEL_SIZE_UM,
            "tracking_method": "mutual_nn",
            "max_distance_um": 8.0,
            "input": "CTC reference centroids",
        },
        "results": sequence_results,
        "aggregate": aggregate,
    }

    (ROOT / "ctc_phenotype_results.json").write_text(
        json.dumps(output, indent=2)
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
