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
from benchmark_ctc_tra_supervised import (
    MAX_DISTANCE_UM,
    f1_from_counts,
    frame_index,
    iou_matrix,
    keyed_track_masks,
    marker_overlap_match,
    segmentation_score,
    truth_edges,
)

TRAIN_WINDOW_FRAMES = 40
MAX_TRAIN_FRAMES = 24
TEST_START_FRAME = 40
TEST_FRAME_COUNT = 40
SAMPLES_PER_CLASS = 2500
RANDOM_STATE = 42
SEGMENTATION_F1_GATE = 0.25
DETECTION_F1_GATE = 0.50
TRACKING_EDGE_F1_GATE = 0.30
GOLD_OBJECT_RECALL_GATE = 0.20


def segmentation_masks(root: Path, sequence: str, corpus: str) -> dict[int, Path]:
    """Return CTC SEG masks. ST is dense silver supervision; GT is sparse gold evaluation."""
    paths = sorted((root / f"{sequence}_{corpus}" / "SEG").glob("man_seg*.tif"))
    output: dict[int, Path] = {}
    for path in paths:
        t = frame_index(path)
        if t in output:
            raise ValueError(f"Duplicate {corpus}/SEG mask at frame {t} for sequence {sequence}")
        output[t] = path
    if not output:
        raise FileNotFoundError(
            f"No CTC {corpus}/SEG man_seg*.tif masks for sequence {sequence}"
        )
    return output


