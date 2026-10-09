#!/usr/bin/env python3
"""ALFI true-image supervised segmenter: train MI01, test unseen MI02.

Uses repo's Supervised2DSegmenter and original images/masks, NOT phenotype
classifications. Masks encode background=0, interphase=128, mitosis=255.
Fixed sparse frames and half-resolution CPU budget are disclosed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.optimize import linear_sum_assignment

from ai4s_imaging.supervised import Supervised2DSegmenter

FRAMES = (1, 5, 9, 13)
TRAIN = "MI01"
TEST = "MI02"


def load_pair(directory: Path, seq: str, frame: int) -> tuple[np.ndarray, np.ndarray]:
    image = np.asarray(Image.open(directory / f"{seq}_image_{frame:04d}.png"))
    raw_mask = np.asarray(Image.open(directory / f"{seq}_mask_{frame:04d}.png"))
    if image.ndim != 2 or raw_mask.ndim != 2 or image.shape != raw_mask.shape:
        raise ValueError(f"Invalid or unaligned ALFI image/mask: {seq} T{frame}")
    values = set(np.unique(raw_mask).tolist())
    if not values <= {0, 128, 255}:
        raise ValueError(f"Unexpected ALFI semantic mask values: {values}")
    if 128 not in values and 255 not in values:
        raise ValueError(f"No annotated cellular foreground: {seq} T{frame}")
    return image[::2, ::2].astype(np.float32), raw_mask[::2, ::2]


def instances_from_binary(binary: np.ndarray, min_area: int = 12) -> np.ndarray:
    labels, n = ndimage.label(binary)
    if n == 0:
        return labels.astype(np.int32)
    counts = np.bincount(labels.ravel(), minlength=n+1)
    remap = np.zeros(n+1, dtype=np.int32)
    good = np.flatnonzero(counts >= min_area)
    good = good[good > 0]
    remap[good] = np.arange(1, len(good)+1)
    return remap[labels]


def semantic_metrics(mask: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    gt, pd = mask > 0, pred > 0
    tp = int(np.count_nonzero(gt & pd))
    fp = int(np.count_nonzero(~gt & pd))
    fn = int(np.count_nonzero(gt & ~pd))
    return dict(
        dice=float(2*tp / max(2*tp+fp+fn, 1)),
        foreground_iou=float(tp / max(tp+fp+fn, 1)),
        precision=float(tp / max(tp+fp, 1)),
        recall=float(tp / max(tp+fn, 1)),
        interphase_recall=float(np.mean(pd[mask == 128])) if np.any(mask == 128) else None,
        mitosis_recall=float(np.mean(pd[mask == 255])) if np.any(mask == 255) else None,
    )


def instance_f1_iou50(gt_instances: np.ndarray, predicted: np.ndarray) -> dict:
    actual = instances_from_binary(gt_instances > 0)
    pred = instances_from_binary(predicted > 0)
    n_gt, n_pd = int(actual.max()), int(pred.max())
    if not n_gt or not n_pd:
        return dict(gt_instances=n_gt, predicted_instances=n_pd,
                    matched_iou50=0, instance_f1_iou50=0.0)
    pairs = np.bincount(
        (actual.ravel().astype(np.int64)*(n_pd+1) + pred.ravel()),
        minlength=(n_gt+1)*(n_pd+1),
    ).reshape(n_gt+1, n_pd+1)[1:, 1:]
    gs = np.bincount(actual.ravel(), minlength=n_gt+1)[1:]
    ps = np.bincount(pred.ravel(), minlength=n_pd+1)[1:]
    unions = gs[:, None] + ps[None, :] - pairs
    iou = np.divide(pairs, unions, out=np.zeros_like(pairs, dtype=float),
                    where=unions > 0)
    rows, cols = linear_sum_assignment(-iou)
    tp = int(np.count_nonzero(iou[rows, cols] >= 0.5))
    return dict(
        gt_instances=n_gt, predicted_instances=n_pd,
        matched_iou50=tp,
        instance_f1_iou50=float(2*tp/max(n_gt+n_pd, 1)),
    )


def save_overlay(image: np.ndarray, mask: np.ndarray, pred: np.ndarray, dest: Path) -> None:
    lo, hi = np.percentile(image, (2, 98))
    gray = np.uint8(np.clip((image-lo)/max(hi-lo, 1), 0, 1)*255)
    rgb = np.repeat(gray[..., None], 3, axis=-1)
    actual_edges = (mask > 0) ^ ndimage.binary_erosion(mask > 0)
    detected_edges = (pred > 0) ^ ndimage.binary_erosion(pred > 0)
    rgb[actual_edges] = [255, 65, 60]
    rgb[detected_edges] = [60, 255, 95]
    Image.fromarray(rgb).save(dest)


def run(directory: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    train_x, train_y = [], []
    sha = []
    for seq in (TRAIN, TEST):
        for t in FRAMES:
            for name in ("image", "mask"):
                file = directory / f"{seq}_{name}_{t:04d}.png"
                sha.append(dict(file=file.name, sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
            image, mask = load_pair(directory, seq, t)
            if seq == TRAIN:
                train_x.append(image)
                train_y.append(instances_from_binary(mask > 0))
    (output/"source_sha256.json").write_text(json.dumps(sha, indent=2), encoding="utf-8")
    model = Supervised2DSegmenter(
        n_estimators=35, max_depth=14, min_samples_leaf=2,
        samples_per_class_per_frame=750,
        max_training_frames=4, min_instance_area=12,
        max_instance_area=50000, random_state=42,
    ).fit(np.stack(train_x), np.stack(train_y))
    records = []
    for t in FRAMES:
        image, gt = load_pair(directory, TEST, t)
        pred_model = model.predict_instances(image)
        # Reproducible intensity threshold: fixed per-image bright 92nd percentile.
        baseline = instances_from_binary(image >= np.percentile(image, 92))
        for name, prediction in (("repo_supervised", pred_model),
                                 ("brightness_p92", baseline)):
            metrics = semantic_metrics(gt, prediction)
            detection = instance_f1_iou50(
                instances_from_binary(gt > 0), prediction
            )
            records.append(dict(
                sequence=TEST, frame=t, model=name,
                **metrics, **detection,
            ))
            if t in (1, 9):
                save_overlay(image, gt, prediction, output/f"MI02_T{t:04d}_{name}_qc.png")
        print(f"MI02 T{t:04d} true mask={int(np.count_nonzero(gt))} pixels; "
              f"repo Dice={records[-2]['dice']:.4f}, "
              f"baseline Dice={records[-1]['dice']:.4f}", flush=True)
    with (output/"per_frame_metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    models = {}
    for name in ("repo_supervised", "brightness_p92"):
        rows = [x for x in records if x["model"] == name]
        models[name] = dict(
            mean_dice=float(np.mean([x["dice"] for x in rows])),
            mean_iou=float(np.mean([x["foreground_iou"] for x in rows])),
            mean_instance_f1_iou50=float(np.mean([x["instance_f1_iou50"] for x in rows])),
            total_gt_instances=int(sum(x["gt_instances"] for x in rows)),
            total_predicted_instances=int(sum(x["predicted_instances"] for x in rows)),
            total_matched_iou50=int(sum(x["matched_iou50"] for x in rows)),
            mean_mitosis_recall=float(np.mean([x["mitosis_recall"] for x in rows
                                               if x["mitosis_recall"] is not None])),
        )
    report = dict(
        status="RAW_IMAGE_SUPERVISED_SEGMENTATION_WITH_EXPERT_MASKS",
        dataset="ALFI CC BY", train_sequence=TRAIN, heldout_sequence=TEST,
        train_frames=list(FRAMES), heldout_frames=list(FRAMES),
        image_resolution="original image sampled every 2 pixels in x and y",
        image_count=8, gt_mask_classes={"0":"background","128":"interphase",
                                       "255":"mitosis"},
        model="repo Supervised2DSegmenter; 35 RF trees; MI01 masks only",
        metrics=models,
        warnings=(
            "Very small, deliberately selected smoke-test of 2 sequences and 4 "
            "frames per sequence; not independent external validation, "
            "not raw-image phase-of-mitosis classification, not a phenotype or "
            "tracking benchmark. Foreground masks include annotated interphase "
            "and mitosis cells only; unannotated structures count as background."
        ),
    )
    (output/"summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("external_biology/alfi_raw_metrics"))
    args = parser.parse_args()
    run(args.inputs, args.out)


if __name__ == "__main__":
    main()
