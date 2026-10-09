from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import tifffile
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from ai4s_core import runtime_metadata
from ai4s_imaging import Supervised2DSegmenter, instances_to_detections
from ai4s_io import DIC_C2DH_HELA_VOXEL_SIZE_UM, ensure_ctc_dataset, load_ctc_tracking
from ai4s_tracking import TrackingConfig, link_metrics, track_detections
from benchmark_ctc_image_e2e import image_files


MAX_TRAIN_FRAMES = 24
MAX_TEST_FRAMES = 40
SAMPLES_PER_CLASS = 2500
CENTER_RADIUS_PX = 6.0
IOU_THRESHOLD = 0.5
MAX_DISTANCE_UM = 8.0
RANDOM_STATE = 42


def frame_index(path: Path) -> int:
    digits = "".join(ch for ch in path.stem if ch.isdigit())
    if not digits:
        raise ValueError(f"No frame index found in {path.name}")
    return int(digits)


def keyed_masks(root: Path, sequence: str) -> dict[int, Path]:
    """Load dense CTC silver segmentation masks for pixel-model training/scoring."""
    paths = sorted((root / f"{sequence}_ST" / "SEG").glob("man_seg*.tif"))
    output: dict[int, Path] = {}
    for path in paths:
        index = frame_index(path)
        if index in output:
            raise ValueError(f"Duplicate segmentation frame {index} for sequence {sequence}")
        output[index] = path
    if not output:
        raise FileNotFoundError(f"No CTC ST/SEG masks for sequence {sequence}")
    return output


def label_centers(labels: np.ndarray) -> np.ndarray:
    centers = []
    for label_id in np.unique(labels):
        if label_id <= 0:
            continue
        yy, xx = np.nonzero(labels == label_id)
        if len(yy):
            centers.append((float(yy.mean()), float(xx.mean())))
    return np.asarray(centers, dtype=float).reshape(-1, 2)


def iou_matrix(gt: np.ndarray, pred: np.ndarray) -> np.ndarray:
    gt_ids = np.unique(gt)
    gt_ids = gt_ids[gt_ids > 0]
    pred_ids = np.unique(pred)
    pred_ids = pred_ids[pred_ids > 0]
    if not len(gt_ids) or not len(pred_ids):
        return np.zeros((len(gt_ids), len(pred_ids)), dtype=float)

    pred_count = int(pred_ids.max()) + 1
    gt_area = np.bincount(gt.ravel(), minlength=int(gt_ids.max()) + 1).astype(float)
    pred_area = np.bincount(pred.ravel(), minlength=pred_count).astype(float)
    code = gt.astype(np.int64) * pred_count + pred.astype(np.int64)
    intersections = np.bincount(
        code.ravel(),
        minlength=(int(gt_ids.max()) + 1) * pred_count,
    ).reshape(int(gt_ids.max()) + 1, pred_count)
    out = np.zeros((len(gt_ids), len(pred_ids)), dtype=float)
    for i, gt_id in enumerate(gt_ids):
        for j, pred_id in enumerate(pred_ids):
            inter = float(intersections[int(gt_id), int(pred_id)])
            union = gt_area[int(gt_id)] + pred_area[int(pred_id)] - inter
            out[i, j] = inter / union if union > 0 else 0.0
    return out


