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

from ai4s_io import ensure_ctc_dataset
from benchmark_ctc_image_e2e import CANDIDATES, DetectorSpec, _mask_from_spec, image_files

MIN_AREA = 20
MAX_AREA = 5000
IOU_MATCH_THRESHOLD = 0.5


def component_labels(frame: np.ndarray, spec: DetectorSpec) -> np.ndarray:
    from scipy import ndimage

    mask = _mask_from_spec(frame, spec)
    labels, _ = ndimage.label(mask)
    output = np.zeros_like(labels, dtype=np.int32)
    next_id = 1
    for label_id in range(1, int(labels.max()) + 1):
        coords = np.argwhere(labels == label_id)
        area = int(coords.shape[0])
        if MIN_AREA <= area <= MAX_AREA:
            output[labels == label_id] = next_id
            next_id += 1
    return output


def iou_matrix(gt: np.ndarray, pred: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    gt_labels = np.unique(gt)
    gt_labels = gt_labels[gt_labels > 0]
    pred_labels = np.unique(pred)
    pred_labels = pred_labels[pred_labels > 0]

    if len(gt_labels) == 0 or len(pred_labels) == 0:
        return (
            np.zeros((len(gt_labels), len(pred_labels)), dtype=float),
            gt_labels,
            pred_labels,
        )

    pred_count = int(pred_labels.max()) + 1
    gt_area = np.bincount(gt.ravel(), minlength=int(gt_labels.max()) + 1).astype(float)
    pred_area = np.bincount(pred.ravel(), minlength=pred_count).astype(float)
    pair_code = gt.astype(np.int64) * pred_count + pred.astype(np.int64)
    intersections = np.bincount(
        pair_code.ravel(),
        minlength=(int(gt_labels.max()) + 1) * pred_count,
    ).reshape(int(gt_labels.max()) + 1, pred_count)

    matrix = np.zeros((len(gt_labels), len(pred_labels)), dtype=float)
    for i, gt_id in enumerate(gt_labels):
        for j, pred_id in enumerate(pred_labels):
            inter = float(intersections[int(gt_id), int(pred_id)])
            union = gt_area[int(gt_id)] + pred_area[int(pred_id)] - inter
            matrix[i, j] = inter / union if union > 0 else 0.0
    return matrix, gt_labels, pred_labels


def frame_score(gt: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    matrix, gt_labels, pred_labels = iou_matrix(gt, pred)
    if matrix.size == 0:
        gt_count = float(len(gt_labels))
        pred_count = float(len(pred_labels))
        return {
            "gt_objects": gt_count,
            "pred_objects": pred_count,
            "matched_objects": 0.0,
            "mean_matched_iou": 0.0,
            "mean_gt_best_iou": 0.0,
            "mean_pred_best_iou": 0.0,
            "gt_recall_iou50": 0.0 if gt_count else 1.0,
            "pred_precision_iou50": 0.0 if pred_count else 1.0,
        }

    rows, cols = linear_sum_assignment(1.0 - matrix)
    matched = [
        float(matrix[r, c])
        for r, c in zip(rows, cols)
        if float(matrix[r, c]) >= IOU_MATCH_THRESHOLD
    ]
    gt_best = matrix.max(axis=1) if len(pred_labels) else np.zeros(len(gt_labels))
    pred_best = matrix.max(axis=0) if len(gt_labels) else np.zeros(len(pred_labels))

    return {
        "gt_objects": float(len(gt_labels)),
        "pred_objects": float(len(pred_labels)),
        "matched_objects": float(len(matched)),
        "mean_matched_iou": float(np.mean(matched) if matched else 0.0),
        "mean_gt_best_iou": float(np.mean(gt_best) if len(gt_best) else 0.0),
        "mean_pred_best_iou": float(np.mean(pred_best) if len(pred_best) else 0.0),
        "gt_recall_iou50": float(np.mean(gt_best >= IOU_MATCH_THRESHOLD)),
        "pred_precision_iou50": float(np.mean(pred_best >= IOU_MATCH_THRESHOLD)),
    }


def annotated_frames(dataset_root: Path, sequence: str) -> list[Path]:
    return sorted((dataset_root / f"{sequence}_GT" / "SEG").glob("man_seg*.tif"))


def evaluate_sequence(dataset_root: Path, sequence: str, spec: DetectorSpec) -> dict[str, object]:
    paths = annotated_frames(dataset_root, sequence)
    if not paths:
        raise FileNotFoundError(f"No GT SEG annotations found for sequence {sequence}")

    raw_paths = image_files(dataset_root, sequence)
    rows: list[dict[str, float]] = []
    for gt_path in paths:
        digits = "".join(ch for ch in gt_path.stem if ch.isdigit())
        frame_index = int(digits)
        raw = np.squeeze(tifffile.imread(raw_paths[frame_index]))
        gt = np.asarray(tifffile.imread(gt_path), dtype=np.int32)
        rows.append(frame_score(gt, component_labels(raw, spec)))

    frame = pd.DataFrame(rows)
    aggregate = frame.mean(numeric_only=True).to_dict()
    return {
        "sequence": sequence,
        "detector": spec.name,
        "annotated_frames": int(len(paths)),
        **{k: float(v) for k, v in aggregate.items()},
    }


def select_detector(rows: list[dict[str, object]], sequence: str) -> str:
    candidates = [r for r in rows if r["sequence"] == sequence]
    best = max(
        candidates,
        key=lambda r: (
            float(r["mean_gt_best_iou"]),
            float(r["gt_recall_iou50"]),
            float(r["mean_matched_iou"]),
        ),
    )
    return str(best["detector"])


def main() -> None:
    dataset_root = ensure_ctc_dataset(ROOT / ".benchmark_cache")
    results: list[dict[str, object]] = []

    for sequence in ("01", "02"):
        for spec in CANDIDATES:
            print(f"[image-seg] sequence={sequence} detector={spec.name}", flush=True)
            results.append(evaluate_sequence(dataset_root, sequence, spec))

    holdout = []
    for train_sequence, test_sequence in (("01", "02"), ("02", "01")):
        selected = select_detector(results, train_sequence)
        test = next(
            row for row in results
            if row["sequence"] == test_sequence and row["detector"] == selected
        )
        holdout.append(
            {
                "train_sequence": train_sequence,
                "test_sequence": test_sequence,
                "selected_detector": selected,
                **test,
            }
        )

    holdout_frame = pd.DataFrame(holdout)
    aggregate = {
        "mean_gt_best_iou": float(holdout_frame["mean_gt_best_iou"].mean()),
        "mean_matched_iou": float(holdout_frame["mean_matched_iou"].mean()),
        "gt_recall_iou50": float(holdout_frame["gt_recall_iou50"].mean()),
        "pred_precision_iou50": float(holdout_frame["pred_precision_iou50"].mean()),
    }

    output = {
        "protocol": {
            "dataset": "DIC-C2DH-HeLa",
            "sequences": ["01", "02"],
            "reference": "CTC GT/SEG instance masks",
            "selection": "cross-sequence holdout",
            "match_threshold_iou": IOU_MATCH_THRESHOLD,
            "min_area_px": MIN_AREA,
            "max_area_px": MAX_AREA,
            "note": (
                "This is an independent image-segmentation validation layer. "
                "It is not the official CTC SEG leaderboard score."
            ),
        },
        "candidate_results": results,
        "cross_sequence_holdout": holdout,
        "aggregate": aggregate,
    }

    (ROOT / "ctc_image_segmentation_results.json").write_text(
        json.dumps(output, indent=2)
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
