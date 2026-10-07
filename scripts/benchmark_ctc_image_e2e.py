from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import tifffile
from scipy import ndimage
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai4s_io import DIC_C2DH_HELA_VOXEL_SIZE_UM, ensure_ctc_dataset, load_ctc_tracking
from ai4s_tracking import link_metrics, TrackingConfig, track_detections

VOXEL_SIZE_UM = DIC_C2DH_HELA_VOXEL_SIZE_UM
MATCH_RADIUS_PX = 6.0
MIN_AREA = 200
MAX_AREA = 30000
GATES_UM = (8.0,)

@dataclass(frozen=True)
class DetectorSpec:
    name: str
    polarity: str
    percentile: float
    sigma: float = 0.0

CANDIDATES = (
    DetectorSpec("dic_ridge_kth", "ridge", 0.0),
    DetectorSpec("dic_ridge_kth_inverted", "ridge_inverted", 0.0),
    DetectorSpec("raw_high_p90", "high", 90.0),
    DetectorSpec("raw_high_p95", "high", 95.0),
    DetectorSpec("raw_high_p97", "high", 97.0),
    DetectorSpec("raw_low_p10", "low", 10.0),
    DetectorSpec("raw_low_p5", "low", 5.0),
    DetectorSpec("residual_pos_p90", "high_residual", 90.0, 5.0),
    DetectorSpec("residual_pos_p95", "high_residual", 95.0, 5.0),
    DetectorSpec("residual_neg_p10", "low_residual", 10.0, 5.0),
    DetectorSpec("residual_neg_p5", "low_residual", 5.0, 5.0),
    DetectorSpec("residual_abs_p95", "abs_residual", 95.0, 5.0),
)

def image_files(root: Path, sequence: str) -> list[Path]:
    candidates = sorted(list((root / sequence).glob("*.tif")) + list((root / sequence).glob("*.tiff")))
    if not candidates:
        raise FileNotFoundError(f"No microscopy TIFF frames found for sequence {sequence}")
    return candidates


def _dic_ridge_mask(frame: np.ndarray, invert: bool = False) -> np.ndarray:
    image = np.asarray(frame, dtype=np.float32)
    finite = np.isfinite(image)
    if invert:
        image = -image
    if not finite.any():
        return np.zeros_like(image, dtype=bool)

    values = image[finite]
    lo, hi = np.percentile(values, (1.0, 99.0))
    if hi <= lo:
        return np.zeros_like(image, dtype=bool)
    image = np.clip((image - lo) / (hi - lo), 0.0, 1.0)

    ridge_max = np.zeros_like(image, dtype=np.float32)
    for sigma in range(5, 11):
        hxx = ndimage.gaussian_filter(image, sigma=float(sigma), order=(0, 2))
        hyy = ndimage.gaussian_filter(image, sigma=float(sigma), order=(2, 0))
        hxy = ndimage.gaussian_filter(image, sigma=float(sigma), order=(1, 1))

        trace = hxx + hyy
        disc = np.sqrt(np.maximum((hxx - hyy) ** 2 + 4.0 * hxy ** 2, 0.0))
        lambda1 = 0.5 * (trace - disc)
        lambda2 = 0.5 * (trace + disc)

        denominator = np.maximum(np.abs(lambda1), 1e-12)
        rb = np.abs(lambda2) / denominator
        s_value = lambda1 ** 2 + lambda2 ** 2
        response = np.exp(-(rb ** 2)) * (1.0 - np.exp(-s_value / 100.0))
        response[lambda1 > 0] = 0.0
        ridge_max = np.maximum(ridge_max, response.astype(np.float32))

    ridge = ndimage.gaussian_filter(ridge_max, sigma=1.0)
    transformed = np.arcsinh(20.0 * ridge)
    mean_value = float(np.mean(transformed))
    if mean_value <= 0:
        return np.zeros_like(image, dtype=bool)

    transformed = transformed / mean_value
    boundary = transformed >= 0.75
    boundary = ndimage.binary_closing(boundary, structure=np.ones((3, 3), dtype=bool))
    boundary = ndimage.binary_dilation(boundary, iterations=1)

    local_mean = ndimage.uniform_filter(image, size=9, mode="nearest")
    local_sq = ndimage.uniform_filter(image ** 2, size=9, mode="nearest")
    local_variance = np.maximum(local_sq - local_mean ** 2, 0.0)

    regions, count = ndimage.label(~boundary)
    mask = np.zeros_like(boundary, dtype=bool)
    for label_id in range(1, count + 1):
        region = regions == label_id
        area = int(region.sum())
        if area < MIN_AREA or area > MAX_AREA:
            continue
        if float(local_variance[region].mean()) > 0.0005:
            mask[region] = True
    return mask

