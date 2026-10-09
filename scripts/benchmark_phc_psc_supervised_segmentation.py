from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import tifffile
from scipy import ndimage
from scipy.optimize import linear_sum_assignment
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from ai4s_core import runtime_metadata
from ai4s_io import ensure_ctc_phc_psc_dataset
from benchmark_ctc_image_e2e import image_files

MIN_AREA = 200
MAX_AREA = 30000
IOU_MATCH_THRESHOLD = 0.5
RANDOM_STATE = 42
SAMPLE_PER_CLASS = 3000
TRAIN_FRAME_CAP = 24
TEST_FRAME_CAP = 40


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


def annotation_masks(
    dataset_root: Path,
    sequence: str,
    corpus: str,
) -> list[Path]:
    if corpus not in {"gold", "silver"}:
        raise ValueError("corpus must be 'gold' or 'silver'")
    suffix = "GT" if corpus == "gold" else "ST"
    paths = sorted(
        (dataset_root / f"{sequence}_{suffix}" / "SEG").glob("man_seg*.tif")
    )
    return paths


def sampled_indices(length: int, limit: int) -> np.ndarray:
    if length <= 0:
        return np.asarray([], dtype=int)
    if length <= limit:
        return np.arange(length, dtype=int)
    return np.unique(np.linspace(0, length - 1, num=limit, dtype=int))


def choose_training_corpus(
    dataset_root: Path,
    sequence: str,
) -> tuple[str, list[Path]]:
    silver = annotation_masks(dataset_root, sequence, "silver")
    if silver:
        return "silver", silver
    gold = annotation_masks(dataset_root, sequence, "gold")
    if gold:
        return "gold_sparse_fallback", gold
    raise FileNotFoundError(f"No GT or ST SEG masks found for sequence {sequence}")


def sample_training_data(
    dataset_root: Path,
    sequence: str,
) -> tuple[np.ndarray, np.ndarray, int, str, int]:
    corpus, seg_paths = choose_training_corpus(dataset_root, sequence)
    raw_paths = image_files(dataset_root, sequence)
    selected = sampled_indices(len(seg_paths), TRAIN_FRAME_CAP)
    rng = np.random.default_rng(RANDOM_STATE)
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []

    for order, sample_index in enumerate(selected, start=1):
        gt_path = seg_paths[int(sample_index)]
        frame_index = int("".join(ch for ch in gt_path.stem if ch.isdigit()))
        if frame_index >= len(raw_paths):
            raise IndexError(
                f"SEG frame {frame_index} exceeds raw sequence length {len(raw_paths)}"
            )
        image = np.squeeze(tifffile.imread(raw_paths[frame_index]))
        gt = np.asarray(tifffile.imread(gt_path), dtype=np.int32)
        if image.shape != gt.shape:
            raise ValueError(
                f"Image/SEG shape mismatch at sequence {sequence}, frame {frame_index}"
            )
        features = feature_image(image).reshape(-1, 25)
        labels = training_labels(gt).reshape(-1)

        chosen = []
        for cls in (0, 1, 2):
            indices = np.flatnonzero(labels == cls)
            if len(indices) > SAMPLE_PER_CLASS:
                indices = rng.choice(indices, size=SAMPLE_PER_CLASS, replace=False)
            chosen.append(indices)
        keep = np.concatenate(chosen)
        rng.shuffle(keep)
        xs.append(features[keep])
        ys.append(labels[keep])
        print(
            f"[psc-seg] train seq={sequence} corpus={corpus} "
            f"frame={frame_index} progress={order}/{len(selected)} "
            f"sampled_pixels={len(keep)}",
            flush=True,
        )

    return np.vstack(xs), np.concatenate(ys), int(len(selected)), corpus, len(seg_paths)


def fit_model(dataset_root: Path, sequence: str) -> tuple[RandomForestClassifier, dict[str, object]]:
    x, y, frames_used, corpus, masks_available = sample_training_data(
        dataset_root, sequence
    )
    model = RandomForestClassifier(
        n_estimators=60,
        max_depth=18,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )
    model.fit(x, y)
    return model, {
        "train_annotation_source": corpus,
        "train_frames_available": masks_available,
        "train_frames_used": frames_used,
        "train_samples_per_class_cap_per_frame": SAMPLE_PER_CLASS,
    }


