#!/usr/bin/env python3
"""Pretrained Cellpose-SAM on true ALFI unseen MI sequences.

No training on test labels. Expert masks used ONLY for evaluation. Small bounded
image sample; does not establish phenotype classification or track performance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np

from ai4s_imaging.cellpose_backend import CellposeSegmenter
from scripts.evaluate_alfi_raw_mi import (
    instance_f1_iou50, instances_from_binary, load_pair,
    save_overlay, semantic_metrics,
)

SEQUENCES = ("MI02", "MI03", "MI04")
FRAMES = (1, 9)


def execute(inputs: Path, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    model = CellposeSegmenter(
        model_name="cpsam_v2", min_size=200, flow_threshold=0.4,
        cellprob_threshold=0.0, invert=False,
    )
    per_frame = []
    source_hashes = []
    for seq in SEQUENCES:
        for t in FRAMES:
            for kind in ("image", "mask"):
                path = inputs / f"{seq}_{kind}_{t:04d}.png"
                source_hashes.append(dict(
                    path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest()
                ))
            image, reference = load_pair(inputs, seq, t)
            start = time.monotonic()
            instances = model.predict_instances(image)
            elapsed = time.monotonic()-start
            gt_instances = instances_from_binary(reference > 0)
            semantic = semantic_metrics(reference, instances)
            objects = instance_f1_iou50(gt_instances, instances)
            per_frame.append(dict(
                sequence=seq, frame=t, elapsed_seconds=elapsed,
                **semantic, **objects,
            ))
            save_overlay(
                image, reference, instances,
                out/f"{seq}_T{t:04d}_cellpose_qc.png",
            )
            print(f"Cellpose {seq} T{t:04d} Dice={semantic['dice']:.4f} "
                  f"F1@IoU50={objects['instance_f1_iou50']:.4f}, "
                  f"{objects['predicted_instances']} preds, "
                  f"{objects['gt_instances']} expert masks; "
                  f"{elapsed:.1f}sec", flush=True)
    rows = per_frame
    per_sequence = {}
    for seq in SEQUENCES:
        group = [row for row in rows if row["sequence"] == seq]
        per_sequence[seq] = {
            "mean_dice": float(np.mean([r["dice"] for r in group])),
            "mean_instance_f1_iou50": float(np.mean([
                r["instance_f1_iou50"] for r in group
            ])),
            "gt": sum(r["gt_instances"] for r in group),
            "predicted": sum(r["predicted_instances"] for r in group),
            "matched": sum(r["matched_iou50"] for r in group),
        }
    result = dict(
        status="PRETRAINED_RAW_IMAGE_INSTANCE_ASSESSMENT",
        source="ALFI, Antonelli et al., CC BY",
        model="Cellpose cpsam_v2, upstream pretrained weights, CPU",
        test_sequences=list(SEQUENCES),
        frames_per_sequence=list(FRAMES),
        model_not_finetuned=True,
        image_sampling="every second original pixel, fixed 512×640",
        mean_dice=float(np.mean([r["dice"] for r in rows])),
        mean_instance_f1_iou50=float(np.mean([
            r["instance_f1_iou50"] for r in rows
        ])),
        gt_total=int(sum(r["gt_instances"] for r in rows)),
        detected_total=int(sum(r["predicted_instances"] for r in rows)),
        matched_total=int(sum(r["matched_iou50"] for r in rows)),
        per_sequence=per_sequence,
        per_frame=rows,
        input_sha256=source_hashes,
        limits=(
            "Only 6 hand-fixed ALFI frames, not a whole-sequence or biological "
            "validation. This pretrained instance detector is evaluated against "
            "expert semantic-mask connected components, which may omit other "
            "cells/structures. No image-based mitosis-stage phenotype predictions "
            "or credible cell tracks are calculated."
        ),
    )
    (out/"summary.json").write_text(
        json.dumps(result, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(json.dumps({
        "status": result["status"],
        "mean_dice": result["mean_dice"],
        "mean_instance_f1_iou50": result["mean_instance_f1_iou50"],
        "per_sequence": per_sequence,
    }, indent=2), flush=True)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("external_biology/alfi_cellpose"))
    a = p.parse_args()
    execute(a.inputs, a.out)


if __name__ == "__main__":
    main()
