from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tifffile
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai4s_io import ensure_ctc_dataset, load_ctc_tracking
from ai4s_imaging import Supervised2DSegmenter, instances_to_detections
from ai4s_phenotype import analyze, discover_phenotypes
from ai4s_tracking import TrackingConfig, link_metrics, track_detections

DATA_URL = "https://data.celltrackingchallenge.net/training-datasets/DIC-C2DH-HeLa.zip"
VOXEL = (1.0, 0.19, 0.19)
SEQ = "01"
TRAIN_SEQ = "02"
MAX_FRAMES = 48
MAX_TRAIN_FRAMES = 24
FPS = 6


def prepare_dataset() -> Path:
    return ensure_ctc_dataset(ROOT / ".benchmark_cache")


def image_files(
    root: Path,
    sequence: str = SEQ,
    max_frames: int | None = MAX_FRAMES,
) -> list[Path]:
    candidates = sorted(
        list((root / sequence).glob("*.tif"))
        + list((root / sequence).glob("*.tiff"))
    )
    if not candidates:
        raise FileNotFoundError(f"No microscopy TIFF frames found for sequence {sequence}.")
    return candidates if max_frames is None else candidates[:max_frames]


def frame_number(path: Path) -> int:
    digits = "".join(ch for ch in path.stem if ch.isdigit())
    if not digits:
        raise ValueError(f"Cannot identify frame number in {path.name}")
    return int(digits)


def track_mask_files(root: Path, sequence: str) -> dict[int, Path]:
    paths = sorted((root / f"{sequence}_GT" / "TRA").glob("man_track*.tif"))
    result: dict[int, Path] = {}
    for path in paths:
        index = frame_number(path)
        if index in result:
            raise ValueError(f"Duplicate GT/TRA frame index {index}")
        result[index] = path
    if not result:
        raise FileNotFoundError(f"No GT/TRA instance masks for sequence {sequence}")
    return result


def fit_supervised_segmenter(root: Path) -> Supervised2DSegmenter:
    """Fit using one annotated sequence, then infer on the separate demo sequence."""
    all_images = image_files(root, TRAIN_SEQ, max_frames=None)
    masks = track_mask_files(root, TRAIN_SEQ)
    pairs = [(path, masks[frame_number(path)]) for path in all_images if frame_number(path) in masks]
    if not pairs:
        raise FileNotFoundError(f"No paired images/GT masks for training sequence {TRAIN_SEQ}")
    if len(pairs) > MAX_TRAIN_FRAMES:
        selected = np.unique(
            np.linspace(0, len(pairs) - 1, num=MAX_TRAIN_FRAMES, dtype=int)
        )
        pairs = [pairs[int(i)] for i in selected]

    train_images, train_masks = [], []
    for image_path, mask_path in pairs:
        image = np.squeeze(tifffile.imread(image_path))
        mask = np.squeeze(tifffile.imread(mask_path))
        if image.ndim != 2 or mask.ndim != 2 or image.shape != mask.shape:
            raise ValueError(f"Invalid training image/mask pair: {image_path.name}, {mask_path.name}")
        train_images.append(image)
        train_masks.append(mask)

    model = Supervised2DSegmenter(
        n_estimators=60,
        max_depth=18,
        min_samples_leaf=2,
        samples_per_class_per_frame=2500,
        max_training_frames=MAX_TRAIN_FRAMES,
        random_state=42,
        min_marker_area=8,
        min_instance_area=200,
        max_instance_area=30000,
    )
    model.fit(np.stack(train_images), np.stack(train_masks))
    print(
        f"Fitted supervised segmenter on {len(train_images)} annotated frames "
        f"from sequence {TRAIN_SEQ}; demo inference will use raw sequence {SEQ}.",
        flush=True,
    )
    return model


def label_centers(labels: np.ndarray) -> np.ndarray:
    centers = []
    for label_id in np.unique(labels):
        if label_id <= 0:
            continue
        yy, xx = np.nonzero(labels == label_id)
        if len(yy):
            centers.append((float(yy.mean()), float(xx.mean())))
    return np.asarray(centers, dtype=float).reshape(-1, 2)