def predict_instances(model: RandomForestClassifier, image: np.ndarray) -> np.ndarray:
    features = feature_image(image)
    classes = model.predict(features.reshape(-1, features.shape[-1])).reshape(image.shape)
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
    gt_count = int(np.count_nonzero(np.unique(gt) > 0))
    pred_count = int(np.count_nonzero(np.unique(pred) > 0))
    matrix = iou_matrix(gt, pred)
    if matrix.size == 0:
        return {
            "gt_objects": float(gt_count),
            "pred_objects": float(pred_count),
            "mean_gt_best_iou": 0.0,
            "mean_matched_iou": 0.0,
            "gt_recall_iou50": 0.0 if gt_count else 1.0,
            "pred_precision_iou50": 0.0 if pred_count else 1.0,
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
        "gt_objects": float(len(gt_best)),
        "pred_objects": float(len(pred_best)),
        "mean_gt_best_iou": float(gt_best.mean() if len(gt_best) else 0.0),
        "mean_matched_iou": float(np.mean(matched) if matched else 0.0),
        "gt_recall_iou50": float(
            np.mean(gt_best >= IOU_MATCH_THRESHOLD) if len(gt_best) else 0.0
        ),
        "pred_precision_iou50": float(
            np.mean(pred_best >= IOU_MATCH_THRESHOLD) if len(pred_best) else 0.0
        ),
    }


def evaluate_on_annotations(
    model: RandomForestClassifier,
    dataset_root: Path,
    sequence: str,
    corpus: str,
    frame_cap: int,
) -> dict[str, object] | None:
    seg_paths = annotation_masks(dataset_root, sequence, corpus)
    if not seg_paths:
        return None
    raw_paths = image_files(dataset_root, sequence)
    selected = sampled_indices(len(seg_paths), frame_cap)
    rows = []

    for order, seg_index in enumerate(selected, start=1):
        gt_path = seg_paths[int(seg_index)]
        frame_index = int("".join(ch for ch in gt_path.stem if ch.isdigit()))
        if frame_index >= len(raw_paths):
            raise IndexError(
                f"SEG frame {frame_index} exceeds raw sequence length {len(raw_paths)}"
            )
        image = np.squeeze(tifffile.imread(raw_paths[frame_index]))
        gt = np.asarray(tifffile.imread(gt_path), dtype=np.int32)
        if image.shape != gt.shape:
            raise ValueError(
                f"Image/SEG shape mismatch at sequence {sequence}, frame {frame_index}"
            )
        pred = predict_instances(model, image)
        rows.append(score_frame(gt, pred))
        print(
            f"[psc-seg] test seq={sequence} corpus={corpus} frame={frame_index} "
            f"progress={order}/{len(selected)}",
            flush=True,
        )

    frame = pd.DataFrame(rows)
    aggregate = frame.mean(numeric_only=True).to_dict()
    return {
        "annotation_source": corpus,
        "annotated_frames_available": int(len(seg_paths)),
        "frames_sampled": int(len(selected)),
        **{key: float(value) for key, value in aggregate.items()},
    }


def evaluate_holdout(
    dataset_root: Path,
    train_sequence: str,
    test_sequence: str,
) -> dict[str, object]:
    model, train_metadata = fit_model(dataset_root, train_sequence)
    test_silver_masks = annotation_masks(dataset_root, test_sequence, "silver")
    test_gold_masks = annotation_masks(dataset_root, test_sequence, "gold")
    if not test_silver_masks and not test_gold_masks:
        raise FileNotFoundError(f"No GT or ST SEG masks found for test sequence {test_sequence}")

    primary_corpus = "silver" if test_silver_masks else "gold"
    primary_evaluation = evaluate_on_annotations(
        model,
        dataset_root,
        test_sequence,
        primary_corpus,
        TEST_FRAME_CAP,
    )
    gold_evaluation = (
        evaluate_on_annotations(
            model,
            dataset_root,
            test_sequence,
            "gold",
            frame_cap=max(1, len(test_gold_masks)),
        )
        if test_silver_masks and test_gold_masks
        else None
    )
    return {
        "train_sequence": train_sequence,
        "test_sequence": test_sequence,
        **train_metadata,
        "primary_evaluation": primary_evaluation,
        "sparse_gold_evaluation": gold_evaluation,
        "model": {
            "type": "random_forest",
            "n_estimators": 60,
            "max_depth": 18,
            "min_samples_leaf": 2,
            "random_state": RANDOM_STATE,
        },
    }


