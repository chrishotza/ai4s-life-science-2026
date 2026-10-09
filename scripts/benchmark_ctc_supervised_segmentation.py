from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import tifffile
from scipy import ndimage
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai4s_io import ensure_ctc_dataset
from benchmark_ctc_image_e2e import image_files

MIN_AREA = 200
MAX_AREA = 30000
IOU_MATCH_THRESHOLD = 0.5
RANDOM_STATE = 42
SAMPLE_PER_CLASS = 12000


def normalize(image: np.ndarray) -> np.ndarray:
    image = np.asarray(image, dtype=np.float32)
    finite = np.isfinite(image)
    if not finite.any():
        return np.zeros_like(image, dtype=np.float32)
    lo, hi = np.percentile(image[finite], (1.0, 99.0))
    if hi <= lo:
        return np.zeros_like(image, dtype=np.float32)
    return np.clip((image - lo) / (hi - lo), 0.0, 1.0)


def feature_image(image: np.ndarray) -> np.ndarray:
    x = normalize(image)
    features = [x]
    for sigma in (1.0, 2.0, 4.0, 8.0):
        smooth = ndimage.gaussian_filter(x, sigma=sigma)
        gx = ndimage.gaussian_filter(x, sigma=sigma, order=(0, 1))
        gy = ndimage.gaussian_filter(x, sigma=sigma, order=(1, 0))
        hxx = ndimage.gaussian_filter(x, sigma=sigma, order=(0, 2))
        hyy = ndimage.gaussian_filter(x, sigma=sigma, order=(2, 0))
        hxy = ndimage.gaussian_filter(x, sigma=sigma, order=(1, 1))
        trace = hxx + hyy
        disc = np.sqrt(np.maximum((hxx - hyy) ** 2 + 4.0 * hxy ** 2, 0.0))
        lam1 = 0.5 * (trace - disc)
        lam2 = 0.5 * (trace + disc)
        window = max(3, int(2 * sigma + 1))
        local_mean = ndimage.uniform_filter(x, size=window, mode="nearest")
        local_sq = ndimage.uniform_filter(x ** 2, size=window, mode="nearest")
        local_var = np.maximum(local_sq - local_mean ** 2, 0.0)
        features.extend(
            [
                x - smooth,
                np.hypot(gx, gy),
                lam1,
                lam2,
                local_mean,
                local_var,
            ]
        )
    return np.stack(features, axis=-1)


def training_labels(gt: np.ndarray) -> np.ndarray:
    cell = gt > 0
    neighborhood_max = ndimage.maximum_filter(gt, size=3, mode="nearest")
    neighborhood_min = ndimage.minimum_filter(gt, size=3, mode="nearest")
    boundary = cell & (neighborhood_max != neighborhood_min)
    labels = np.zeros_like(gt, dtype=np.uint8)
    labels[cell & ~boundary] = 1
    labels[boundary] = 2
    return labels


def sample_training_data(dataset_root: Path, sequence: str) -> tuple[np.ndarray, np.ndarray]:
    seg_paths = sorted((dataset_root / f"{sequence}_GT" / "SEG").glob("man_seg*.tif"))
    raw_paths = image_files(dataset_root, sequence)
    rng = np.random.default_rng(RANDOM_STATE)
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []

    for gt_path in seg_paths:
        frame_index = int("".join(ch for ch in gt_path.stem if ch.isdigit()))
        image = np.squeeze(tifffile.imread(raw_paths[frame_index]))
        gt = np.asarray(tifffile.imread(gt_path), dtype=np.int32)
        feat_img = feature_image(image)
        feats = feat_img.reshape(-1, feat_img.shape[-1])
        labels = training_labels(gt).reshape(-1)

        chosen = []
        for cls in (0, 1, 2):
            idx = np.flatnonzero(labels == cls)
            if len(idx) > SAMPLE_PER_CLASS:
                idx = rng.choice(idx, size=SAMPLE_PER_CLASS, replace=False)
            chosen.append(idx)
        keep = np.concatenate(chosen)
        rng.shuffle(keep)
        xs.append(feats[keep])
        ys.append(labels[keep])

    return np.vstack(xs), np.concatenate(ys)


def fit_model(dataset_root: Path, sequence: str) -> RandomForestClassifier:
    x, y = sample_training_data(dataset_root, sequence)
    model = RandomForestClassifier(
        n_estimators=60,
        max_depth=18,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )
    model.fit(x, y)
    return model


def predict_instances(model: RandomForestClassifier, image: np.ndarray) -> np.ndarray:
    feats = feature_image(image)
    classes = model.predict(feats.reshape(-1, feats.shape[-1])).reshape(image.shape)
    markers, count = ndimage.label(classes == 1)

    remap = np.zeros(count + 1, dtype=np.int32)
    next_id = 1
    for label_id in range(1, count + 1):
        area = int((markers == label_id).sum())
        if MIN_AREA <= area <= MAX_AREA:
            remap[label_id] = next_id
            next_id += 1
    markers = remap[markers]

    if next_id == 1:
        fallback, _ = ndimage.label(classes != 0)
        return fallback.astype(np.int32)

    cell_region = classes != 0
    _, indices = ndimage.distance_transform_edt(
        markers == 0,
        return_indices=True,
    )
    nearest = markers[tuple(indices)]
    return np.where(cell_region, nearest, 0).astype(np.int32)


