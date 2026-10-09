"""Select CTC time-lapse windows that contain annotated division events.

Reference lineage metadata is used ONLY to find an interesting evaluation
window. It must not be used as model predictions or advertised as automatic
division detection.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ai4s_io import ensure_ctc_dataset  # noqa: E402

def read_rows(path: Path) -> list[dict[str, int]]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.strip().split()
        if len(fields) >= 4:
            tid, start, end, parent = map(int, fields[:4])
            records.append({
                "track_id": tid, "start": start,
                "end": end, "parent_id": parent,
            })
    return records

def events_for_sequence(root: Path, seq: str) -> dict:
    rows = read_rows(root / f"{seq}_GT" / "TRA" / "man_track.txt")
    by_id = {r["track_id"]: r for r in rows}
    children = defaultdict(list)
    for r in rows:
        if r["parent_id"] > 0:
            children[r["parent_id"]].append(r)
    events = []
    for parent_id, offspring in children.items():
        if len(offspring) < 2 or parent_id not in by_id:
            continue
        parent = by_id[parent_id]
        daughter_start = min(r["start"] for r in offspring)
        max_t = 83
        start = max(0, daughter_start - 12)
        end = min(max_t, start + 23)
        start = max(0, end - 23)
        viable = (daughter_start - start >= 8 and
                  end - daughter_start >= 6 and
                  all(r["end"] - r["start"] >= 4 for r in offspring[:2]))
        score = (2 if viable else 0) * 100 - abs(42 - daughter_start)
        events.append({
            "parent_track_id": parent_id,
            "parent_end": parent["end"],
            "child_track_ids": [r["track_id"] for r in offspring],
            "children_start": [r["start"] for r in offspring],
            "event_frame": daughter_start,
            "recommended_start_frame": start,
            "recommended_end_frame_inclusive": end,
            "window_frames": end - start + 1,
            "viable_24_frame_window": bool(viable),
            "priority_score": score,
        })
    events.sort(key=lambda e: (-e["priority_score"], e["event_frame"]))
    return {
        "sequence": seq,
        "annotated_track_count": len(rows),
        "annotated_division_parent_count": len(events),
        "candidate_events": events[:20],
    }

def main():
    dataset = ensure_ctc_dataset(ROOT / ".benchmark_cache")
    seqs = [events_for_sequence(dataset, name) for name in ("01", "02")]
    all_ev = [
        {**event, "sequence": seq["sequence"]}
        for seq in seqs for event in seq["candidate_events"]
    ]
    all_ev.sort(key=lambda x: -x["priority_score"])
    out = {
        "method": "GT metadata-only event window discovery",
        "no_model_inference": True,
        "not_evidence_of_automatic_division_detection": True,
        "source": "CTC DIC-C2DH-HeLa / man_track.txt",
        "sequences": seqs,
        "best_window": all_ev[0] if all_ev else None,
        "interpretation_rule": "CTC annotations select the clip only; any segmentation, tracking or division predictions must be computed independently from raw images, then evaluated.",
    }
    path=ROOT / "ctc_division_window_scout.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "event_counts": {x["sequence"]: x["annotated_division_parent_count"] for x in seqs},
        "best_window": out["best_window"],
    }, indent=2))

if __name__ == "__main__":
    main()