def segmentation_score(gt: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    matrix = iou_matrix(gt, pred)
    gt_count, pred_count = matrix.shape
    if matrix.size:
        bonus = float(min(matrix.shape) + 1)
        score = matrix + bonus * (matrix >= IOU_THRESHOLD)
        rows, cols = linear_sum_assignment(score, maximize=True)
        tp = sum(float(matrix[r, c]) >= IOU_THRESHOLD for r, c in zip(rows, cols))
        matched = [float(matrix[r, c]) for r, c in zip(rows, cols) if matrix[r, c] >= IOU_THRESHOLD]
    else:
        tp, matched = 0, []
    precision = tp / pred_count if pred_count else (1.0 if gt_count == 0 else 0.0)
    recall = tp / gt_count if gt_count else (1.0 if pred_count == 0 else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "gt_objects": float(gt_count),
        "pred_objects": float(pred_count),
        "tp_iou50": float(tp),
        "precision_iou50": float(precision),
        "recall_iou50": float(recall),
        "f1_iou50": float(f1),
        "mean_matched_iou": float(np.mean(matched) if matched else 0.0),
    }


def centroid_match(
    predicted: pd.DataFrame,
    truth: pd.DataFrame,
) -> tuple[int, int, int, dict[int, int]]:
    tp = fp = fn = 0
    mapping: dict[int, int] = {}
    p_groups = {int(t): group for t, group in predicted.groupby("t", sort=False)}
    g_groups = {int(t): group for t, group in truth.groupby("t", sort=False)}
    for t in sorted(set(p_groups) | set(g_groups)):
        p = p_groups.get(t, pd.DataFrame(columns=predicted.columns))
        g = g_groups.get(t, pd.DataFrame(columns=truth.columns))
        if p.empty:
            fn += len(g)
            continue
        if g.empty:
            fp += len(p)
            continue
        distance = np.linalg.norm(
            p[["y", "x"]].to_numpy(float)[:, None, :] - g[["y", "x"]].to_numpy(float)[None, :, :],
            axis=2,
        )
        rows, cols = linear_sum_assignment(distance)
        matches = [
            (int(r), int(c))
            for r, c in zip(rows, cols)
            if float(distance[r, c]) <= CENTER_RADIUS_PX
        ]
        tp += len(matches)
        fp += len(p) - len(matches)
        fn += len(g) - len(matches)
        for r, c in matches:
            mapping[int(p.iloc[r]["node_id"])] = int(g.iloc[c]["node_id"])
    return tp, fp, fn, mapping


def f1_from_counts(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if tp + fp else (1.0 if fn == 0 else 0.0)
    recall = tp / (tp + fn) if tp + fn else (1.0 if fp == 0 else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": float(precision), "recall": float(recall), "f1": float(f1)}


def truth_edges(nodes: pd.DataFrame) -> pd.DataFrame:
    edge_pairs: set[tuple[int, int]] = set()
    for _, group in nodes.sort_values(["track_id", "t"]).groupby("track_id", sort=False):
        ordered = group.sort_values("t")
        ids = ordered["node_id"].astype(int).tolist()
        times = ordered["t"].astype(int).tolist()
        for source, target, t0, t1 in zip(ids, ids[1:], times, times[1:]):
            if t1 == t0 + 1:
                edge_pairs.add((source, target))
    return pd.DataFrame(sorted(edge_pairs), columns=["source_id", "target_id"])


def evaluate_fold(root: Path, train_sequence: str, test_sequence: str) -> dict[str, object]:
    train_image_paths = image_files(root, train_sequence)
    train_mask_map = keyed_masks(root, train_sequence)
    paired_train = [
        (path, train_mask_map[frame_index(path)])
        for path in train_image_paths
        if frame_index(path) in train_mask_map
    ]
    if not paired_train:
        raise FileNotFoundError(f"No paired training images/masks for sequence {train_sequence}")
    if len(paired_train) > MAX_TRAIN_FRAMES:
        choices = np.unique(
            np.linspace(0, len(paired_train) - 1, num=MAX_TRAIN_FRAMES, dtype=int)
        )
        paired_train = [paired_train[int(i)] for i in choices]

    train_frames, train_masks = [], []
    for image_path, mask_path in paired_train:
        image = np.squeeze(tifffile.imread(image_path))
        mask = np.squeeze(tifffile.imread(mask_path))
        if image.ndim != 2 or mask.ndim != 2 or image.shape != mask.shape:
            raise ValueError(f"Invalid paired image/mask shapes: {image.shape} and {mask.shape}")
        train_frames.append(image)
        train_masks.append(mask)
    segmenter = Supervised2DSegmenter(
        n_estimators=60,
        max_depth=18,
        min_samples_leaf=2,
        samples_per_class_per_frame=SAMPLES_PER_CLASS,
        max_training_frames=MAX_TRAIN_FRAMES,
        random_state=RANDOM_STATE,
        min_instance_area=200,
        max_instance_area=30000,
    ).fit(np.stack(train_frames), np.stack(train_masks))

    test_image_paths = image_files(root, test_sequence)[:MAX_TEST_FRAMES]
    test_mask_map = keyed_masks(root, test_sequence)
    truth_nodes, _, _ = load_ctc_tracking(root / f"{test_sequence}_GT" / "TRA")
    truth_nodes = truth_nodes[truth_nodes["t"].isin([frame_index(path) for path in test_image_paths])].copy()

    predicted_masks: list[np.ndarray] = []
    truth_masks: list[np.ndarray] = []
    frame_rows: list[dict[str, float]] = []
    for image_path in test_image_paths:
        t = frame_index(image_path)
        if t not in test_mask_map:
            continue
        image = np.squeeze(tifffile.imread(image_path))
        truth_mask = np.squeeze(tifffile.imread(test_mask_map[t])).astype(np.int32, copy=False)
        predicted_mask = segmenter.predict_instances(image)
        predicted_masks.append(predicted_mask)
        truth_masks.append(truth_mask)
        score = segmentation_score(truth_mask, predicted_mask)
        score["frame"] = float(t)
        frame_rows.append(score)
        print(
            f"[supervised-tra] train={train_sequence} test={test_sequence} frame={t} "
            f"F1@IoU50={score['f1_iou50']:.3f}",
            flush=True,
        )

    if not predicted_masks:
        raise RuntimeError(f"No held-out frames evaluated for sequence {test_sequence}")
    eval_times = [frame_index(path) for path in test_image_paths if frame_index(path) in test_mask_map]
    detections = instances_to_detections(
        np.stack([np.squeeze(tifffile.imread(path)) for path in test_image_paths if frame_index(path) in test_mask_map]),
        np.stack(predicted_masks),
    )
    detections["t"] = detections["t"].map(dict(enumerate(eval_times))).astype(int)
    detections = detections.reset_index(drop=True)
    tracked, edges = track_detections(
        detections[["t", "z", "y", "x"]],
        TrackingConfig(
            max_distance_um=MAX_DISTANCE_UM,
            method="mutual_nn",
            voxel_size_um=DIC_C2DH_HELA_VOXEL_SIZE_UM,
        ),
    )
    matched_tp, matched_fp, matched_fn, node_mapping = centroid_match(
        tracked,
        truth_nodes[["node_id", "track_id", "t", "z", "y", "x"]],
    )
    detection_scores = f1_from_counts(matched_tp, matched_fp, matched_fn)

    gt_edges = truth_edges(truth_nodes)
    mapped_edges = {
        (node_mapping[int(row.source_id)], node_mapping[int(row.target_id)])
        for row in edges.itertuples(index=False)
        if int(row.source_id) in node_mapping and int(row.target_id) in node_mapping
    }
    predicted_edge_df = pd.DataFrame(sorted(mapped_edges), columns=["source_id", "target_id"])
    edge_score = link_metrics(predicted_edge_df, gt_edges)

    frame_df = pd.DataFrame(frame_rows)
    aggregate_frame_metrics = frame_df.mean(numeric_only=True).to_dict()
    return {
        "train_sequence": train_sequence,
        "test_sequence": test_sequence,
        "train_frames_used": int(len(paired_train)),
        "test_frames_evaluated": int(len(predicted_masks)),
        "model": {
            "type": "RandomForest background/interior/boundary",
            "n_estimators": 60,
            "max_depth": 18,
            "samples_per_class_per_frame": SAMPLES_PER_CLASS,
            "min_marker_area_px": int(segmenter.effective_min_marker_area),
            "min_marker_area_rule": "10% of median labeled training-cell area, clamped to 16-256 px",
            "random_state": RANDOM_STATE,
        },
        "segmentation": {
            "mean_object_precision_iou50": float(frame_df["precision_iou50"].mean()),
            "mean_object_recall_iou50": float(frame_df["recall_iou50"].mean()),
            "mean_object_f1_iou50": float(frame_df["f1_iou50"].mean()),
            "mean_matched_iou": float(frame_df["mean_matched_iou"].mean()),
        },
        "image_derived_detection": {
            **detection_scores,
            "match_radius_px": CENTER_RADIUS_PX,
        },
        "image_derived_tracking": {
            "edge_precision": float(edge_score["precision"]),
            "edge_recall": float(edge_score["recall"]),
            "edge_f1": float(edge_score["f1"]),
            "true_positive_links": float(edge_score["true_positive"]),
            "false_positive_links": float(edge_score["false_positive"]),
            "false_negative_links": float(edge_score["false_negative"]),
            "tracking_method": "mutual_nn",
            "max_distance_um": MAX_DISTANCE_UM,
        },
        "mean_frame_metrics": {k: float(v) for k, v in aggregate_frame_metrics.items()},
    }


def main() -> None:
    dataset_root = ensure_ctc_dataset(ROOT / ".benchmark_cache")
    folds = [
        evaluate_fold(dataset_root, "01", "02"),
        evaluate_fold(dataset_root, "02", "01"),
    ]
    output = {
        "runtime": runtime_metadata(),
        "protocol": {
            "dataset": "DIC-C2DH-HeLa",
            "label_source": "CTC ST/SEG dense silver segmentation masks",
            "training": "up to 24 evenly sampled labeled frames from one sequence",
            "evaluation": "first 40 frames in the other sequence",
            "cross_sequence_holdout": [["01", "02"], ["02", "01"]],
            "segmentation_match": "one-to-one instance IoU >= 0.5 against ST/SEG silver labels (proxy)",
            "detection_match": f"one-to-one centroid distance <= {CENTER_RADIUS_PX} px",
            "tracking": f"mutual-nearest-neighbor; {MAX_DISTANCE_UM} um gate",
            "claim_boundary": (
                "Cross-sequence raw-image-to-instance-mask-to-tracking evaluation. Segmentation "
                "scores are measured against dense CTC silver ST/SEG labels as a proxy, while "
                "detection and links are checked against GT/TRA tracking identities. This is not "
                "an official CTC leaderboard score or independent manual segmentation validation."
            ),
        },
        "folds": folds,
        "aggregate": {
            "mean_segmentation_f1_iou50": float(np.mean([
                fold["segmentation"]["mean_object_f1_iou50"] for fold in folds
            ])),
            "mean_detection_f1": float(np.mean([
                fold["image_derived_detection"]["f1"] for fold in folds
            ])),
            "mean_tracking_edge_f1": float(np.mean([
                fold["image_derived_tracking"]["edge_f1"] for fold in folds
            ])),
        },
    }
    out_path = ROOT / "ctc_supervised_tra_e2e_results.json"
    out_path.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(json.dumps(output["aggregate"], indent=2))
    print(f"Evidence written to {out_path}")


if __name__ == "__main__":
    main()