def _mask_from_spec(frame: np.ndarray, spec: DetectorSpec) -> np.ndarray:
    if spec.polarity == "ridge":
        return _dic_ridge_mask(frame, invert=False)
    if spec.polarity == "ridge_inverted":
        return _dic_ridge_mask(frame, invert=True)

    image = np.asarray(frame, dtype=np.float32)
    finite = np.isfinite(image)
    if not finite.any():
        return np.zeros_like(image, dtype=bool)

    if spec.sigma > 0:
        smooth = ndimage.gaussian_filter(
            np.nan_to_num(image, nan=float(np.nanmedian(image[finite]))),
            sigma=spec.sigma,
        )
        signal = image - smooth
    else:
        signal = image

    values = signal[finite]
    if spec.polarity == "abs_residual":
        values_abs = np.abs(values)
        threshold = float(np.nanpercentile(values_abs, spec.percentile))
        return finite & (np.abs(signal) >= threshold)

    threshold = float(np.nanpercentile(values, spec.percentile))
    if spec.polarity in {"high", "high_residual"}:
        return finite & (signal >= threshold)
    if spec.polarity in {"low", "low_residual"}:
        return finite & (signal <= threshold)
    raise ValueError(f"Unknown polarity: {spec.polarity}")

def segment_frame(frame: np.ndarray, spec: DetectorSpec, time_index: int) -> pd.DataFrame:
    mask = _mask_from_spec(frame, spec)
    labels, count = ndimage.label(mask)
    if count == 0:
        return pd.DataFrame(columns=["t", "z", "y", "x", "area", "mean_intensity"])

    rows: list[dict[str, float | int]] = []
    for label_id, slc in enumerate(ndimage.find_objects(labels), start=1):
        if slc is None:
            continue
        coords = np.argwhere(labels[slc] == label_id)
        area = int(coords.shape[0])
        if area < MIN_AREA or area > MAX_AREA:
            continue
        y0, x0 = slc[0].start, slc[1].start
        yy = coords[:, 0] + y0
        xx = coords[:, 1] + x0
        rows.append(
            {
                "t": int(time_index),
                "z": 0.0,
                "y": float(np.mean(yy)),
                "x": float(np.mean(xx)),
                "area": area,
                "mean_intensity": float(frame[yy, xx].mean()),
            }
        )
    return pd.DataFrame(rows)

def segment_sequence(root: Path, sequence: str, spec: DetectorSpec) -> pd.DataFrame:
    rows = []
    for t, path in enumerate(image_files(root, sequence)):
        frame = np.squeeze(tifffile.imread(path))
        if frame.ndim != 2:
            raise ValueError(f"Expected 2-D DIC frame, got shape {frame.shape} at {path}")
        rows.append(segment_frame(frame, spec, t))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

def framewise_match(
    predicted: pd.DataFrame,
    truth: pd.DataFrame,
    radius_px: float = MATCH_RADIUS_PX,
) -> tuple[int, int, int, float, dict[int, int]]:
    pred_by_t = {int(t): g for t, g in predicted.groupby("t", sort=False)}
    truth_by_t = {int(t): g for t, g in truth.groupby("t", sort=False)}
    tp = fp = fn = 0
    distances: list[float] = []
    pred_to_truth: dict[int, int] = {}

    for t in sorted(set(pred_by_t) | set(truth_by_t)):
        pred = pred_by_t.get(t, pd.DataFrame(columns=predicted.columns))
        gt = truth_by_t.get(t, pd.DataFrame(columns=truth.columns))
        if pred.empty:
            fn += len(gt)
            continue
        if gt.empty:
            fp += len(pred)
            continue

        p = pred[["y", "x"]].to_numpy(float)
        g = gt[["y", "x"]].to_numpy(float)
        distance = np.linalg.norm(p[:, None, :] - g[None, :, :], axis=2)
        row_ind, col_ind = linear_sum_assignment(distance)
        matched = 0
        for r, c in zip(row_ind, col_ind):
            d = float(distance[r, c])
            if d <= radius_px:
                matched += 1
                distances.append(d)
                pred_to_truth[int(pred.iloc[r]["node_id"])] = int(gt.iloc[c]["node_id"])
        tp += matched
        fp += len(pred) - matched
        fn += len(gt) - matched

    return tp, fp, fn, float(np.mean(distances) if distances else 0.0), pred_to_truth

def truth_edges(truth: pd.DataFrame) -> set[tuple[int, int]]:
    edges: set[tuple[int, int]] = set()
    for _, group in truth.sort_values(["track_id", "t"]).groupby("track_id", sort=False):
        rows = group["node_id"].astype(int).tolist()
        times = group["t"].astype(int).tolist()
        for a, b, ta, tb in zip(rows, rows[1:], times, times[1:]):
            if tb == ta + 1:
                edges.add((a, b))
    return edges

