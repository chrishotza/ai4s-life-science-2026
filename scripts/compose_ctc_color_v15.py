#!/usr/bin/env python3
"""Compose a public-judge-facing demo from *verified* real model-prediction media.

Replace the old V13 pilot scene with the stable-identity 24-frame CTC film,
keeping the original soundtrack, measured claims and all other scenes. The
source video and the real model-rendered clip are externally supplied media,
not included in this repository; respect upstream CTC redistribution rights.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

START = 14.0
END = 30.5


def probe(path: Path) -> dict:
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries",
        "format=duration,size:stream=codec_type,codec_name,width,height",
        "-of", "json", str(path),
    ]))


def compose(source: Path, colored: Path, evidence: Path, output: Path) -> dict:
    record = json.loads(evidence.read_text(encoding="utf-8"))
    if (record.get("stable_identity_coloring") is not True
            or record.get("visualized_frames") != 24
            or record.get("first_frame_index") != 34
            or record.get("last_frame_index") != 57
            or record.get("colors_keyed_by")
            != "model-predicted track_id, NOT per-frame instance_id"):
        raise ValueError("supplied colored clip lacks matching real-image provenance")
    original, clip = probe(source), probe(colored)
    if not {"audio", "video"}.issubset(
        x["codec_type"] for x in original["streams"]
    ):
        raise ValueError("original narration and video are both required")
    if not any(x["codec_type"] == "video" for x in clip["streams"]):
        raise ValueError("colored clip has no video stream")
    duration = float(original["format"]["duration"])
    clip_duration = float(clip["format"]["duration"])
    if duration < 110 or not 15.5 <= clip_duration <= 17.0:
        raise ValueError("video durations do not match controlled cut plan")
    stretch = (END - START) / clip_duration
    graph = (
        f"[0:v]trim=start=0:end={START},setpts=PTS-STARTPTS[a];"
        f"[1:v]setpts={stretch:.9f}*(PTS-STARTPTS),fps=24,"
        "scale=1280:720:flags=lanczos,setsar=1[b];"
        f"[0:v]trim=start={END}:end={duration},setpts=PTS-STARTPTS[c];"
        "[a][b][c]concat=n=3:v=1:a=0[v]"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(source), "-i", str(colored),
        "-filter_complex", graph, "-map", "[v]", "-map", "0:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "copy",
        "-t", str(duration), "-movflags", "+faststart", str(output),
    ], check=True)
    completed = probe(output)
    if (abs(float(completed["format"]["duration"]) - duration) > .10
            or {"audio", "video"} !=
            {s["codec_type"] for s in completed["streams"]}
            or output.stat().st_size <= 1500000):
        raise AssertionError("completed video failed A/V integrity checks")
    manifest = {
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "colored_clip_sha256": hashlib.sha256(colored.read_bytes()).hexdigest(),
        "final_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "duration_seconds": float(completed["format"]["duration"]),
        "replaced_segment_seconds": [START, END],
        "real_data": "CTC raw microscope frames 34-57, sequence 02; predicted model masks",
        "color_policy": "stable by predicted track_id, never ephemeral instance_id",
        "no_interpolation": "video repeats actual photos for playback; no synthetic microscope frames",
        "division_policy": "familial hues are heuristic candidates, not biological proof",
        "public_redistribution": "requires independently checked CTC permissions",
    }
    output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--colored", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(compose(args.source, args.colored,
                             args.evidence, args.output), indent=2))


if __name__ == "__main__":
    main()