def segmentation_f1(gt: np.ndarray, pred: np.ndarray, threshold: float = 0.5) -> dict[str, float]:
    gt_ids = np.unique(gt)
    gt_ids = gt_ids[gt_ids > 0]
    pred_ids = np.unique(pred)
    pred_ids = pred_ids[pred_ids > 0]
    if not len(gt_ids) or not len(pred_ids):
        tp = 0
    else:
        pred_count = int(pred_ids.max()) + 1
        gt_area = np.bincount(gt.ravel(), minlength=int(gt_ids.max()) + 1).astype(float)
        pred_area = np.bincount(pred.ravel(), minlength=pred_count).astype(float)
        code = gt.astype(np.int64) * pred_count + pred.astype(np.int64)
        inter = np.bincount(
            code.ravel(),
            minlength=(int(gt_ids.max()) + 1) * pred_count,
        ).reshape(int(gt_ids.max()) + 1, pred_count)
        iou = np.zeros((len(gt_ids), len(pred_ids)), dtype=float)
        for i, gt_id in enumerate(gt_ids):
            for j, pred_id in enumerate(pred_ids):
                common = float(inter[int(gt_id), int(pred_id)])
                union = gt_area[int(gt_id)] + pred_area[int(pred_id)] - common
                iou[i, j] = common / union if union > 0 else 0.0
        bonus = float(min(iou.shape) + 1)
        rows, cols = linear_sum_assignment(iou + bonus * (iou >= threshold), maximize=True)
        tp = sum(float(iou[r, c]) >= threshold for r, c in zip(rows, cols))
    fp, fn = len(pred_ids) - tp, len(gt_ids) - tp
    precision = tp / len(pred_ids) if len(pred_ids) else (1.0 if not len(gt_ids) else 0.0)
    recall = tp / len(gt_ids) if len(gt_ids) else (1.0 if not len(pred_ids) else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": float(precision), "recall": float(recall), "f1": float(f1)}


def center_counts(gt: np.ndarray, pred: np.ndarray, radius_px: float = 6.0) -> tuple[int, int, int]:
    gt_centers, pred_centers = label_centers(gt), label_centers(pred)
    if not len(gt_centers):
        return (0, len(pred_centers), 0)
    if not len(pred_centers):
        return (0, 0, len(gt_centers))
    distances = np.linalg.norm(
        pred_centers[:, None, :] - gt_centers[None, :, :], axis=2
    )
    rows, cols = linear_sum_assignment(distances)
    tp = sum(float(distances[r, c]) <= radius_px for r, c in zip(rows, cols))
    return (int(tp), int(len(pred_centers) - tp), int(len(gt_centers) - tp))


def consecutive_truth_edges(nodes):
    pairs = set()
    for _, group in nodes.sort_values(["track_id", "t"]).groupby("track_id", sort=False):
        group = group.sort_values("t")
        ids, times = group["node_id"].astype(int).tolist(), group["t"].astype(int).tolist()
        for a, b, ta, tb in zip(ids, ids[1:], times, times[1:]):
            if tb == ta + 1:
                pairs.add((a, b))
    return set(pairs)


def evaluate_demo_run(root: Path, image_paths: list[Path], predicted_masks: np.ndarray, tracked, edges) -> dict[str, float | int]:
    mask_map = track_mask_files(root, SEQ)
    truth_nodes, _, _ = load_ctc_tracking(root / f"{SEQ}_GT" / "TRA")
    frame_ids = [frame_number(path) for path in image_paths]
    truth_nodes = truth_nodes[truth_nodes["t"].isin(frame_ids)].copy()
    mask_scores, tp, fp, fn = [], 0, 0, 0

    for i, t in enumerate(frame_ids):
        if t not in mask_map:
            continue
        truth_mask = np.squeeze(tifffile.imread(mask_map[t])).astype(np.int32, copy=False)
        mask_scores.append(segmentation_f1(truth_mask, predicted_masks[i]))
        frame_tp, frame_fp, frame_fn = center_counts(truth_mask, predicted_masks[i])
        tp += frame_tp
        fp += frame_fp
        fn += frame_fn

    det_precision = tp / (tp + fp) if tp + fp else 0.0
    det_recall = tp / (tp + fn) if tp + fn else 0.0
    det_f1 = 2 * det_precision * det_recall / (det_precision + det_recall) if det_precision + det_recall else 0.0

    node_mapping = {}
    p_by_t = {int(t): g for t, g in tracked.groupby("t", sort=False)}
    g_by_t = {int(t): g for t, g in truth_nodes.groupby("t", sort=False)}
    for t in sorted(set(p_by_t) | set(g_by_t)):
        p, g = p_by_t.get(t), g_by_t.get(t)
        if p is None or g is None or p.empty or g.empty:
            continue
        distance = np.linalg.norm(
            p[["y", "x"]].to_numpy(float)[:, None, :] - g[["y", "x"]].to_numpy(float)[None, :, :],
            axis=2,
        )
        rows, cols = linear_sum_assignment(distance)
        for r, c in zip(rows, cols):
            if float(distance[r, c]) <= 6.0:
                node_mapping[int(p.iloc[r]["node_id"])] = int(g.iloc[c]["node_id"])

    mapped = {
        (node_mapping[int(row.source_id)], node_mapping[int(row.target_id)])
        for row in edges.itertuples(index=False)
        if int(row.source_id) in node_mapping and int(row.target_id) in node_mapping
    }
    truth_pairs = consecutive_truth_edges(truth_nodes)
    predicted_edges = [{"source_id": a, "target_id": b} for a, b in sorted(mapped)]
    truth_edge_rows = [{"source_id": a, "target_id": b} for a, b in sorted(truth_pairs)]
    import pandas as pd
    link_score = link_metrics(pd.DataFrame(predicted_edges, columns=["source_id", "target_id"]),
                              pd.DataFrame(truth_edge_rows, columns=["source_id", "target_id"]))
    mask_f1 = float(np.mean([row["f1"] for row in mask_scores])) if mask_scores else 0.0
    return {
        "heldout_mask_f1_iou50": mask_f1,
        "heldout_centroid_detection_f1_r6px": float(det_f1),
        "heldout_tracking_edge_f1": float(link_score["f1"]),
        "heldout_detection_precision_r6px": float(det_precision),
        "heldout_detection_recall_r6px": float(det_recall),
        "image_derived_observations": int(len(tracked)),
        "image_derived_tracks": int(tracked["track_id"].nunique()) if not tracked.empty else 0,
        "image_derived_temporal_links": int(len(edges)),
        "training_sequence": TRAIN_SEQ,
        "inference_sequence": SEQ,
        "training_frames": MAX_TRAIN_FRAMES,
        "evaluated_frames": int(len(image_paths)),
    }


def normalize(image: np.ndarray) -> np.ndarray:
    image = image.astype(np.float32)
    lo, hi = np.percentile(image, (1, 99))
    if hi <= lo:
        return np.zeros_like(image)
    return np.clip((image - lo) / (hi - lo), 0, 1)



def render_title(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 7), dpi=120)
    ax.set_axis_off()
    ax.text(
        0.05, 0.80,
        "Temporal Cellular\nPhenotype Engine",
        fontsize=31,
        weight="bold",
        va="top",
    )
    ax.text(
        0.05, 0.51,
        "Microscopy  →  Tracking  →  Temporal phenotype  →  Discovery",
        fontsize=15,
    )
    ax.text(
        0.05, 0.38,
        "AI4S Life Science 2026  |  End-to-End System",
        fontsize=12,
    )
    ax.text(
        0.05, 0.22,
        "Real DIC-C2DH-HeLa microscopy with a deterministic, reproducible baseline.",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)