def iou_matrix(gt: np.ndarray, pred: np.ndarray) -> np.ndarray:
    gt_labels = np.unique(gt)
    gt_labels = gt_labels[gt_labels > 0]
    pred_labels = np.unique(pred)
    pred_labels = pred_labels[pred_labels > 0]
    if len(gt_labels) == 0 or len(pred_labels) == 0:
        return np.zeros((len(gt_labels), len(pred_labels)), dtype=float)

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
    return matrix


def score_frame(gt: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    from scipy.optimize import linear_sum_assignment

    matrix = iou_matrix(gt, pred)
    if matrix.size == 0:
        return {
            "gt_objects": float(max(0, len(np.unique(gt)) - 1)),
            "pred_objects": float(max(0, len(np.unique(pred)) - 1)),
            "mean_gt_best_iou": 0.0,
            "mean_matched_iou": 0.0,
            "gt_recall_iou50": 0.0,
            "pred_precision_iou50": 0.0,
        }

    rows, cols = linear_sum_assignment(1.0 - matrix)
    matched = [
        float(matrix[r, c])
        for r, c in zip(rows, cols)
        if float(matrix[r, c]) >= IOU_MATCH_THRESHOLD
    ]
    gt_best = matrix.max(axis=1) if matrix.shape[1] else np.zeros(matrix.shape[0])
    pred_best = matrix.max(axis=0) if matrix.shape[0] else np.zeros(matrix.shape[1])

    return {
        "gt_objects": float(matrix.shape[0]),
        "pred_objects": float(matrix.shape[1]),
        "mean_gt_best_iou": float(gt_best.mean() if len(gt_best) else 0.0),
        "mean_matched_iou": float(np.mean(matched) if matched else 0.0),
        "gt_recall_iou50": float(np.mean(gt_best >= IOU_MATCH_THRESHOLD) if len(gt_best) else 0.0),
        "pred_precision_iou50": float(np.mean(pred_best >= IOU_MATCH_THRESHOLD) if len(pred_best) else 0.0),
    }


def evaluate_holdout(dataset_root: Path, train_sequence: str, test_sequence: str) -> dict[str, object]:
    model = fit_model(dataset_root, train_sequence)
    raw_paths = image_files(dataset_root, test_sequence)
    seg_paths = sorted((dataset_root / f"{test_sequence}_GT" / "SEG").glob("man_seg*.tif"))
    rows = []

    for gt_path in seg_paths:
        frame_index = int("".join(ch for ch in gt_path.stem if ch.isdigit()))
        image = np.squeeze(tifffile.imread(raw_paths[frame_index]))
        gt = np.asarray(tifffile.imread(gt_path), dtype=np.int32)
        pred = predict_instances(model, image)
        rows.append(score_frame(gt, pred))

    frame = pd.DataFrame(rows)
    aggregate = frame.mean(numeric_only=True).to_dict()
    return {
        "train_sequence": train_sequence,
        "test_sequence": test_sequence,
        "annotated_frames": int(len(seg_paths)),
        "training_samples_per_class_cap": SAMPLE_PER_CLASS,
        "model": {
            "type": "random_forest",
            "n_estimators": 60,
            "max_depth": 18,
            "min_samples_leaf": 2,
            "random_state": RANDOM_STATE,
        },
        **{k: float(v) for k, v in aggregate.items()},
    }


def main() -> None:
    dataset_root = ensure_ctc_dataset(ROOT / ".benchmark_cache")
    holdout = [
        evaluate_holdout(dataset_root, "01", "02"),
        evaluate_holdout(dataset_root, "02", "01"),
    ]
    table = pd.DataFrame(holdout)
    output = {
        "protocol": {
            "dataset": "DIC-C2DH-HeLa",
            "train_test": [["01", "02"], ["02", "01"]],
            "selection": "strict cross-sequence holdout",
            "training_labels": "CTC GT/SEG instance masks from the training sequence only",
            "features": "multi-scale intensity, contrast, gradient, Hessian-eigenvalue and local-variance features",
            "note": (
                "The classifier is trained from public CTC training annotations at benchmark time. "
                "No external model weights or private data are used."
            ),
        },
        "holdout": holdout,
        "aggregate": {
            "mean_gt_best_iou": float(table["mean_gt_best_iou"].mean()),
            "mean_matched_iou": float(table["mean_matched_iou"].mean()),
            "gt_recall_iou50": float(table["gt_recall_iou50"].mean()),
            "pred_precision_iou50": float(table["pred_precision_iou50"].mean()),
        },
    }
    (ROOT / "ctc_supervised_segmentation_results.json").write_text(
        json.dumps(output, indent=2)
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