def evaluate_sequence(root: Path, sequence: str) -> dict[str, object]:
    all_images = image_files(root, sequence)
    seg_map = segmentation_masks(root, sequence, "ST")
    gold_map = segmentation_masks(root, sequence, "GT")
    paired = [
        path for path in all_images
        if frame_index(path) in seg_map and frame_index(path) < TEST_START_FRAME
    ]
    test_paths = [
        path for path in all_images
        if TEST_START_FRAME <= frame_index(path) < TEST_START_FRAME + TEST_FRAME_COUNT
        and frame_index(path) in seg_map
    ]
    if len(paired) < MAX_TRAIN_FRAMES or not test_paths:
        raise RuntimeError(
            f"Insufficient non-overlapping frames for sequence {sequence}: "
            f"training={len(paired)}, test={len(test_paths)}"
        )

    train_frames: list[np.ndarray] = []
    train_masks: list[np.ndarray] = []
    for image_path in paired:
        image = np.squeeze(tifffile.imread(image_path))
        mask = np.squeeze(tifffile.imread(seg_map[frame_index(image_path)]))
        if image.ndim != 2 or mask.ndim != 2 or image.shape != mask.shape:
            raise ValueError(f"Invalid train pair at {image_path.name}: {image.shape} vs {mask.shape}")
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

    predicted_masks: list[np.ndarray] = []
    input_frames: list[np.ndarray] = []
    frame_metrics: list[dict[str, float]] = []
    gold_tp = 0
    gold_objects = 0
    gold_best_ious: list[float] = []
    gold_frames = 0
    eval_times: list[int] = []
    for image_path in test_paths:
        t = frame_index(image_path)
        image = np.squeeze(tifffile.imread(image_path))
        silver_mask = np.squeeze(tifffile.imread(seg_map[t])).astype(np.int32, copy=False)
        if image.ndim != 2 or silver_mask.ndim != 2 or image.shape != silver_mask.shape:
            raise ValueError(f"Invalid held-out pair at {image_path.name}")
        pred_mask = segmenter.predict_instances(image)
        # ST/SEG has broad instance coverage and is the full-frame proxy metric.
        score = segmentation_score(silver_mask, pred_mask)
        # GT/SEG is human-made but sparse. Score annotated objects only; predictions
        # on unlabeled cells are not counted as false positives.
        if t in gold_map:
            gold_mask = np.squeeze(tifffile.imread(gold_map[t])).astype(np.int32, copy=False)
            if gold_mask.shape != pred_mask.shape:
                raise ValueError(f"Gold mask shape mismatch at {image_path.name}")
            gold_ids = np.unique(gold_mask)
            gold_ids = gold_ids[gold_ids > 0]
            if len(gold_ids):
                matrix = iou_matrix(gold_mask, pred_mask)
                if matrix.size:
                    rows, cols = linear_sum_assignment(matrix, maximize=True)
                    gold_tp += sum(float(matrix[r, col]) >= 0.5 for r, col in zip(rows, cols))
                    gold_best_ious.extend(float(value) for value in matrix.max(axis=1))
                gold_objects += int(len(gold_ids))
                gold_frames += 1
        score["frame"] = float(t)
        frame_metrics.append(score)
        predicted_masks.append(pred_mask)
        input_frames.append(image)
        eval_times.append(t)
        print(
            f"[temporal-holdout] seq={sequence} t={t} "
            f"SEG_GT={int(score['gt_objects'])} pred={int(score['pred_objects'])} "
            f"mask_F1@IoU50={score['f1_iou50']:.3f}",
            flush=True,
        )

    detections = instances_to_detections(np.stack(input_frames), np.stack(predicted_masks))
    detections["t"] = detections["t"].map(dict(enumerate(eval_times))).astype(int)
    detections = detections.reset_index(drop=True)

    # TRA supplies identities and temporal edges only; its labels are not used for
    # segmentation-mask scoring.
    truth_nodes, _, _ = load_ctc_tracking(root / f"{sequence}_GT" / "TRA")
    truth_nodes = truth_nodes[truth_nodes["t"].isin(eval_times)].copy()
    tracked, predicted_edges = track_detections(
        detections[["t", "z", "y", "x", "instance_id"]],
        TrackingConfig(
            max_distance_um=MAX_DISTANCE_UM,
            method="mutual_nn",
            voxel_size_um=DIC_C2DH_HELA_VOXEL_SIZE_UM,
        ),
    )
    gt_track_masks = keyed_track_masks(root, sequence)
    tp, fp, fn, node_mapping = marker_overlap_match(
        tracked,
        truth_nodes[["node_id", "track_id", "t", "z", "y", "x"]],
        dict(zip(eval_times, predicted_masks)),
        gt_track_masks,
    )
    detection_metrics = f1_from_counts(tp, fp, fn)
    truth_edge_df = truth_edges(truth_nodes)
    mapped_edge_pairs = {
        (node_mapping[int(edge.source_id)], node_mapping[int(edge.target_id)])
        for edge in predicted_edges.itertuples(index=False)
        if int(edge.source_id) in node_mapping and int(edge.target_id) in node_mapping
    }
    mapped_edge_df = pd.DataFrame(sorted(mapped_edge_pairs), columns=["source_id", "target_id"])
    edge_metrics = link_metrics(mapped_edge_df, truth_edge_df)

    frame_df = pd.DataFrame(frame_metrics)
    return {
        "sequence": sequence,
        "protocol": {
            "training_frame_range": [0, TEST_START_FRAME - 1],
            "training_frames_available": len(paired),
            "training_frames_used": MAX_TRAIN_FRAMES,
            "test_frame_range": [min(eval_times), max(eval_times)],
            "test_frames_evaluated": len(eval_times),
            "no_temporal_overlap": True,
            "segmentation_reference": "CTC ST/SEG man_seg*.tif (dense silver proxy)",
            "gold_shape_reference": "CTC GT/SEG man_seg*.tif (sparse gold objects only)",
            "identity_and_edge_reference": "CTC GT/TRA man_track*.tif",
        },
        "model": {
            "type": "RandomForest background/interior/boundary",
            "n_estimators": 60,
            "max_depth": 18,
            "samples_per_class_per_frame": SAMPLES_PER_CLASS,
            "effective_min_marker_area_px": int(segmenter.effective_min_marker_area),
            "marker_area_rule": "10% of median labeled training-cell area, clipped to 16-256 px",
            "random_state": RANDOM_STATE,
        },
        "segmentation": {
            "reference": "ST/SEG dense silver annotations (proxy, not independent manual gold)",
            "mean_precision_iou50": float(frame_df["precision_iou50"].mean()),
            "mean_recall_iou50": float(frame_df["recall_iou50"].mean()),
            "mean_f1_iou50": float(frame_df["f1_iou50"].mean()),
            "mean_matched_iou": float(frame_df["mean_matched_iou"].mean()),
            "mean_gt_objects_per_frame": float(frame_df["gt_objects"].mean()),
            "mean_pred_objects_per_frame": float(frame_df["pred_objects"].mean()),
        },
        "sparse_gold_shape_check": {
            "reference": "GT/SEG human annotations; only annotated objects are scored",
            "gold_frames_with_objects": int(gold_frames),
            "annotated_objects": int(gold_objects),
            "matched_objects_iou50": int(gold_tp),
            "object_recall_iou50": float(gold_tp / gold_objects) if gold_objects else None,
            "mean_best_iou_per_annotated_object": (
                float(np.mean(gold_best_ious)) if gold_best_ious else None
            ),
            "precision_or_f1_reported": False,
            "reason": "Gold segmentation has sparse object coverage; unannotated cells are unknown, not negatives.",
        },
        "detection": {**detection_metrics, "matching_rule": "one-to-one predicted-instance coverage of >50% of CTC GT/TRA marker pixels"},
        "tracking": {
            "edge_precision": float(edge_metrics["precision"]),
            "edge_recall": float(edge_metrics["recall"]),
            "edge_f1": float(edge_metrics["f1"]),
            "true_positive_links": float(edge_metrics["true_positive"]),
            "false_positive_links": float(edge_metrics["false_positive"]),
            "false_negative_links": float(edge_metrics["false_negative"]),
            "method": "mutual_nn",
            "max_distance_um": MAX_DISTANCE_UM,
        },
    }