def render_detection(
    image: np.ndarray,
    path: Path,
    detections,
    instance_mask: np.ndarray,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 7), dpi=120)
    ax.imshow(normalize(image), cmap="gray")
    if instance_mask is not None and np.any(instance_mask > 0):
        display_mask = np.ma.masked_where(instance_mask == 0, instance_mask)
        ax.imshow(display_mask, cmap="turbo", alpha=0.42, interpolation="nearest")
    if detections is not None and not detections.empty:
        ax.scatter(
            detections["x"],
            detections["y"],
            s=24,
            facecolors="none",
            edgecolors="white",
            linewidth=0.8,
        )
    ax.set_axis_off()
    ax.set_title(
        "Stage 1 | Raw microscopy → supervised instance masks → centroids",
        fontsize=13,
    )
    ax.text(
        0.01,
        0.02,
        f"Random Forest trained on CTC GT/TRA masks from sequence {TRAIN_SEQ}; "
        f"predictions use raw images from held-out sequence {SEQ}.",
        transform=ax.transAxes,
        fontsize=8.5,
        bbox=dict(facecolor="black", alpha=0.70, pad=4),
        color="white",
    )
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def render_frame(
    image: np.ndarray,
    tracks,
    frame_index: int,
    total_frames: int,
    path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 7), dpi=120)
    ax.imshow(normalize(image), cmap="gray")
    cmap = plt.get_cmap("turbo")

    current = tracks[tracks["t"] <= frame_index]
    ids = sorted(current["track_id"].unique())
    denom = max(1, len(ids) - 1)

    for rank, track_id in enumerate(ids):
        group = current[current["track_id"] == track_id].sort_values("t")
        if len(group) < 2:
            continue
        color = cmap(rank / denom)
        ax.plot(group["x"], group["y"], linewidth=1.6, alpha=0.85, color=color)
        last = group.iloc[-1]
        if int(last["t"]) == frame_index:
            ax.scatter([last["x"]], [last["y"]], s=20, color=color, edgecolor="white", linewidth=0.4)

    ax.set_title(
        "Temporal Cellular Phenotype Engine  |  "
        f"DIC-C2DH-HeLa / sequence {SEQ}  |  frame {frame_index + 1}/{total_frames}",
        fontsize=12,
    )
    ax.text(
        0.01, 0.02,
        "Image-derived trajectories from supervised masks; training and inference sequences are separated",
        transform=ax.transAxes,
        fontsize=9,
        bbox=dict(facecolor="black", alpha=0.60, pad=4),
        color="white",
    )
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)



