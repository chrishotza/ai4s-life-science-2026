#!/usr/bin/env python3
"""ALFI full MI01-MI04 train; MI05-MI08 heldout raw-image instances.

Frozen estimator and train-only QC originally evaluated in the MI01->MI02-04
pilot. This is a follow-up cross-sequence assessment, NOT tracking/phenotypes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from ai4s_imaging.supervised import Supervised2DSegmenter
from scripts.evaluate_alfi_raw_mi import (
    aggregate, filter_small_predictions, instance_f1_iou50,
    instances_from_binary, load_pair, save_overlay, semantic_metrics,
    train_area_gate,
)

FRAMES = (1, 5, 9, 13)
TRAIN_SEQUENCES = tuple(f"MI{x:02d}" for x in range(1,5))
TEST_SEQUENCES = tuple(f"MI{x:02d}" for x in range(5,9))
TARGET_HEIGHT = 512
TARGET_WIDTH = 640


def pair(inputs: Path, seq: str, frame: int):
    image, mask = load_pair(inputs, seq, frame)
    if image.shape != (TARGET_HEIGHT, TARGET_WIDTH):
        # Preserve the semantic 0/128/255 annotation values with nearest resize.
        image = np.asarray(Image.fromarray(image).resize(
            (TARGET_WIDTH, TARGET_HEIGHT), resample=Image.Resampling.BILINEAR
        ), dtype=np.float32)
        mask = np.asarray(Image.fromarray(mask).resize(
            (TARGET_WIDTH, TARGET_HEIGHT), resample=Image.Resampling.NEAREST
        ))
    return image, mask


def run(inputs: Path, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    train_images = []
    train_instances = []
    for seq in TRAIN_SEQUENCES:
        for t in FRAMES:
            img, mask = pair(inputs, seq, t)
            train_images.append(img)
            train_instances.append(instances_from_binary(mask > 0))
    mask_gate = train_area_gate(train_instances)
    estimator = Supervised2DSegmenter(
        n_estimators=35, max_depth=14, min_samples_leaf=2,
        samples_per_class_per_frame=750, max_training_frames=16,
        min_instance_area=12, max_instance_area=50000, random_state=42,
    ).fit(np.stack(train_images), np.stack(train_instances))
    records = []
    for seq in TEST_SEQUENCES:
        for t in FRAMES:
            img, gt = pair(inputs, seq, t)
            predicted = estimator.predict_instances(img)
            decisions = {
                "repo_supervised_multi_sequence": predicted,
                "repo_multi_sequence_train_size_gate":
                    filter_small_predictions(predicted, mask_gate),
                "brightness_p92": instances_from_binary(
                    img >= np.percentile(img,92)
                ),
            }
            for name, labels in decisions.items():
                measures = semantic_metrics(gt, labels)
                matches = instance_f1_iou50(
                    instances_from_binary(gt > 0), labels
                )
                records.append(dict(
                    sequence=seq, frame=t, model=name,
                    **measures, **matches
                ))
                if t == 1 and name in (
                    "repo_supervised_multi_sequence", "brightness_p92"
                ):
                    save_overlay(
                        img, gt, labels,
                        output/f"{seq}_{name}_overlay.png"
                    )
            finished = [r for r in records
                        if r["sequence"] == seq and r["frame"] == t]
            print(f"{seq} T{t}: model Dice={finished[0]['dice']:.4f}, "
                  f"instance F1={finished[0]['instance_f1_iou50']:.4f}, "
                  f"gate instance F1={finished[1]['instance_f1_iou50']:.4f}",
                  flush=True)
        # Checkpoint after each heldout sequence, so a later failed sample
        # cannot erase the successfully processed groups.
        partial = {
            name: aggregate([r for r in records if r["model"] == name])
            for name in decisions
        }
        (output/"partial_metrics.json").write_text(
            json.dumps(dict(processed=len(records)//3, metrics=partial),indent=2)
        )
    models = list(decisions)
    report = dict(
        status="ALFI_RAW_IMAGE_FOUR_SEQUENCE_DOMAIN_TRAIN_HELDOUT_TEST",
        train_sequences=TRAIN_SEQUENCES, heldout_sequences=TEST_SEQUENCES,
        train_frames=FRAMES, evaluation_frames=FRAMES,
        n_train_images=len(train_images),
        n_test_images=len(TEST_SEQUENCES)*len(FRAMES),
        model="Fixed repo Supervised2DSegmenter; 35 trees depth14",
        train_only_area_gate=mask_gate,
        semantic_gt="ALFI mask values 0 background,128 interphase,255 mitosis",
        resolution=(TARGET_HEIGHT,TARGET_WIDTH),
        metrics={
            name: aggregate([r for r in records if r["model"] == name])
            for name in models
        },
        per_sequence={
            seq: {
                name: aggregate([r for r in records if r["model"] == name
                                 and r["sequence"] == seq])
                for name in models
            } for seq in TEST_SEQUENCES
        },
        per_frame=records,
        claim_limits=(
            "MI01-MI04 images/masks used to train a supervised mask model. "
            "MI05-MI08 image/mask labels are held out from training; some "
            "were used in prior distinct ALFI oracle-track phenotype research. "
            "Only four sparse frames per sequence, half-scale/resize. "
            "Pixel and instance segmentation only, NOT tracking or biological "
            "phenotype prediction; class labels 128/255 are merged as cell "
            "foreground. False positives may include unannotated structures. "
            "No post hoc choice of the best evaluation model or cutoff."
        ),
    )
    (output/"summary.json").write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(json.dumps(report["metrics"],indent=2),flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--out", type=Path,
                   default=Path("external_biology/alfi_multi_training/results"))
    args=p.parse_args()
    run(args.inputs,args.out)


if __name__ == "__main__":
    main()