def main() -> None:
    dataset_root = ensure_ctc_dataset(ROOT / ".benchmark_cache")
    sequences = [evaluate_sequence(dataset_root, sequence) for sequence in ("01", "02")]
    aggregate = {
        "mean_segmentation_f1_iou50": float(np.mean([
            r["segmentation"]["mean_f1_iou50"] for r in sequences
        ])),
        "mean_detection_f1": float(np.mean([r["detection"]["f1"] for r in sequences])),
        "mean_tracking_edge_f1": float(np.mean([r["tracking"]["edge_f1"] for r in sequences])),
    }
    output = {
        "runtime": runtime_metadata(),
        "protocol": {
            "dataset": "DIC-C2DH-HeLa",
            "split": "per-sequence temporal holdout",
            "training_window": f"frames 0-{TEST_START_FRAME - 1}",
            "evaluation_window": f"frames {TEST_START_FRAME}-{TEST_START_FRAME + TEST_FRAME_COUNT - 1}",
            "segmentation_metric": "one-to-one instance IoU >= 0.5",
            "detection_metric": "one-to-one predicted-instance overlap with complete-coverage CTC GT/TRA marker pixels",
            "edge_metric": "image-derived temporal links matched to CTC TRA identities",
            "gold_shape_check": "GT/SEG sparse annotated objects only; no false-positive accounting on unlabeled cells",
            "quality_gate_thresholds": {
                "mean_segmentation_f1_iou50_st_proxy": SEGMENTATION_F1_GATE,
                "mean_detection_f1": DETECTION_F1_GATE,
                "mean_tracking_edge_f1": TRACKING_EDGE_F1_GATE,
                "sparse_gold_object_recall_iou50": GOLD_OBJECT_RECALL_GATE,
            },
            "claim_boundary": (
                "Same-sequence future-frame holdout, with segmentation GT/SEG labels and "
                "TRA used only for identity/link scoring, with detection evaluated by overlap between "
                "predicted cell instances and gold tracking-marker pixels (not centroid-to-cell-centroid "
                "distance). Not an official CTC leaderboard score "
                "or validation of biological phenotype labels."
            ),
        },
        "sequences": sequences,
        "aggregate": aggregate,
    }
    output_path = ROOT / "ctc_temporal_holdout_results.json"
    output_path.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"aggregate": aggregate, "per_sequence": sequences}, indent=2))
    print(f"Evidence written to {output_path}")

    failures = []
    if aggregate["mean_segmentation_f1_iou50"] < SEGMENTATION_F1_GATE:
        failures.append(
            f"segmentation F1@IoU50 {aggregate['mean_segmentation_f1_iou50']:.4f} "
            f"< {SEGMENTATION_F1_GATE:.4f}"
        )
    if aggregate["mean_detection_f1"] < DETECTION_F1_GATE:
        failures.append(
            f"detection F1 {aggregate['mean_detection_f1']:.4f} < {DETECTION_F1_GATE:.4f}"
        )
    if aggregate["mean_tracking_edge_f1"] < TRACKING_EDGE_F1_GATE:
        failures.append(
            f"tracking-edge F1 {aggregate['mean_tracking_edge_f1']:.4f} "
            f"< {TRACKING_EDGE_F1_GATE:.4f}"
        )
    gold_counts = [int(r["sparse_gold_shape_check"]["annotated_objects"]) for r in sequences]
    gold_tp_total = sum(int(r["sparse_gold_shape_check"]["matched_objects_iou50"]) for r in sequences)
    gold_total = sum(gold_counts)
    gold_recall = gold_tp_total / gold_total if gold_total else 0.0
    aggregate["sparse_gold_object_recall_iou50"] = gold_recall if gold_total else None
    aggregate["sparse_gold_annotated_objects"] = gold_total
    if gold_total and gold_recall < GOLD_OBJECT_RECALL_GATE:
        failures.append(
            f"sparse gold object recall@IoU50 {gold_recall:.4f} "
            f"< {GOLD_OBJECT_RECALL_GATE:.4f}"
        )
    if failures:
        raise SystemExit("Scientific quality gate failed: " + "; ".join(failures))
    print("Scientific quality gate passed.")


if __name__ == "__main__":
    main()
