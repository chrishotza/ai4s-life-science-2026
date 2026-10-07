from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai4s_io import load_ctc_tracking
from ai4s_phenotype import analyze
from ai4s_tracking import TrackingConfig, track_detections

DATA_URL = "https://data.celltrackingchallenge.net/training-datasets/DIC-C2DH-HeLa.zip"
VOXEL = (1.0, 0.19, 0.19)
SEQS = ("01", "02")

# Frozen validated baseline. This is not the official competition score.
BASELINE = {
    "precision": 0.99135,
    "recall": 0.99322,
    "f1": 0.99228,
    "coverage": 0.9451,
    "persistence_mae": 0.0439,
}


def dataset_root() -> Path:
    work = ROOT / ".benchmark_cache"
    work.mkdir(exist_ok=True)
    archive = work / "DIC-C2DH-HeLa.zip"
    if not archive.exists():
        print(f"Downloading {DATA_URL}", flush=True)
        urlretrieve(DATA_URL, archive)
    root = work / "dataset" / "DIC-C2DH-HeLa"
    if not root.exists():
        root.parent.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(root.parent)
    return root


def truth_links(nodes: pd.DataFrame) -> set[tuple[int, int]]:
    ordered = nodes.sort_values(["t", "z", "y", "x"]).reset_index(drop=True)
    out: set[tuple[int, int]] = set()
    for _, g in ordered.groupby("track_id", sort=False):
        ids = g.index.to_list()
        ids.sort(key=lambda i: int(ordered.loc[i, "t"]))
        for a, b in zip(ids, ids[1:]):
            if int(ordered.loc[b, "t"]) == int(ordered.loc[a, "t"]) + 1:
                out.add((int(a), int(b)))
    return out


def link_score(truth: set[tuple[int, int]], pred: set[tuple[int, int]]) -> dict[str, float]:
    tp, fp, fn = len(truth & pred), len(pred - truth), len(truth - pred)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def phenotype_score(
    truth_nodes: pd.DataFrame,
    truth_edges: pd.DataFrame,
    pred_nodes: pd.DataFrame,
    pred_edges: pd.DataFrame,
) -> dict[str, float]:
    def scale(frame: pd.DataFrame) -> pd.DataFrame:
        out = frame.copy()
        out[["z", "y", "x"]] = out[["z", "y", "x"]].to_numpy(float) * np.asarray(VOXEL)
        return out

    gt = analyze(scale(truth_nodes), truth_edges)
    pr = analyze(scale(pred_nodes), pred_edges)

    left = truth_nodes[["node_id", "track_id", "t"]]
    right = pred_nodes[["node_id", "track_id", "t"]]
    aligned = left.merge(right, on=["node_id", "t"], suffixes=("_gt", "_pred"))
    overlap = aligned.groupby(["track_id_gt", "track_id_pred"]).size().reset_index(name="n")
    gt_sizes = left.groupby("track_id").size().to_dict()

    used_gt: set[int] = set()
    used_pred: set[int] = set()
    rows: list[tuple[int, int, float]] = []
    for row in overlap.sort_values("n", ascending=False).itertuples(index=False):
        g, p = int(row.track_id_gt), int(row.track_id_pred)
        if g in used_gt or p in used_pred:
            continue
        rows.append((g, p, int(row.n) / max(1, int(gt_sizes[g]))))
        used_gt.add(g)
        used_pred.add(p)

    if not rows:
        return {"coverage": 0.0, "persistence_mae": 1.0}

    gt = gt.set_index("track_id")
    pr = pr.set_index("track_id")
    coverage = [row[2] for row in rows]
    persistence_mae = [
        abs(float(pr.loc[p, "directional_persistence"]) - float(gt.loc[g, "directional_persistence"]))
        for g, p, _ in rows
    ]
    return {"coverage": float(np.mean(coverage)), "persistence_mae": float(np.mean(persistence_mae))}


def evaluate(method: str, distance: float, root: Path) -> dict[str, float]:
    rows = []
    for seq in SEQS:
        truth, truth_edges, _ = load_ctc_tracking(root / f"{seq}_GT" / "TRA")
        detections = truth[["t", "z", "y", "x", "track_id"]].sort_values(["t", "z", "y", "x"]).reset_index(drop=True)
        detections["node_id"] = np.arange(len(detections))

        predicted, predicted_edges = track_detections(
            detections[["t", "z", "y", "x"]],
            TrackingConfig(max_distance_um=distance, method=method, voxel_size_um=VOXEL),
        )
        predicted_set = {(int(r.source_id), int(r.target_id)) for r in predicted_edges.itertuples()}
        rows.append({
            **link_score(truth_links(detections), predicted_set),
            **phenotype_score(truth, truth_edges, predicted, predicted_edges),
        })

    frame = pd.DataFrame(rows)
    return {metric: float(frame[metric].mean()) for metric in BASELINE}


def compare(metrics: dict[str, float]) -> dict[str, object]:
    delta = {key: metrics[key] - BASELINE[key] for key in BASELINE}
    critical = (
        delta["f1"] < -0.002
        or delta["recall"] < -0.003
        or delta["coverage"] < -0.020
        or delta["persistence_mae"] > 0.010
    )
    improved = sum(
        [
            delta["f1"] > 0,
            delta["precision"] > 0,
            delta["recall"] > 0,
            delta["coverage"] > 0,
            delta["persistence_mae"] < 0,
        ]
    )

    def utility(m: dict[str, float]) -> float:
        return (
            0.45 * m["f1"]
            + 0.10 * m["precision"]
            + 0.10 * m["recall"]
            + 0.25 * m["coverage"]
            + 0.10 * (1 - m["persistence_mae"])
        )

    score = utility(metrics)
    baseline_score = utility(BASELINE)
    if critical:
        decision = "REJECT"
    elif score > baseline_score + 0.002 and improved >= 2:
        decision = "ACCEPT"
    elif score >= baseline_score - 0.001:
        decision = "KEEP-UNDER-REVIEW"
    else:
        decision = "REJECT"

    return {
        "delta": delta,
        "internal_score": score,
        "baseline_score": baseline_score,
        "improved_dimensions": improved,
        "critical_regression": critical,
        "decision": decision,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", default="mutual_nn", choices=["mutual_nn", "hungarian", "velocity_hungarian"])
    parser.add_argument("--distance", type=float, default=8.0)
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--output", default="ab_experiment_results.json")
    args = parser.parse_args()

    root = dataset_root()
    methods = ["mutual_nn", "hungarian", "velocity_hungarian"] if args.sweep else [args.method]
    distances = [1.0, 2.0, 4.0, 6.0, 8.0] if args.sweep else [args.distance]

    reports = []
    for method in methods:
        for distance in distances:
            metrics = evaluate(method, distance, root)
            comparison = compare(metrics)
            reports.append({"candidate": {"method": method, "distance_um": distance}, "metrics": metrics, "comparison": comparison})
            print(
                f"{method:18s} {distance:4.1f} um | "
                f"F1={metrics['f1']:.5f} coverage={metrics['coverage']:.4f} "
                f"persistence_MAE={metrics['persistence_mae']:.4f} | {comparison['decision']}"
            )

    reports.sort(key=lambda item: item["comparison"]["internal_score"], reverse=True)
    Path(ROOT / args.output).write_text(
        json.dumps(
            {
                "official_competition_score": False,
                "baseline_commit": "07830adddf77fa61af8c7c05b2533f289c767a8b",
                "frozen_baseline": BASELINE,
                "reports": reports,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
