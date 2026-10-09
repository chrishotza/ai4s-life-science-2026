"""Export actual CellposeSAM-v2 predictions as readable CTC demo frames.

Produces predicted masks and tracks, not CTC reference annotations.
This is a bounded visualization pilot, not a replacement for the 168-frame
reported benchmark.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

from ai4s_imaging import CellposeSegmenter, instances_to_detections
from ai4s_io import DIC_C2DH_HELA_VOXEL_SIZE_UM, ensure_ctc_dataset
from ai4s_tracking import TrackingConfig, track_detections
from benchmark_ctc_image_e2e import image_files
from benchmark_ctc_tra_supervised import (
    frame_index, keyed_masks, restrict_instances_to_foi, segmentation_score,
)

N = int(os.environ.get("AI4S_VISUAL_FRAMES", "8"))
START = int(os.environ.get("AI4S_VISUAL_START_FRAME", "0"))
SEQ = os.environ.get("AI4S_VISUAL_SEQUENCE", "01")
assert 2 <= N <= 84 and 0 <= START <= 84 - N and SEQ in ("01", "02")
OUT = ROOT / "cellpose_visual_pilot"
OUT.mkdir(exist_ok=True)
P = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
B = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
SM = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 17)
BG = (7, 17, 29)
CYAN = (83, 218, 235)
WHITE = (236, 245, 251)
MUTED = (151, 175, 192)

def normalized_u8(a: np.ndarray) -> np.ndarray:
    x = np.asarray(a, dtype=np.float32)
    lo, hi = np.percentile(x, [1, 99])
    if hi <= lo:
        return np.zeros(x.shape, dtype=np.uint8)
    return np.uint8(np.clip((x - lo) / (hi - lo), 0, 1) * 255)

def fit_square(image: Image.Image, side: int = 466) -> Image.Image:
    out = image.copy()
    out.thumbnail((side, side), Image.Resampling.BILINEAR)
    canvas = Image.new("RGB", (side, side), (11, 23, 34))
    canvas.paste(out, ((side - out.width)//2, (side - out.height)//2))
    return canvas

def color(track_id: int) -> tuple[int, int, int]:
    # Deterministic track colors.
    palette = [(66, 214, 236), (127, 232, 151), (249, 190, 93),
               (208, 140, 246), (252, 142, 135), (136, 177, 255)]
    return palette[int(track_id) % len(palette)]

def render(i: int, raw: np.ndarray, mask: np.ndarray,
           nodes, scores: dict) -> None:
    gray = normalized_u8(raw)
    raw_im = Image.fromarray(gray, "L").convert("RGB")
    over = raw_im.copy().convert("RGBA")
    # Predicted instances only; no GT mask in display.
    for lab in np.unique(mask):
        if int(lab) <= 0:
            continue
        ys, xs = np.nonzero(mask == lab)
        if not len(xs):
            continue
        hue = color(int(lab))
        # Fill is deliberately translucent so raw cells remain visible.
        alpha = 47
        subset = Image.new("RGBA", (int(xs.max()-xs.min()+1), int(ys.max()-ys.min()+1)), (*hue, alpha))
        array = np.asarray(mask[ys.min():ys.max()+1, xs.min():xs.max()+1] == lab, dtype=np.uint8) * 255
        over.alpha_composite(Image.composite(subset, Image.new("RGBA", subset.size), Image.fromarray(array, "L")), (int(xs.min()), int(ys.min())))
    overlay = Image.alpha_composite(over, marks).convert("RGB")
    od = ImageDraw.Draw(overlay)
    # Tracks computed from the same predicted observations.
    curr = nodes[nodes["t"] <= i]
    for ident, group in curr.groupby("track_id"):
        g = group.sort_values("t")
        color_rgb = color(int(ident))
        pts = [(float(r.x), float(r.y)) for r in g.itertuples()]
        if len(pts) >= 2:
            od.line(pts, fill=color_rgb, width=3, joint="curve")
        recent = g.iloc[-1]
        if int(recent.t) == i:
            x, y = float(recent.x), float(recent.y)
            od.ellipse((x-5, y-5, x+5, y+5), fill=color_rgb, outline=(255,255,255), width=2)
    board = Image.new("RGB", (1280, 720), BG)
    d = ImageDraw.Draw(board)
    d.text((72, 44), "Real CTC microscopy — image-derived predictions", font=B, fill=WHITE)
    d.text((72, 105), f"Sequence {SEQ} / CTC frame {START+i:02d} / 24-frame division window" if START else f"Sequence {SEQ} / frame {i+1:02d} of {N:02d}", font=P, fill=MUTED)
    board.paste(fit_square(raw_im), (108, 160))
    board.paste(fit_square(overlay), (705, 160))
    d.text((108, 620), "RAW MICROSCOPY", font=P, fill=WHITE)
    d.text((705, 620), "CELLPOSESAM-v2 + TRACKS", font=P, fill=CYAN)
    d.text((108, 666), "Predictions shown. Reference annotations are used for scoring only.", font=SM, fill=MUTED)
    board.save(OUT / f"pilot_{i:03d}.png")

def main() -> None:
    root = ensure_ctc_dataset(ROOT / ".benchmark_cache")
    paths = image_files(root, SEQ)[START:START+N]
    gt = keyed_masks(root, SEQ)
    model = CellposeSegmenter(
        model_name="cpsam_v2", min_size=200,
        flow_threshold=0.4, cellprob_threshold=0.0, invert=False,
    )
    frames, masks, records = [], [], []
    for p in paths:
        img = np.squeeze(tifffile.imread(p))
        pred = restrict_instances_to_foi(model.predict_instances(img))
        timeidx = frame_index(p)
        score = segmentation_score(np.squeeze(tifffile.imread(gt[timeidx])), pred)
        frames.append(img)
        masks.append(pred)
        records.append({"frame": timeidx, "f1_iou50": float(score["f1_iou50"]),
                        "gt_objects": int(score["gt_objects"]),
                        "predicted_objects": int(score["pred_objects"])})
        print("pilot", records[-1], flush=True)
    detections = instances_to_detections(np.stack(frames), np.stack(masks))
    track_nodes, edges = track_detections(
        detections[["t", "z", "y", "x", "area", "mean_intensity", "instance_id"]],
        TrackingConfig(max_distance_um=8.0, method="mutual_nn",
                       voxel_size_um=DIC_C2DH_HELA_VOXEL_SIZE_UM),
    )
    for i, (im, mask) in enumerate(zip(frames, masks)):
        render(i, im, mask, track_nodes, records[i])
    (OUT / "visual_pilot_metrics.json").write_text(json.dumps({
        "model": "CellposeSAM-v2 cpsam_v2",
        "sequence": SEQ,
        "visualized_frames": len(frames),
        "first_frame_index": frame_index(paths[0]),
        "last_frame_index": frame_index(paths[-1]),
        "window_selection": "CTC metadata selects a candidate division-event neighborhood only" if START else "first N images",
        "aggregate_mean_frame_segmentation_f1": float(np.mean([s["f1_iou50"] for s in records])),
        "predicted_track_count": int(track_nodes["track_id"].nunique()),
        "predicted_temporal_link_count": int(len(edges)),
        "frames": records,
        "caveat": "Visual pilot only. NOT the full 168-frame CTC benchmark, which was measured separately. Predicted masks and tracks shown; CTC annotations never substituted for predictions."
    }, indent=2), encoding="utf-8")
    print("Wrote", len(frames), "predicted-mask frames", flush=True)

if __name__ == "__main__":
    main()
