#!/usr/bin/env python3
"""Export a genuinely continuous, single-predicted-cell CTC time-lapse.

This visualization re-runs the SAME pretrained CellposeSAM-v2 image→centroid
MNN tracker as the archived 168-frame CTC benchmark; it uses raw pixels and
PREDICTED instance masks only. No reference-mask coordinates enter the display.
It does not establish biological cell identity correctness, mitosis detection,
or out-of-domain biology. Every display frame is an actual microscope TIFF.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_dilation, binary_erosion
import tifffile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

SEQUENCE = "02"
TARGET_TRACK = 21
FRAME_RATE = 4
FRAME_SIZE = (1280, 720)
BG = (7, 17, 29)
INK = (235, 242, 248)
MUTED = (155, 177, 192)
CYAN = (75, 226, 234)
AMBER = (247, 190, 106)
PIXEL_UM = 0.19


def normalize_u8(raw: np.ndarray) -> np.ndarray:
    array = np.asarray(raw, dtype=np.float32)
    if array.ndim != 2 or not np.isfinite(array).all():
        raise ValueError("expected finite 2D raw microscope frame")
    lo, hi = np.percentile(array, (1.0, 99.0))
    if hi <= lo:
        return np.zeros(array.shape, dtype=np.uint8)
    return np.uint8(np.round(255 * np.clip((array - lo) / (hi - lo), 0, 1)))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    suffix = "-Bold" if bold else ""
    try:
        return ImageFont.truetype(
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans{suffix}.ttf", size
        )
    except OSError:
        return ImageFont.load_default()


def timeline(nodes: pd.DataFrame, target_track: int) -> pd.DataFrame:
    selected = nodes[nodes["track_id"].eq(target_track)].sort_values("t").copy()
    if selected.empty:
        raise ValueError(f"target predicted track {target_track} is absent")
    if selected["t"].duplicated().any():
        raise ValueError("selected predicted track contains duplicate frames")
    if len(selected) < 3:
        raise ValueError("selected track has insufficient temporal evidence")
    for column in ("t", "x", "y", "instance_id"):
        if not np.isfinite(selected[column].to_numpy(float)).all():
            raise ValueError(f"nonfinite predicted track field: {column}")
    return selected


def prefix_motion(points: pd.DataFrame) -> dict[str, float | int]:
    """No future-lookahead; compute measurements from observed history only."""
    if points.empty:
        return {"observations": 0, "path_um": 0.0, "net_um": 0.0, "persistence": 0.0}
    p = points[["y", "x"]].to_numpy(float) * PIXEL_UM
    delta = np.diff(p, axis=0)
    path = float(np.linalg.norm(delta, axis=1).sum()) if len(p) > 1 else 0.0
    net = float(np.linalg.norm(p[-1] - p[0]))
    return {
        "observations": len(p),
        "path_um": path,
        "net_um": net,
        "persistence": float(net / path) if path > 0 else 0.0,
    }


def visual_frame(
    raw: np.ndarray,
    predicted_mask: np.ndarray,
    history: pd.DataFrame,
    current_frame: int,
    first_frame: int,
    last_frame: int,
    target_track: int,
) -> Image.Image:
    """Draw real microscope and segmented target; never synthesize cell pixels."""
    if raw.shape != predicted_mask.shape or raw.ndim != 2:
        raise ValueError("raw microscope/mask image dimensions differ")
    original = Image.fromarray(normalize_u8(raw), "L").convert("RGB")
    overlay = original.copy()
    active = history[history["t"].eq(current_frame)]
    if len(active) > 1:
        raise ValueError("ambiguous cell identity within selected video frame")
    if len(active):
        cell = predicted_mask == int(active.iloc[0]["instance_id"])
        if not cell.any():
            raise ValueError("predicted track instance not in predicted mask")
        mask_rgba = np.zeros((*raw.shape, 4), dtype=np.uint8)
        mask_rgba[cell] = (37, 223, 234, 68)
        edge = binary_dilation(cell, iterations=2) & ~binary_erosion(cell)
        mask_rgba[edge] = (84, 244, 250, 235)
        overlay = Image.alpha_composite(
            overlay.convert("RGBA"), Image.fromarray(mask_rgba, "RGBA")
        ).convert("RGB")

    # The same untransformed physical field appears in both panels.
    left = original.resize((500, 500), Image.Resampling.BICUBIC)
    right = overlay.resize((500, 500), Image.Resampling.BICUBIC)
    canvas = Image.new("RGB", FRAME_SIZE, BG)
    draw = ImageDraw.Draw(canvas)
    canvas.paste(left, (65, 137))
    canvas.paste(right, (713, 137))
    draw.rounded_rectangle((62, 134, 567, 640), radius=8, outline=(44, 71, 91), width=2)
    draw.rounded_rectangle((710, 134, 1215, 640), radius=8, outline=(61, 171, 172), width=2)
    # Trail uses only current and earlier model-predicted centroids.
    prior = history[history["t"] <= current_frame].sort_values("t")
    pts = [(713 + 500 * float(r.x) / raw.shape[1],
            137 + 500 * float(r.y) / raw.shape[0],
            int(r.t)) for r in prior.itertuples(index=False)]
    for a, b in zip(pts, pts[1:]):
        if b[2] - a[2] == 1:
            draw.line(((a[0], a[1]), (b[0], b[1])), fill=AMBER, width=4)
    if len(active):
        x = 713 + 500 * float(active.iloc[0]["x"]) / raw.shape[1]
        y = 137 + 500 * float(active.iloc[0]["y"]) / raw.shape[0]
        draw.ellipse((x - 10, y - 10, x + 10, y + 10), outline=INK, width=3)
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=CYAN)
    m = prefix_motion(prior)
    draw.text((64, 24), "ONE CELL. REAL FRAMES. MEASURED MOTION.", font=font(29, True), fill=INK)
    draw.text((65, 77), "CTC DIC-C2DH-HeLa / seq 02 · original imaging order", font=font(19), fill=MUTED)
    draw.text((65, 650), "UNMODIFIED RAW MICROSCOPY", font=font(17, True), fill=INK)
    draw.text((713, 650), f"PREDICTED TRACK {target_track:02d} / MODEL MASK", font=font(17, True), fill=CYAN)
    draw.text((65, 679), f"Frame {current_frame:02d} / {last_frame:02d} · {current_frame-first_frame+1} of {last_frame-first_frame+1}", font=font(16), fill=MUTED)
    draw.text((713, 679), f"Path {m['path_um']:.2f} um  |  Net {m['net_um']:.2f} um  |  N={m['observations']}", font=font(15), fill=INK)
    return canvas


def produce(sequence: str, track_id: int, out_dir: Path, fps: int) -> dict:
    from imageio_ffmpeg import write_frames
    from ai4s_imaging import CellposeSegmenter, instances_to_detections
    from ai4s_io import DIC_C2DH_HELA_VOXEL_SIZE_UM, ensure_ctc_dataset
    from ai4s_tracking import TrackingConfig, track_detections
    from benchmark_ctc_image_e2e import image_files
    from benchmark_ctc_tra_supervised import frame_index, restrict_instances_to_foi

    if sequence != SEQUENCE:
        raise ValueError("this reproducibility experiment is fixed to CTC sequence 02")
    out_dir.mkdir(parents=True, exist_ok=True)
    images = image_files(ensure_ctc_dataset(ROOT / ".benchmark_cache"), sequence)
    if len(images) != 84:
        raise ValueError(f"requires all 84 chronological real TIFFs; got {len(images)}")
    actual = [frame_index(p) for p in images]
    if actual != list(range(84)):
        raise ValueError("unexpected missing or reordered microscope frames")

    model = CellposeSegmenter(
        model_name="cpsam_v2", min_size=200,
        flow_threshold=0.4, cellprob_threshold=0.0, invert=False,
    )
    raw_frames, masks = [], []
    for k, path in enumerate(images):
        frame = np.squeeze(tifffile.imread(path))
        predicted = restrict_instances_to_foi(model.predict_instances(frame))
        raw_frames.append(frame)
        masks.append(predicted)
        print(f"image-derived frame {k+1:02d}/84", flush=True)

    detections = instances_to_detections(np.stack(raw_frames), np.stack(masks))
    detections["t"] = detections["t"].map(dict(enumerate(actual))).astype(int)
    tracked, edges = track_detections(
        detections,
        TrackingConfig(max_distance_um=8.0, method="mutual_nn",
                       voxel_size_um=DIC_C2DH_HELA_VOXEL_SIZE_UM),
    )
    selected = timeline(tracked, track_id)
    times = selected["t"].astype(int).to_numpy()
    first_frame, last_frame = int(times.min()), int(times.max())
    predicted_stats = prefix_motion(selected)
    gaps = sorted(set(range(first_frame, last_frame + 1)) - set(map(int, times)))
    # Guard against accidentally substituting a differently configured inference.
    if track_id == TARGET_TRACK:
        if len(selected) != 66:
            raise AssertionError(f"Expected published 66 observations, got {len(selected)}")
        if abs(predicted_stats["path_um"] - 142.095316) > 0.08:
            raise AssertionError("Predicted track does not reproduce the archived path length")
        if abs(predicted_stats["net_um"] - 4.289433) > 0.08:
            raise AssertionError("Predicted track does not reproduce archived displacement")

    video = out_dir / "ai4s-seq02-track21-continuous.mp4"
    writer = write_frames(str(video), FRAME_SIZE, fps=fps,
                          codec="libx264", pix_fmt_in="rgb24",
                          output_params=["-crf", "19", "-movflags", "+faststart"])
    writer.send(None)
    source_sha = []
    try:
        for t in range(first_frame, last_frame + 1):
            canvas = visual_frame(raw_frames[t], masks[t], selected, t,
                                  first_frame, last_frame, track_id)
            writer.send(np.asarray(canvas).tobytes())
            source_sha.append(hashlib.sha256(images[t].read_bytes()).hexdigest())
    finally:
        writer.close()
    # Visual trace for independent reproducibility / non-interpolation audit.
    export_columns = [c for c in ("node_id", "track_id", "t", "x", "y",
                                   "instance_id", "area", "mean_intensity")
                      if c in selected.columns]
    selected[export_columns].to_csv(out_dir / "predicted_track21_centroids.csv", index=False)
    manifest = {
        "status": "REAL_84_FRAME_INFERENCE_SINGLE_PREDICTED_TRACK_VISUALIZATION",
        "source": "CTC DIC-C2DH-HeLa seq02 raw TIFF; pretrained CellposeSAM-v2",
        "model": "cpsam_v2",
        "tracking": "mutual_nn, 8.0 micrometers, pixel calibration 0.19 um/px",
        "sequence_total_frames": len(images),
        "selected_predicted_track_id": track_id,
        "selected_track_observations": len(selected),
        "chronological_display_first_frame": first_frame,
        "chronological_display_last_frame": last_frame,
        "display_frame_indices": list(range(first_frame, last_frame + 1)),
        "missing_track_detection_frame_indices": gaps,
        "interpolated_cell_positions": 0,
        "actual_raw_tiff_sha256_in_display_order": source_sha,
        "path_um": predicted_stats["path_um"],
        "net_displacement_um": predicted_stats["net_um"],
        "persistence": predicted_stats["persistence"],
        "video_fps": fps,
        "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
        "limitation": (
            "A tracked instance is a predicted identity, not biologically independently "
            "confirmed across every frame. The video uses observed microscopy TIFF frames "
            "only, and no position is interpolated through missing detections. No "
            "reference masks or oracle lineages are used as input."
        ),
    }
    (out_dir / "continuous_track_manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: manifest[k] for k in (
        "selected_track_observations", "chronological_display_first_frame",
        "chronological_display_last_frame", "missing_track_detection_frame_indices",
        "path_um", "net_displacement_um", "video_sha256"
    )}, indent=2), flush=True)
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, default=ROOT / "continuous_cell_demo")
    p.add_argument("--sequence", default="02", choices=("02",))
    p.add_argument("--track-id", type=int, default=21)
    p.add_argument("--fps", type=int, default=FRAME_RATE)
    args = p.parse_args()
    if not 1 <= args.fps <= 24:
        p.error("fps must be 1..24; frames themselves are never interpolated")
    produce(args.sequence, args.track_id, args.output_dir, args.fps)


if __name__ == "__main__":
    main()
