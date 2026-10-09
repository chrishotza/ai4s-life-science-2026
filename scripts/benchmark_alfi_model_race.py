#!/usr/bin/env python3
"""Frozen cross-domain Cellpose model-family comparison on ALFI MI05-MI08.

This is *inference only* on previously untuned heldout images, no training.
No score from GT is used to change thresholds, model polarity or preproc.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from ai4s_imaging.cellpose_backend import CellposeSegmenter
from scripts.evaluate_alfi_raw_mi import (
    instances_from_binary, semantic_metrics, instance_f1_iou50, load_pair,
    save_overlay,
)

SEQUENCES = ("MI05", "MI06", "MI07", "MI08")
FRAME = 1


def run(inputs: Path, output: Path, model_name: str):
    output.mkdir(exist_ok=True, parents=True)
    detector = CellposeSegmenter(
        model_name=model_name, min_size=200, flow_threshold=.4,
        cellprob_threshold=0, invert=False,
    )
    outputs = []
    file_hashes = []
    for seq in SEQUENCES:
        for kind in ("image", "mask"):
            path = inputs / f"{seq}_{kind}_{FRAME:04d}.png"
            file_hashes.append(dict(file=path.name,
                                    sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        raw, mask = load_pair(inputs, seq, FRAME)
        predicted = detector.predict_instances(raw)
        score = semantic_metrics(mask, predicted)
        objects = instance_f1_iou50(
            instances_from_binary(mask > 0), predicted,
        )
        outputs.append(dict(
            sequence=seq, frame=FRAME, model=model_name, **score, **objects,
        ))
        save_overlay(raw, mask, predicted,
                     output/f"{seq}_{model_name}_overlay.png")
        print(seq, model_name, "F1", objects["instance_f1_iou50"],
              "Dice", score["dice"], "pred", objects["predicted_instances"],flush=True)
    summary = dict(
        status="PRETRAINED_CROSS_DOMAIN_ALFI_INSTANCE_BENCHMARK",
        model=model_name,
        model_weights_unmodified=True,
        test_sequences=list(SEQUENCES), n_images=len(outputs),
        mean_instance_f1_iou50=float(np.mean([
            r["instance_f1_iou50"] for r in outputs
        ])),
        mean_pixel_dice=float(np.mean([r["dice"] for r in outputs])),
        gt_instances=sum(r["gt_instances"] for r in outputs),
        matched_instances=sum(r["matched_iou50"] for r in outputs),
        predicted_instances=sum(r["predicted_instances"] for r in outputs),
        source_sha256=file_hashes,
        per_sequence=outputs,
        limits=(
            "4 predetermined single frames on MI05–MI08, pretrained zero-shot "
            "instance segmentation only, not tracking/mitosis phase phenotype. "
            "Expert masks can omit structures. Cellpose model weights carry "
            "upstream non-commercial training-data and license constraints, "
            "requiring proper rights assessment before reuse."
        ),
    )
    (output/"summary.json").write_text(json.dumps(
        summary,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps(summary, indent=2),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--model",required=True,choices=("cpsam_v2","cpdino-vitb"))
    a=p.parse_args()
    run(a.inputs,a.output,a.model)


if __name__=="__main__":
    main()