def association_score(
    predicted_edges: pd.DataFrame,
    truth: pd.DataFrame,
    pred_to_truth: dict[int, int],
) -> dict[str, float]:
    gt_edges = truth_edges(truth)
    mapped_edges = {
        (pred_to_truth[int(row.source_id)], pred_to_truth[int(row.target_id)])
        for row in predicted_edges.itertuples(index=False)
        if int(row.source_id) in pred_to_truth and int(row.target_id) in pred_to_truth
    }
    gt_frame = pd.DataFrame(list(gt_edges), columns=["source_id", "target_id"])
    pred_frame = pd.DataFrame(list(mapped_edges), columns=["source_id", "target_id"])
    metrics = link_metrics(pred_frame, gt_frame)
    return {
        "edge_precision": float(metrics["precision"]),
        "edge_recall": float(metrics["recall"]),
        "edge_f1": float(metrics["f1"]),
        "true_positive_links": float(metrics["true_positive"]),
        "false_positive_links": float(metrics["false_positive"]),
        "false_negative_links": float(metrics["false_negative"]),
    }

def evaluate(root: Path, sequence: str, spec: DetectorSpec) -> dict[str, object]:
    truth_nodes, _, metadata = load_ctc_tracking(root / f"{sequence}_GT" / "TRA")
    detections = (
        segment_sequence(root, sequence, spec)
        .sort_values(["t", "z", "y", "x"])
        .reset_index(drop=True)
    )
    detections["node_id"] = np.arange(len(detections), dtype=int)

    tp, fp, fn, mean_distance, pred_to_truth = framewise_match(
        detections,
        truth_nodes[["node_id", "track_id", "t", "z", "y", "x"]],
    )
    tracked, edges = track_detections(
        detections[["t", "z", "y", "x"]],
        TrackingConfig(
            max_distance_um=GATES_UM[0],
            method="mutual_nn",
            voxel_size_um=VOXEL_SIZE_UM,
        ),
    )
    assoc = association_score(
        edges,
        truth_nodes[["node_id", "track_id", "t", "z", "y", "x"]],
        pred_to_truth,
    )

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    return {
        "sequence": sequence,
        "detector": spec.name,
        "detections": int(len(detections)),
        "ground_truth_detections": int(len(truth_nodes)),
        "ground_truth_tracks": int(metadata["track_id"].nunique()),
        "predicted_tracks": int(tracked["track_id"].nunique()) if not tracked.empty else 0,
        "detection_precision": float(precision),
        "detection_recall": float(recall),
        "detection_f1": float(f1),
        "mean_centroid_error_px": mean_distance,
        **assoc,
    }

def select_on_sequence(results: list[dict[str, object]], sequence: str) -> str:
    candidates = [r for r in results if r["sequence"] == sequence]
    best = max(
        candidates,
        key=lambda r: (
            float(r["detection_f1"]),
            float(r["edge_f1"]),
            float(r["detection_precision"]),
        ),
    )
    return str(best["detector"])

def main() -> None:
    dataset_root = ensure_ctc_dataset(ROOT / ".benchmark_cache")
    all_results: list[dict[str, object]] = []

    for sequence in ("01", "02"):
        for spec in CANDIDATES:
            print(f"[image-e2e] sequence={sequence} detector={spec.name}", flush=True)
            all_results.append(evaluate(dataset_root, sequence, spec))

    holdout = []
    for train_sequence, test_sequence in (("01", "02"), ("02", "01")):
        selected = select_on_sequence(all_results, train_sequence)
        test_row = next(
            r for r in all_results
            if r["sequence"] == test_sequence and r["detector"] == selected
        )
        holdout.append(
            {
                "train_sequence": train_sequence,
                "test_sequence": test_sequence,
                "selected_detector": selected,
                **test_row,
            }
        )

    holdout_frame = pd.DataFrame(holdout)
    aggregate = {
        "detection_precision": float(holdout_frame["detection_precision"].mean()),
        "detection_recall": float(holdout_frame["detection_recall"].mean()),
        "detection_f1": float(holdout_frame["detection_f1"].mean()),
        "edge_precision": float(holdout_frame["edge_precision"].mean()),
        "edge_recall": float(holdout_frame["edge_recall"].mean()),
        "edge_f1": float(holdout_frame["edge_f1"].mean()),
        "mean_centroid_error_px": float(holdout_frame["mean_centroid_error_px"].mean()),
    }

    output = {
        "protocol": {
            "dataset": "DIC-C2DH-HeLa",
            "sequences": ["01", "02"],
            "selection": "cross-sequence holdout",
            "selection_metric": "detection_f1, then edge_f1",
            "tracking_method": "mutual_nn",
            "max_distance_um": GATES_UM[0],
            "voxel_size_um": VOXEL_SIZE_UM,
            "detection_match_radius_px": MATCH_RADIUS_PX,
            "min_area_px": MIN_AREA,
            "max_area_px": MAX_AREA,
            "no_reference_centroids_as_detections": True,
            "note": (
                "Raw microscopy frames are segmented before tracking. "
                "Reference annotations are used only for scoring and cross-sequence model selection."
            ),
        },
        "candidate_results": all_results,
        "cross_sequence_holdout": holdout,
        "aggregate": aggregate,
    }

    (ROOT / "ctc_image_e2e_results.json").write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()
