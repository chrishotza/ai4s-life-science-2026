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
TESTS = ("MI02", "MI03", "MI04")


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



def train_area_gate(instances: list[np.ndarray]) -> int:
    """Size cutoff fixed using only MI01 expert-mask areas; no test-mask tuning."""
    areas = np.concatenate([
        np.bincount(mask.ravel())[1:] for mask in instances
    ])
    areas = areas[areas >= 12]
    if not len(areas):
        raise ValueError("Training masks contain no valid cell instances")
    return int(max(12, np.floor(0.35 * np.percentile(areas, 10))))


def filter_small_predictions(instances: np.ndarray, cutoff: int) -> np.ndarray:
    labels = np.asarray(instances, dtype=np.int32)
    counts = np.bincount(labels.ravel())
    valid = np.flatnonzero(counts >= cutoff)
    valid = valid[valid > 0]
    remap = np.zeros(len(counts), dtype=np.int32)
    remap[valid] = np.arange(1, len(valid) + 1)
    return remap[labels]


def aggregate(rows: list[dict]) -> dict:
    if not rows:
        return {}
    return dict(
        frames=len(rows),
        mean_dice=float(np.mean([x["dice"] for x in rows])),
        mean_iou=float(np.mean([x["foreground_iou"] for x in rows])),
        mean_instance_f1_iou50=float(np.mean([x["instance_f1_iou50"] for x in rows])),
        total_gt_instances=int(sum(x["gt_instances"] for x in rows)),
        total_predicted_instances=int(sum(x["predicted_instances"] for x in rows)),
        total_matched_iou50=int(sum(x["matched_iou50"] for x in rows)),
        mean_mitosis_recall=(
            float(np.mean([x["mitosis_recall"] for x in rows
                           if x["mitosis_recall"] is not None]))
            if any(x["mitosis_recall"] is not None for x in rows) else None
        ),
    )

def run(directory: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    train_x, train_y = [], []
    sha = []
    for seq in (TRAIN, *TESTS):
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
    area_gate = train_area_gate(train_y)
    records = []
    for seq in TESTS:
        for t in FRAMES:
            image, gt = load_pair(directory, seq, t)
            predicted = model.predict_instances(image)
            predictions = {
                "repo_supervised_raw": predicted,
                "repo_supervised_train_qc_gate":
                    filter_small_predictions(predicted, area_gate),
                "brightness_p92": instances_from_binary(
                    image >= np.percentile(image, 92)
                ),
            }
            for name, proposal in predictions.items():
                metrics = semantic_metrics(gt, proposal)
                detections = instance_f1_iou50(
                    instances_from_binary(gt > 0), proposal
                )
                records.append(dict(
                    sequence=seq, frame=t, model=name,
                    **metrics, **detections,
                ))
                if t in (1, 9):
                    save_overlay(
                        image, gt, proposal,
                        output/f"{seq}_T{t:04d}_{name}_qc.png"
                    )
            results = [x for x in records if x["sequence"] == seq and x["frame"] == t]
            print(f"{seq} T{t:04d}: model Dice={results[0]['dice']:.4f}, "
                  f"gated Dice={results[1]['dice']:.4f}, "
                  f"brightness baseline Dice={results[2]['dice']:.4f}, "
                  f"gated instance F1={results[1]['instance_f1_iou50']:.4f}",
                  flush=True)
    with (output/"per_frame_metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    model_names = ("repo_supervised_raw", "repo_supervised_train_qc_gate",
                   "brightness_p92")
    report = dict(
        status="RAW_IMAGE_HELDOUT_MULTI_SEQUENCE_SUPERVISED_SEGMENTATION",
        dataset="ALFI CC BY", train_sequence=TRAIN, heldout_sequences=list(TESTS),
        development_sequence="MI02",
        new_untouched_assessment_sequences=["MI03", "MI04"],
        train_frames=list(FRAMES), heldout_frames=list(FRAMES),
        image_resolution="original 1024x1280 pixel image subsampled every 2 pixels",
        image_count=(len(TESTS)+1)*len(FRAMES),
        gt_mask_classes={"0":"background","128":"interphase","255":"mitosis"},
        training_mask_area_gate_min_pixels=area_gate,
        gate_rule="35% of MI01 training mask object-area 10th percentile, floor >=12",
        models={
            name: aggregate([x for x in records if x["model"] == name])
            for name in model_names
        },
        per_sequence={
            seq: {
                name: aggregate([
                    x for x in records if x["model"] == name and x["sequence"] == seq
                ]) for name in model_names
            } for seq in TESTS
        },
        limitations=(
            "MI02 was inspected when deciding to study filtering. MI03 and MI04 "
            "were not used for parameter choice. Train masks from MI01 only. "
            "Four sparse frames per sequence, half original resolution. "
            "This measures image segmentation, not phenotype classification "
            "or cell tracking. ALFI masks contain annotated interphase/mitosis "
            "objects but unannotated cellular structures may remain. "
            "No claim of a general segmentation or biomedical predictor."
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
