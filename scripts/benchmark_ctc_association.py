from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai4s_io import load_ctc_tracking
from ai4s_tracking import TrackingConfig, track_detections


DATA_URL = "https://data.celltrackingchallenge.net/training-datasets/DIC-C2DH-HeLa.zip"
VOXEL_SIZE_UM = (1.0, 0.19, 0.19)
DISTANCES_UM = (0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0)
METHODS = ("mutual_nn", "hungarian", "velocity_hungarian")


def link_sets(
    truth: pd.DataFrame,
    predicted_edges: pd.DataFrame,
) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
    ordered = truth.sort_values(["t", "z", "y", "x"]).reset_index(drop=True)
    truth_edges: set[tuple[int, int]] = set()
    for _, group in ordered.groupby("track_id", sort=False):
        rows = group.index.to_list()
        rows.sort(key=lambda i: int(ordered.loc[i, "t"]))
        for a, b in zip(rows, rows[1:]):
            if int(ordered.loc[b, "t"]) == int(ordered.loc[a, "t"]) + 1:
                truth_edges.add((int(a), int(b)))

    pred_edges = {
        (int(row.source_id), int(row.target_id))
        for row in predicted_edges.itertuples(index=False)
    }
    return truth_edges, pred_edges


def score(
    truth: set[tuple[int, int]],
    pred: set[tuple[int, int]],
) -> dict[str, float]:
    tp = len(truth & pred)
    fp = len(pred - truth)
    fn = len(truth - pred)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_links": len(truth),
        "predicted_links": len(pred),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def main() -> None:
    work = ROOT / ".benchmark_cache"
    work.mkdir(exist_ok=True)
    archive = work / "DIC-C2DH-HeLa.zip"

    if not archive.exists():
        print(f"Downloading {DATA_URL}", flush=True)
        urlretrieve(DATA_URL, archive)

    extract = work / "dataset"
    dataset_root = extract / "DIC-C2DH-HeLa"
    if not dataset_root.exists():
        extract.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(extract)

    all_results: list[dict[str, object]] = []

    for sequence in ("01", "02"):
        truth_dir = dataset_root / f"{sequence}_GT" / "TRA"
        truth_nodes, _, metadata = load_ctc_tracking(truth_dir)

        detections = (
            truth_nodes[["t", "z", "y", "x", "track_id"]]
            .sort_values(["t", "z", "y", "x"])
            .reset_index(drop=True)
        )

        for method in METHODS:
            for max_distance_um in DISTANCES_UM:
                predicted, predicted_edges = track_detections(
                    detections[["t", "z", "y", "x"]],
                    TrackingConfig(
                        max_distance_um=max_distance_um,
                        method=method,
                        voxel_size_um=VOXEL_SIZE_UM,
                    ),
                )
                truth_edges, pred_edges = link_sets(detections, predicted_edges)
                metrics = score(truth_edges, pred_edges)

                all_results.append(
                    {
                        "dataset": "DIC-C2DH-HeLa",
                        "sequence": sequence,
                        "method": method,
                        "max_distance_um": max_distance_um,
                        "voxel_size_um": VOXEL_SIZE_UM,
                        "detections": len(detections),
                        "ground_truth_tracks": int(metadata["track_id"].nunique()),
                        "predicted_tracks": int(predicted["track_id"].nunique()),
                        **metrics,
                    }
                )

    frame = pd.DataFrame(all_results)
    summary = (
        frame.groupby(["method", "max_distance_um"], as_index=False)[
            ["precision", "recall", "f1", "predicted_tracks"]
        ]
        .mean()
        .sort_values(["f1", "precision", "recall"], ascending=False)
        .reset_index(drop=True)
    )

    best = summary.iloc[0].to_dict() if not summary.empty else {}

    output = {
        "benchmark": {
            "dataset": "DIC-C2DH-HeLa",
            "sequences": ["01", "02"],
            "voxel_size_um": VOXEL_SIZE_UM,
            "ground_truth_centroids_as_detections": True,
            "note": "Association benchmark only; segmentation is not evaluated here.",
        },
        "results": all_results,
        "summary": summary.to_dict(orient="records"),
        "best_mean_f1": best,
    }

    (ROOT / "ctc_association_results.json").write_text(
        json.dumps(output, indent=2)
    )
    (ROOT / "ctc_association_summary.csv").write_text(
        summary.to_csv(index=False)
    )

    print(json.dumps(best, indent=2))
    print(summary.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