def physical_coordinates_for_phenotype(tracks):
    """Convert pixel coordinates to micrometers before deriving motion features."""
    physical = tracks.copy()
    physical[["z", "y", "x"]] = (
        physical[["z", "y", "x"]].to_numpy(dtype=float) * np.asarray(VOXEL, dtype=float)
    )
    return physical


def render_phenotype(path: Path, tracks, edges) -> None:
    phenotypes = analyze(physical_coordinates_for_phenotype(tracks), edges)
    eligible = phenotypes.loc[phenotypes["observations"] >= 3].copy()
    if len(eligible) >= 3:
        discovered = discover_phenotypes(
            eligible,
            n_clusters=min(3, len(eligible)),
            random_state=17,
        )
    else:
        discovered = eligible.assign(
            phenotype_cluster=-1,
            phenotype_cluster_name="insufficient_tracks",
        )

    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(10, 7), dpi=120)
    cmap = plt.get_cmap("turbo")

    for cluster in sorted(discovered["phenotype_cluster"].unique()):
        group = discovered[discovered["phenotype_cluster"] == cluster]
        color = cmap(float(cluster) / max(1, int(discovered["phenotype_cluster"].max())))
        name = str(group["phenotype_cluster_name"].iloc[0])
        ax_left.scatter(
            group["mean_speed"],
            group["directional_persistence"],
            s=45,
            alpha=0.85,
            label=name,
            color=color,
        )

    ax_left.set_xlabel("Mean speed (µm/frame)")
    ax_left.set_ylabel("Directional persistence")
    ax_left.set_title("Phenotypes (tracks with ≥3 observations)")
    if not discovered.empty:
        ax_left.legend(loc="best", fontsize=8)
    else:
        ax_left.text(
            0.5,
            0.5,
            "Not enough trajectories with ≥3 observations",
            transform=ax_left.transAxes,
            ha="center",
            va="center",
        )
    ax_left.text(
        0.02,
        0.02,
        f"Excluded from this view: {len(phenotypes) - len(discovered)} short tracks",
        transform=ax_left.transAxes,
        fontsize=8,
    )
    ax_left.grid(alpha=0.2)

    top = discovered.sort_values(
        ["directional_persistence", "mean_speed"], ascending=False
    ).head(6)
    ax_right.axis("off")
    ax_right.text(0.02, 0.96, "Per-cell temporal phenotype", fontsize=17, weight="bold", va="top")
    y = 0.86
    if top.empty:
        ax_right.text(0.02, y, "No eligible trajectories", fontsize=11)
    for row in top.itertuples(index=False):
        label = str(row.phenotype_cluster_name)
        ax_right.text(
            0.02,
            y,
            f"Cell {int(row.track_id):02d}  |  {label}",
            fontsize=11,
        )
        ax_right.text(
            0.05,
            y - 0.035,
            f"speed={float(row.mean_speed):.3f} µm/frame  "
            f"persistence={float(row.directional_persistence):.3f}  "
            f"duration={int(row.duration)} frames",
            fontsize=9,
        )
        y -= 0.12

    fig.suptitle(
        "Stage 3 | Temporal phenotype layer | physical units; short tracks excluded from discovery view",
        fontsize=13,
    )
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def render_validation_notes(path: Path, metrics: dict[str, float | int]) -> None:
    fig, ax = plt.subplots(figsize=(10, 7), dpi=120)
    ax.set_axis_off()
    ax.text(0.05, 0.88, "What this evidence does—and does not—show", fontsize=21, weight="bold")
    ax.text(0.06, 0.72, "VALIDATION", fontsize=12, weight="bold")
    ax.text(
        0.08, 0.64,
        f"Held-out mask F1 @ IoU 0.5: {float(metrics['heldout_mask_f1_iou50']):.3f}",
        fontsize=15,
    )
    ax.text(
        0.08, 0.56,
        f"Centroid detection F1 (6 px): {float(metrics['heldout_centroid_detection_f1_r6px']):.3f}",
        fontsize=15,
    )
    ax.text(
        0.08, 0.48,
        f"Image-derived temporal-link F1: {float(metrics['heldout_tracking_edge_f1']):.3f}",
        fontsize=15,
    )
    ax.text(0.06, 0.36, "INTERPRETATION BOUNDARY", fontsize=12, weight="bold")
    ax.text(
        0.08, 0.29,
        "• Train masks: CTC sequence 02; infer/evaluate raw microscopy: sequence 01",
        fontsize=10.5,
    )
    ax.text(0.08, 0.22, "• CTC training annotations are used only to fit the segmenter.", fontsize=10.5)
    ax.text(0.08, 0.15, "• Cluster groups are descriptive, not validated biological labels.", fontsize=10.5)
    ax.text(0.08, 0.08, "• These are local held-out metrics, not official CTC leaderboard scores.", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def render_summary(path: Path, metrics: dict[str, float | int]) -> None:
    fig, ax = plt.subplots(figsize=(10, 7), dpi=120)
    ax.set_axis_off()
    ax.text(0.05, 0.88, "Temporal Cellular Phenotype Engine", fontsize=24, weight="bold")
    ax.text(0.05, 0.77, "Image-derived end-to-end holdout snapshot", fontsize=15)

    rows = [
        ("Mask F1 @ IoU 0.5", f"{float(metrics['heldout_mask_f1_iou50']):.3f}"),
        ("Detection F1 (centroid, 6 px)", f"{float(metrics['heldout_centroid_detection_f1_r6px']):.3f}"),
        ("Tracking edge F1", f"{float(metrics['heldout_tracking_edge_f1']):.3f}"),
        ("Image-derived observations", str(metrics["image_derived_observations"])),
        ("Predicted tracks", str(metrics["image_derived_tracks"])),
        ("Temporal links", str(metrics["image_derived_temporal_links"])),
    ]
    y = 0.66
    for label, value in rows:
        ax.text(0.07, y, label, fontsize=13)
        ax.text(0.73, y, value, fontsize=16, weight="bold", ha="center")
        y -= 0.085

    ax.text(
        0.05, 0.09,
        "Supervised fit: CTC sequence 02 annotations; inference: raw sequence 01 images.\n"
        "Tracking and phenotype start from the predicted masks, not reference centroids.",
        fontsize=9.5,
        va="bottom",
    )
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    root = prepare_dataset()
    images = image_files(root, SEQ, MAX_FRAMES)
    raw_frames = []
    for image_path in images:
        frame = np.squeeze(tifffile.imread(image_path))
        while frame.ndim > 2:
            frame = frame[0]
        if frame.ndim != 2:
            raise ValueError(f"Expected 2-D grayscale frame at {image_path}; got {frame.shape}")
        raw_frames.append(frame)
    raw_stack = np.stack(raw_frames)
    predicted_masks = np.stack(
        [fit_supervised_segmenter(root).predict_instances(frame) for frame in []]
    ) if False else None
    segmenter = fit_supervised_segmenter(root)
    predicted_masks = np.stack(
        [segmenter.predict_instances(frame) for frame in raw_stack],
        axis=0,
    )

    detections = instances_to_detections(raw_stack, predicted_masks)
    frame_ids = [frame_number(path) for path in images]
    detections["t"] = frame_ids
    predicted, predicted_edges = track_detections(
        detections[["t", "z", "y", "x", "area", "mean_intensity"]],
        TrackingConfig(
            max_distance_um=8.0,
            method="mutual_nn",
            voxel_size_um=VOXEL,
        ),
    )
    metrics = evaluate_demo_run(root, images, predicted_masks, predicted, predicted_edges)
    (ROOT / "ai4s_demo_video_metrics.json").write_text(
        __import__("json").dumps(metrics, indent=2),
        encoding="utf-8",
    )
    print("IMAGE-DERIVED HELD-OUT METRICS")
    print(__import__("json").dumps(metrics, indent=2))

    with tempfile.TemporaryDirectory(prefix="ai4s_demo_") as tmp:
        tmp_path = Path(tmp)
        frame_dir = tmp_path / "frames"
        frame_dir.mkdir()
        for i, image_path in enumerate(images):
            render_frame(
                raw_frames[i],
                predicted,
                frame_ids[i],
                len(images),
                frame_dir / f"frame_{i:04d}.png",
            )

        title_path = tmp_path / "title.png"
        render_title(title_path)
        detection_path = tmp_path / "detection.png"
        mid = min(len(images) - 1, len(images) // 2)
        mid_detections = detections[detections["t"].eq(frame_ids[mid])]
        render_detection(raw_frames[mid], detection_path, mid_detections, predicted_masks[mid])

        phenotype_path = tmp_path / "phenotype.png"
        render_phenotype(phenotype_path, predicted, predicted_edges)
        notes_path = tmp_path / "notes.png"
        render_validation_notes(notes_path, metrics)
        summary_path = tmp_path / "summary.png"
        render_summary(summary_path, metrics)

        output = ROOT / "ai4s_demo_video.mp4"
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-loop", "1",
            "-t", str(3),
            "-i", str(title_path),
            "-framerate", str(FPS),
            "-i", str(frame_dir / "frame_%04d.png"),
            "-loop", "1",
            "-t", str(4),
            "-i", str(detection_path),
            "-loop", "1",
            "-t", str(6),
            "-i", str(phenotype_path),
            "-loop", "1",
            "-t", str(4),
            "-i", str(notes_path),
            "-loop", "1",
            "-t", str(5),
            "-i", str(summary_path),
            "-filter_complex", "[0:v]fps=6[title];[1:v]fps=6[track];[2:v]fps=6[detection];[3:v]fps=6[phenotype];[4:v]fps=6[notes];[5:v]fps=6[summary];[title][track][detection][phenotype][notes][summary]concat=n=6:v=1:a=0[v]",
            "-map", "[v]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output),
        ]
        subprocess.run(cmd, check=True)
        print(output)


if __name__ == "__main__":
    main()

# Render protocol v6: intro + real microscopy + phenotype + synthetic cohort-method validation + validation summary.
