#!/usr/bin/env python3
"""Compose a narrated, full-field, native-identity CTC video from explicit media.

The microscopy input must be a model-native GitHub Actions artifact; this script
must never reinterpret RGB masks or invent temporal identities. Result is a
LOCAL preview until CTC redistribution rights and public Writeup are verified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def digest(path: Path) -> str:
    obj = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            obj.update(block)
    return obj.hexdigest()


def probe(path: Path) -> dict:
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "stream=codec_type,codec_name,width,height:format=duration,size",
        "-of", "json", str(path),
    ]))


def validate_native_population(metadata: dict, native_dir: Path) -> dict:
    if metadata.get("full_population_mode") is not True:
        raise ValueError("requires true full-population native rendering")
    if metadata.get("colors_keyed_by") != (
        "model-predicted track_id, NOT per-frame instance_id"
    ):
        raise ValueError("color palette is not tied to predicted track IDs")
    if metadata.get("uncertain_predicted_instances_remain_visible_uncolored") is not True:
        raise ValueError("must not hide ambiguous cells from raw microscopy")
    if metadata.get("no_biological_identity_or_division_claim") is not True:
        raise ValueError("must not equate model colors with confirmed biology")
    count = metadata.get("visualized_frames")
    frame_ids = metadata.get("model_native_colored_ids_by_frame")
    if count not in (24, 84) or not isinstance(frame_ids, list) or len(frame_ids) != count:
        raise ValueError("invalid source frame count or per-frame color manifest")
    start, end = metadata.get("first_frame_index"), metadata.get("last_frame_index")
    if (count == 24 and (start, end) != (34, 57)) or (
        count == 84 and (start, end) != (0, 83)
    ):
        raise ValueError("unexpected CTC source-frame window")
    if not (native_dir / "model_predicted_instances.npz").is_file():
        raise FileNotFoundError("exact native predicted masks are mandatory")
    if not (native_dir / "model_predicted_track_nodes.csv").is_file():
        raise FileNotFoundError("exact native predicted track IDs are mandatory")
    if not (native_dir / "model_predicted_temporal_edges.csv").is_file():
        raise FileNotFoundError("exact native predicted temporal edges are mandatory")
    if len(list(native_dir.glob("pilot_*.png"))) != count:
        raise ValueError("missing actual sequential PNG render(s)")
    return {"frames": count, "start": start, "end": end,
            "colored_by_frame": [len(ids) for ids in frame_ids],
            "native_predicted_tracks": metadata["predicted_track_count"],
            "native_predicted_edges": metadata["predicted_temporal_link_count"]}


def soundtrack_hash(path: Path) -> str:
    return subprocess.check_output([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", str(path), "-map", "0:a:0", "-c", "copy",
        "-f", "streamhash", "-hash", "SHA256", "-",
    ]).decode().strip()


def compose(source: Path, clip: Path, artifact_dir: Path,
            output: Path, start: float = 14.0, end: float = 30.5) -> dict:
    native_dir = artifact_dir / "cellpose_visual_pilot"
    record = json.loads((native_dir / "visual_pilot_metrics.json").read_text())
    evidence = validate_native_population(record, native_dir)
    original = probe(source)
    predicted = probe(clip)
    if {"video", "audio"} - {s["codec_type"] for s in original["streams"]}:
        raise ValueError("original must contain video and narration")
    if "video" not in {s["codec_type"] for s in predicted["streams"]}:
        raise ValueError("model native film must contain video")
    duration = float(original["format"]["duration"])
    clip_seconds = float(predicted["format"]["duration"])
    if not 100 <= duration <= 180 or not 0 < start < end < duration:
        raise ValueError("unexpected source duration / edit section")
    if not 15.5 <= clip_seconds <= 60:
        raise ValueError("unexpected source microscope film duration")
    factor = (end - start) / clip_seconds
    filtergraph = (
        f"[0:v]trim=start=0:end={start},setpts=PTS-STARTPTS[a];"
        f"[1:v]setpts={factor:.10f}*(PTS-STARTPTS),fps=24,"
        "scale=1280:720:flags=lanczos,setsar=1[b];"
        f"[0:v]trim=start={end}:end={duration},setpts=PTS-STARTPTS[c];"
        "[a][b][c]concat=n=3:v=1:a=0[v]"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(source), "-i", str(clip),
        "-filter_complex", filtergraph, "-map", "[v]", "-map", "0:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "19",
        "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "copy",
        "-t", str(duration), "-movflags", "+faststart", str(output),
    ], check=True)
    outcome = probe(output)
    if abs(float(outcome["format"]["duration"]) - duration) > 0.1:
        raise AssertionError("video did not preserve narrated presentation duration")
    if {s["codec_type"] for s in outcome["streams"]} != {"video", "audio"}:
        raise AssertionError("missing video/audio after rendering")
    if (soundtrack_hash(source) != soundtrack_hash(output)):
        raise AssertionError("narration changed during conversion")
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(output),
                    "-f", "null", "-"], check=True)
    manifest = {
        "status": "LOCAL PREVIEW. NOT KAGGLE-SUBMITTED; RIGHTS UNVERIFIED.",
        "source": str(source), "native_video": str(clip),
        "source_video_sha256": digest(source),
        "native_video_sha256": digest(clip),
        "native_mask_sha256": digest(native_dir / "model_predicted_instances.npz"),
        "finished_video_sha256": digest(output),
        "same_original_soundtrack": True,
        "duration_seconds": float(outcome["format"]["duration"]),
        "scene_interval_sec": [start, end],
        **evidence,
        "claim_boundary": (
            "Same-color regions are *predicted* identities, not experimentally "
            "validated biological tracks. No interpolated microscopy images."
        ),
    }
    output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--clip", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(compose(args.source, args.clip,
                             args.artifact_dir, args.output), indent=2))


if __name__ == "__main__":
    main()
