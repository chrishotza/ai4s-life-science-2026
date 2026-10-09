#!/usr/bin/env python3
"""Scale and polarity ablation of the pretrained ALFI CellposeSAM-v2 backbone.

Post-hoc diagnostic (MI05–MI08 T0001): original 1024x1280 vs 512x640,
and native vs intensity-inverted. All other detection hyperparameters frozen;
test masks are evaluated, never used during inference/parameter fitting.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from ai4s_imaging.cellpose_backend import CellposeSegmenter
from scripts.evaluate_alfi_raw_mi import (
    instance_f1_iou50, instances_from_binary, semantic_metrics, save_overlay,
)

SEQUENCES=("MI05","MI06","MI07","MI08")
VARIANTS={
    "native":dict(downsample=False,invert=False),
    "native-invert":dict(downsample=False,invert=True),
    "half-invert":dict(downsample=True,invert=True),
}


def run(inputs: Path, out: Path, variant: str):
    out.mkdir(parents=True,exist_ok=True)
    config=VARIANTS[variant]
    model=CellposeSegmenter(
        model_name="cpsam_v2",
        min_size=200, flow_threshold=.4,
        cellprob_threshold=0.0, invert=config["invert"],
    )
    frames=[]
    hashes=[]
    for seq in SEQUENCES:
        image_file=inputs/f"{seq}_image_0001.png"
        mask_file=inputs/f"{seq}_mask_0001.png"
        hashes.extend([
            dict(name=f.name,sha256=hashlib.sha256(f.read_bytes()).hexdigest())
            for f in (image_file,mask_file)
        ])
        x=np.asarray(Image.open(image_file))
        y=np.asarray(Image.open(mask_file))
        if x.shape!=(1024,1280) or y.shape!=x.shape:
            raise ValueError("Unexpected ALFI native image/mask dimensions")
        if not set(np.unique(y)) <= {0,128,255}:
            raise ValueError("Unexpected expert mask code")
        if config["downsample"]:
            x=x[::2,::2];y=y[::2,::2]
        x=x.astype(np.float32)
        prediction=model.predict_instances(x)
        semantic=semantic_metrics(y,prediction)
        instances=instance_f1_iou50(
            instances_from_binary(y>0),prediction,
        )
        frames.append(dict(
            sequence=seq,model="cpsam_v2",variant=variant,
            **semantic,**instances,
        ))
        save_overlay(x,y,prediction,out/f"{seq}_{variant}.png")
        print(f"{variant} {seq}: Dice={semantic['dice']:.4f} "
              f"instance-F1={instances['instance_f1_iou50']:.4f} "
              f"pred={instances['predicted_instances']} "
              f"GT={instances['gt_instances']} "
              f"matched={instances['matched_iou50']}",flush=True)
    summary=dict(
        status="ALFI_EXPLORATORY_MODEL_SCALE_POLARITY_ABLATION",
        variant=variant,config=config,frames=frames,sha256=hashes,
        n_test_frames=len(frames),
        mean_dice=float(np.mean([d["dice"] for d in frames])),
        mean_instance_f1_iou50=float(np.mean([d["instance_f1_iou50"] for d in frames])),
        matched_instances=sum(d["matched_iou50"] for d in frames),
        predicted_instances=sum(d["predicted_instances"] for d in frames),
        gt_instances=sum(d["gt_instances"] for d in frames),
        warning=(
            "Only four frames from an ALFI set previously examined in other "
            "research workflows. This is a post-hoc scale/polarity diagnostic, "
            "NOT a novel independent heldout benchmark. Expert mask classes "
            "128 and 255 are merged for instance F1. No actual video-to-phase "
            "prediction was done."
        ),
    )
    (out/"summary.json").write_text(
        json.dumps(summary,indent=2,allow_nan=False),encoding="utf-8"
    )
    print(json.dumps({k:v for k,v in summary.items() if k!="frames" and k!="sha256"},
                     indent=2),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--variant",choices=VARIANTS,required=True)
    args=p.parse_args()
    run(args.inputs,args.out,args.variant)


if __name__=="__main__":
    main()