def metric_means(holdout: list[dict[str, object]], key: str) -> dict[str, float] | None:
    rows = [
        row[key]
        for row in holdout
        if isinstance(row.get(key), dict)
    ]
    if not rows:
        return None
    frame = pd.DataFrame(rows)
    metric_names = (
        "mean_gt_best_iou",
        "mean_matched_iou",
        "gt_recall_iou50",
        "pred_precision_iou50",
        "gt_objects",
        "pred_objects",
    )
    return {name: float(frame[name].mean()) for name in metric_names if name in frame}


def main() -> None:
    dataset_root = ensure_ctc_phc_psc_dataset(ROOT / ".benchmark_cache")
    holdout = [
        evaluate_holdout(dataset_root, "01", "02"),
        evaluate_holdout(dataset_root, "02", "01"),
    ]
    output = {
        "runtime": runtime_metadata(),
        "protocol": {
            "dataset": "PhC-C2DL-PSC",
            "microscopy": "phase-contrast pancreatic stem cells",
            "pixel_size_um": [1.6, 1.6],
            "frame_interval_minutes": 10,
            "train_test": [["01", "02"], ["02", "01"]],
            "selection": "strict cross-sequence holdout; no test-sequence masks used for fitting",
            "training_corpus_policy": (
                "Prefer CTC silver SEG annotations for dense training coverage; use sparse gold "
                "SEG only when silver annotations are unavailable."
            ),
            "test_corpus_policy": (
                "Primary evaluation uses silver SEG annotations where available; sparse gold SEG "
                "is reported separately as a lower-coverage cross-check."
            ),
            "training_frames_cap": TRAIN_FRAME_CAP,
            "test_frames_cap": TEST_FRAME_CAP,
            "sampling": "deterministic even coverage of annotated frames; available and sampled counts disclosed",
            "features": "multi-scale intensity, local contrast, gradient, Hessian eigenvalues and variance",
            "model": "RandomForestClassifier; no external model weights or private data",
            "object_match_threshold_iou": IOU_MATCH_THRESHOLD,
            "claim_boundary": (
                "Cross-sequence raw-image-to-instance-mask validation on PhC-C2DL-PSC. Silver-mask "
                "agreement is not human gold-standard segmentation, independent biological validation, "
                "or an official CTC leaderboard score."
            ),
        },
        "holdout": holdout,
        "aggregate_primary": metric_means(holdout, "primary_evaluation"),
        "aggregate_sparse_gold_crosscheck": metric_means(holdout, "sparse_gold_evaluation"),
    }
    (ROOT / "phc_psc_supervised_segmentation_results.json").write_text(
        json.dumps(output, indent=2)
    )
    table = pd.DataFrame(
        [
            {
                "train_sequence": row["train_sequence"],
                "test_sequence": row["test_sequence"],
                "train_annotation_source": row["train_annotation_source"],
                "train_frames_available": row["train_frames_available"],
                "train_frames_used": row["train_frames_used"],
                "test_annotation_source": row["primary_evaluation"]["annotation_source"],
                "test_annotated_frames_available": row["primary_evaluation"]["annotated_frames_available"],
                "test_frames_sampled": row["primary_evaluation"]["frames_sampled"],
                **{
                    f"primary_{metric}": row["primary_evaluation"][metric]
                    for metric in (
                        "mean_gt_best_iou",
                        "mean_matched_iou",
                        "gt_recall_iou50",
                        "pred_precision_iou50",
                    )
                },
            }
            for row in holdout
        ]
    )
    (ROOT / "phc_psc_supervised_segmentation_summary.csv").write_text(
        table.to_csv(index=False)
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
