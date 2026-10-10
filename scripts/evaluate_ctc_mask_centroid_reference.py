#!/usr/bin/env python3
"""Measure predicted-mask centroid offsets from CTC silver SEG reference masks.

Matched instances are paired by one-to-one IoU >= 0.50, independently within
each evaluated frame. The error is a comparison to a reference mask's GEOMETRIC
centroid, not a ground-truth biological-cell center or a uniform uncertainty
radius guaranteed for every tracked centroid.

CTC ST/SEG are reference/silver masks and may not annotate every visible cell.
No reference annotations are supplied to pretrained Cellpose segmentation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import tifffile
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from ai4s_io import DIC_C2DH_HELA_VOXEL_SIZE_UM, ensure_ctc_dataset
from ai4s_imaging import CellposeSegmenter
from benchmark_ctc_image_e2e import image_files
from benchmark_ctc_tra_supervised import (
    frame_index,
    iou_matrix,
    keyed_masks,
    restrict_instances_to_foi,
)

MODEL = "cpsam_v2"
MIN_SIZE = 200
FLOW_THRESHOLD = 0.4
CELLPROB_THRESHOLD = 0.0
IOU_THRESHOLD = 0.5
PIXEL_SIZE_UM_Y = float(DIC_C2DH_HELA_VOXEL_SIZE_UM[1])
PIXEL_SIZE_UM_X = float(DIC_C2DH_HELA_VOXEL_SIZE_UM[2])
SEQUENCES = ("01", "02")


def pair_mask_centroids(
    silver: np.ndarray, predicted: np.ndarray, *,
    sequence: str = "fixture", frame: int = 0,
) -> tuple[list[dict], dict]:
    """One-to-one IoU matching with centroid errors in physical units."""
    reference = np.asarray(silver)
    model = np.asarray(predicted)
    if reference.ndim != 2 or model.shape != reference.shape:
        raise ValueError("Expected two same-shape 2D instance-label masks")
    if not np.issubdtype(reference.dtype, np.integer) or not np.issubdtype(
        model.dtype, np.integer
    ):
        raise ValueError("Instance masks must have integer labels")
    if (reference < 0).any() or (model < 0).any():
        raise ValueError("Instance masks cannot have negative labels")

    gold_labels = np.unique(reference)
    gold_labels = gold_labels[gold_labels > 0]
    pred_labels = np.unique(model)
    pred_labels = pred_labels[pred_labels > 0]
    matrix = iou_matrix(reference, model)
    if matrix.shape != (len(gold_labels), len(pred_labels)):
        raise AssertionError("Inconsistent label ordering in IoU evaluator")

    assignment: list[tuple[int, int, float]] = []
    if matrix.size:
        bonus = float(min(matrix.shape) + 1)
        rewarded = matrix + bonus * (matrix >= IOU_THRESHOLD)
        r, c = linear_sum_assignment(rewarded, maximize=True)
        assignment = [
            (int(i), int(j), float(matrix[i, j]))
            for i, j in zip(r, c) if float(matrix[i, j]) >= IOU_THRESHOLD
        ]

    hits = []
    for i, j, iou in assignment:
        gid, pid = int(gold_labels[i]), int(pred_labels[j])
        ry, rx = np.nonzero(reference == gid)
        py, px = np.nonzero(model == pid)
        if not len(ry) or not len(py):
            raise AssertionError("IoU matched an empty instance")
        dy_um = (float(py.mean()) - float(ry.mean())) * PIXEL_SIZE_UM_Y
        dx_um = (float(px.mean()) - float(rx.mean())) * PIXEL_SIZE_UM_X
        distance = float(math.hypot(dy_um, dx_um))
        area_um2 = float(len(ry) * PIXEL_SIZE_UM_Y * PIXEL_SIZE_UM_X)
        equivalent_radius_um = math.sqrt(area_um2 / math.pi)
        hits.append({
            "sequence": sequence, "frame": int(frame),
            "silver_label": gid, "predicted_label": pid,
            "reference_area_pixels": int(len(ry)),
            "predicted_area_pixels": int(len(py)),
            "iou": iou,
            "reference_center_y_px": float(ry.mean()),
            "reference_center_x_px": float(rx.mean()),
            "predicted_center_y_px": float(py.mean()),
            "predicted_center_x_px": float(px.mean()),
            "dy_um": dy_um, "dx_um": dx_um,
            "offset_um": distance,
            "offset_pixels": float(math.hypot(
                float(py.mean()-ry.mean()), float(px.mean()-rx.mean())
            )),
            "reference_equivalent_radius_um": equivalent_radius_um,
            "relative_offset_to_radius": distance / equivalent_radius_um,
        })
    ref_count, pred_count = len(gold_labels), len(pred_labels)
    matches = len(hits)
    quality = {
        "sequence": sequence, "frame": int(frame),
        "reference_instances": ref_count,
        "predicted_instances": pred_count,
        "matched_instances_iou50": matches,
        "unmatched_reference_instances": ref_count - matches,
        "unmatched_predicted_instances": pred_count - matches,
        "frame_f1_iou50": (
            float(2 * matches / (ref_count + pred_count))
            if ref_count + pred_count else 1.0
        ),
    }
    return hits, quality


def summarize_errors(records: list[dict], frames: list[dict]) -> dict:
    errors = np.array([r["offset_um"] for r in records], dtype=float)
    radii = np.array([r["relative_offset_to_radius"] for r in records], dtype=float)
    total_ref = sum(f["reference_instances"] for f in frames)
    total_pred = sum(f["predicted_instances"] for f in frames)
    matched = len(records)
    return {
        "frames": len(frames),
        "matched_instances": matched,
        "reference_instances": total_ref,
        "predicted_instances": total_pred,
        "matched_reference_fraction": (
            matched / total_ref if total_ref else None
        ),
        "matched_prediction_fraction": (
            matched / total_pred if total_pred else None
        ),
        "mean_frame_f1_iou50": (
            float(np.mean([f["frame_f1_iou50"] for f in frames]))
            if frames else None
        ),
        "centroid_offset_um": {
            "mean": float(np.mean(errors)) if len(errors) else None,
            "median": float(np.median(errors)) if len(errors) else None,
            "p90": float(np.percentile(errors, 90)) if len(errors) else None,
            "p95": float(np.percentile(errors, 95)) if len(errors) else None,
            "max": float(np.max(errors)) if len(errors) else None,
            "rmse": float(np.sqrt(np.mean(errors ** 2))) if len(errors) else None,
        },
        "relative_error_to_silver_equivalent_radius": {
            "median": float(np.median(radii)) if len(radii) else None,
            "p95": float(np.percentile(radii, 95)) if len(radii) else None,
        },
        "fraction_with_offset_le_um": {
            str(threshold): (
                float(np.mean(errors <= threshold)) if len(errors) else None
            ) for threshold in (0.1, 0.25, 0.5, 1.0, 2.0)
        },
    }


def select_evenly_spaced_frames(
    root: Path, sequence: str, number: int,
) -> list[tuple[int, Path, Path]]:
    masks = keyed_masks(root, sequence)
    image_set = image_files(root, sequence)
    paired = [
        (frame_index(img), img, masks[frame_index(img)])
        for img in image_set if frame_index(img) in masks
    ]
    if len(paired) < number:
        raise ValueError(f"Sequence {sequence}: only {len(paired)} paired frames")
    indices = np.linspace(0, len(paired)-1, number, dtype=int)
    if len(np.unique(indices)) != number:
        raise ValueError("Frame sampling gave duplicate indices")
    return [paired[int(i)] for i in indices]


def run(*, per_sequence: int, output: Path, csv_output: Path) -> dict:
    if not 2 <= per_sequence <= 84:
        raise ValueError("Require 2..84 evenly spaced paired frames per sequence")
    root = ensure_ctc_dataset(ROOT / ".benchmark_cache")
    selected = [
        (seq, time, image, label)
        for seq in SEQUENCES
        for time, image, label in select_evenly_spaced_frames(root, seq, per_sequence)
    ]
    # Initialize the exact pretrained backend/hyperparameters used in the full run.
    segmenter = CellposeSegmenter(
        model_name=MODEL, min_size=MIN_SIZE,
        flow_threshold=FLOW_THRESHOLD,
        cellprob_threshold=CELLPROB_THRESHOLD, invert=False,
    )
    all_matches, all_frames = [], []
    for sequence, t, image_path, silver_path in selected:
        frame = np.squeeze(tifffile.imread(image_path))
        silver = np.squeeze(tifffile.imread(silver_path))
        if frame.ndim != 2 or silver.shape != frame.shape:
            raise ValueError(f"CTC raw/reference shape mismatch: {sequence}/{t}")
        pred = restrict_instances_to_foi(segmenter.predict_instances(frame))
        hits, q = pair_mask_centroids(
            silver, pred, sequence=sequence, frame=t,
        )
        all_matches.extend(hits)
        all_frames.append(q)
        print(
            f"[silver-center] seq={sequence} t={t:02d} "
            f"matched={len(hits)}/{q['reference_instances']} "
            f"F1@0.5={q['frame_f1_iou50']:.4f}",
            flush=True,
        )

    if not all_matches:
        raise RuntimeError("No matched silver-reference masks; cannot report offsets")
    if len(all_frames) != 2 * per_sequence:
        raise AssertionError("Missing sampled frames")
    matches_df = pd.DataFrame(all_matches).sort_values(
        ["sequence", "frame", "silver_label"]
    )
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    matches_df.to_csv(csv_output, index=False, float_format="%.9g")

    report = {
        "status": "EMPIRICAL_OFFSET_TO_CTC_SILVER_SEGMENTATION_CENTROID",
        "experiment": {
            "dataset": "CTC DIC-C2DH-HeLa training sequences 01 and 02",
            "reference_type": "silver ST/SEG manual/curated segmentation masks",
            "model": "pretrained cpsam_v2, min_size=200, flow=0.4, cellprob=0",
            "sampling": "fixed evenly spaced image/mask paired frames per sequence",
            "per_sequence_requested": per_sequence,
            "total_sampled_frames": len(all_frames),
            "image_evaluation_historical_run": "37930909373",
            "micrometers_per_pixel_yx": [PIXEL_SIZE_UM_Y, PIXEL_SIZE_UM_X],
            "matching": "one-to-one Hungarian maximum IoU, >=0.50",
            "python": platform.python_version(),
            "sampled_frame_ids": {
                seq: [f["frame"] for f in all_frames if f["sequence"] == seq]
                for seq in SEQUENCES
            },
            "per_match_csv_sha256": hashlib.sha256(csv_output.read_bytes()).hexdigest(),
        },
        "pooled": summarize_errors(all_matches, all_frames),
        "by_sequence": {
            seq: summarize_errors(
                [r for r in all_matches if r["sequence"] == seq],
                [f for f in all_frames if f["sequence"] == seq],
            ) for seq in SEQUENCES
        },
        "per_frame": all_frames,
        "limitations": [
            "Reference ST/SEG masks are SILVER annotations; their geometric centroids are not verified biological cell centers.",
            "Localization discrepancy is conditional on matching at IoU>=0.50. Unmatched objects are reported but have no interpretable centroid offset.",
            "The sampled frames belong to the two original CTC sequences and are NOT an independent dataset or a new domain-transfer benchmark.",
            "Observed offsets for matched instances do NOT provide a guaranteed uniform maximum localization-error radius for all 51 phenotype tracks.",
            "The study does not independently validate temporal association, lineage events, causal treatment responses or biological phenotypes.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps(report, indent=2, allow_nan=False),flush=True)
    return report


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--frames-per-sequence",type=int,default=8)
    p.add_argument("--output",type=Path,default=Path("ctc_centroid_reference_results.json"))
    p.add_argument("--matches-csv",type=Path,default=Path("ctc_centroid_reference_matches.csv"))
    args=p.parse_args()
    run(per_sequence=args.frames_per_sequence,output=args.output,csv_output=args.matches_csv)


if __name__ == "__main__":
    main()
