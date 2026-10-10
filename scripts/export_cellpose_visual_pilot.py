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
from ai4s_tracking import TrackingConfig, track_detections, infer_divisions
from ai4s_imaging.track_colors import track_color_map
from ai4s_imaging.identity_confidence import (
    audit_track_color_continuity, audit_track_color_prefixes,
)
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
           nodes, scores: dict, colors: dict,
           highlighted: set[int] | None = None,
           show_ids: bool = False) -> None:
    gray = normalized_u8(raw)
    raw_im = Image.fromarray(gray, "L").convert("RGB")
    over = raw_im.copy().convert("RGBA")
    # Predicted instance_id is ephemeral. Resolve each mask to persistent track_id.
    frame_nodes = nodes[nodes["t"].eq(i)]
    if frame_nodes["instance_id"].duplicated().any():
        raise ValueError("ambiguous predicted instance-to-track mapping")
    lookup = dict(zip(frame_nodes["instance_id"].astype(int),
                      frame_nodes["track_id"].astype(int)))
    if {int(v) for v in np.unique(mask) if v > 0} != set(lookup):
        raise ValueError("predicted masks do not match tracked instances")
    for lab in np.unique(mask):
        if int(lab) <= 0:
            continue
        ys, xs = np.nonzero(mask == lab)
        if not len(xs):
            continue
        if highlighted is not None and lookup[int(lab)] not in highlighted:
            continue
        hue = colors[lookup[int(lab)]].rgb
        # Fill is deliberately translucent so raw cells remain visible.
        alpha = 47
        subset = Image.new("RGBA", (int(xs.max()-xs.min()+1), int(ys.max()-ys.min()+1)), (*hue, alpha))
        array = np.asarray(mask[ys.min():ys.max()+1, xs.min():xs.max()+1] == lab, dtype=np.uint8) * 255
        over.alpha_composite(Image.composite(subset, Image.new("RGBA", subset.size), Image.fromarray(array, "L")), (int(xs.min()), int(ys.min())))
    overlay = over.convert("RGB")
    od = ImageDraw.Draw(overlay)
    # Tracks computed from the same predicted observations.
    curr = nodes[nodes["t"] <= i]
    for ident, group in curr.groupby("track_id"):
        if highlighted is not None and int(ident) not in highlighted:
            continue
        g = group.sort_values("t")
        color_rgb = colors[int(ident)].rgb
        pts = [(float(r.x), float(r.y)) for r in g.itertuples()]
        if len(pts) >= 2:
            od.line(pts, fill=color_rgb, width=3, joint="curve")
        recent = g.iloc[-1]
        if int(recent.t) == i:
            x, y = float(recent.x), float(recent.y)
            od.ellipse((x-5, y-5, x+5, y+5), fill=color_rgb, outline=(255,255,255), width=2)
            if show_ids:
                od.text((max(0,x+8), max(0,y-22)), f'{int(ident):02d}',
                        font=SM, fill=color_rgb, stroke_width=2,
                        stroke_fill=(5,15,25))
    board = Image.new("RGB", (1280, 720), BG)
    d = ImageDraw.Draw(board)
    d.text((72, 44), "Real CTC microscopy — image-derived predictions", font=B, fill=WHITE)
    d.text((72, 105), f"Sequence {SEQ} / CTC frame {START+i:02d} / 24-frame division window" if START else f"Sequence {SEQ} / frame {i+1:02d} of {N:02d}", font=P, fill=MUTED)
    board.paste(fit_square(raw_im), (108, 160))
    board.paste(fit_square(overlay), (705, 160))
    d.text((108, 620), "RAW MICROSCOPY", font=P, fill=WHITE)
    d.text((705, 620), "CELLPOSESAM-v2 + TRACKS", font=P, fill=CYAN)
    d.text((108, 666), "Only high-continuity predicted tracks are colored; others remain grayscale. Not biological IDs.", font=SM, fill=MUTED)
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
    division_candidates = infer_divisions(
        track_nodes, edges, division_radius_um=5.0,
        voxel_size_um=DIC_C2DH_HELA_VOXEL_SIZE_UM,
    )
    palette = track_color_map(track_nodes, division_candidates)
    audit = audit_track_color_continuity(np.stack(masks), track_nodes)
    stable_ids = {int(k) for k, value in audit.items() if value["eligible"]}
    population_mode = os.environ.get("AI4S_VISUAL_POPULATION_MODE", "0") == "1"
    prefix_audit = (audit_track_color_prefixes(np.stack(masks), track_nodes)
                    if population_mode else {})
    strict = os.environ.get("AI4S_VISUAL_STRICT_IDENTITY", "1") == "1"
    selection = os.environ.get("AI4S_VISUAL_FOCUS_TRACK_IDS", "").strip()
    focused = {int(x.strip()) for x in selection.split(",") if x.strip()} if selection else None
    highlighted = (set(palette) if population_mode else
                   (stable_ids if strict else set(palette)))
    if focused is not None:
        highlighted &= focused
    if not highlighted:
        raise RuntimeError("no predicted track passes the conservative color-continuity gate")
    highlighted_by_frame = []
    for i in range(len(masks)):
        frame_ids = (
            {int(k) for k, row in prefix_audit.items()
             if row["colored_through_frame"] is not None
             and row["first_frame"] <= i <= row["colored_through_frame"]}
            if population_mode else highlighted.copy()
        )
        highlighted_by_frame.append(frame_ids & highlighted)
    print("Color stability audit:", {str(k): v for k, v in audit.items()}, flush=True)
    for i, (im, mask) in enumerate(zip(frames, masks)):
        render(i, im, mask, track_nodes, records[i], palette,
               highlighted_by_frame[i], show_ids=population_mode)
    if population_mode:
        # Preserve exact Cellpose integer instances and tracker ownership.
        # These are predicted outputs, not CTC ground-truth masks.
        np.savez_compressed(OUT / "model_predicted_instances.npz",
                            masks=np.stack(masks).astype(np.int32))
        track_nodes.to_csv(OUT / "model_predicted_track_nodes.csv", index=False)
        edges.to_csv(OUT / "model_predicted_temporal_edges.csv", index=False)
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
        "stable_identity_coloring": True,
        "full_population_mode": population_mode,
        "population_prefix_quality_audit": {str(k): v for k,v in prefix_audit.items()},
        "model_native_colored_ids_by_frame": [sorted(x) for x in highlighted_by_frame],
        "uncertain_predicted_instances_remain_visible_uncolored": True,
        "no_biological_identity_or_division_claim": True,
        "identity_continuity_audit": {str(k): v for k,v in audit.items()},
        "colored_stable_predicted_track_ids": sorted(highlighted),
        "strict_identity_mask_overlap_gate": strict,
        "requested_focus_track_ids": sorted(focused) if focused is not None else None,
        "noneligible_or_nonselected_tracks_remain_gray": True,
        "colors_keyed_by": "model-predicted track_id, NOT per-frame instance_id",
        "lineage_color_family_candidate_tracks": sorted(int(k) for k,v in palette.items() if v.lineage_candidate),
        "lineage_caveat": "Only unambiguous inferred candidates inherit related tones; NOT biological division proof.",
        "frames": records,
        "caveat": "Visual pilot only. NOT the full 168-frame CTC benchmark, which was measured separately. Predicted masks and tracks shown; CTC annotations never substituted for predictions."
    }, indent=2), encoding="utf-8")
    print("Wrote", len(frames), "predicted-mask frames", flush=True)

if __name__ == "__main__":
    main()
