#!/usr/bin/env python3
"""Independent regression audit for frozen real CTC silver-center measurements.

Does NOT download microscopy images, run Cellpose or re-estimate centroids.
It cross-checks individual exported offsets, matching coverage, per-sequence
summaries and provenance against the frozen validated inference artifact.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/"docs/evidence/ctc/cellpose_centroid_reference_16_frames.json"
MATCHES=ROOT/"docs/evidence/ctc/cellpose_centroid_matches_16_frames.csv"


def percentile(values: list[float], q: float) -> float:
    if not values or not 0<=q<=100:
        raise ValueError("Need nonempty data and quantile between 0 and 100")
    x=sorted(values)
    rank=(len(x)-1)*q/100
    i=int(rank)
    j=min(i+1,len(x)-1)
    return x[i]+(rank-i)*(x[j]-x[i])


def audit(report: dict, csv_bytes: bytes) -> dict:
    if report.get("status")!="EMPIRICAL_OFFSET_TO_CTC_SILVER_SEGMENTATION_CENTROID":
        raise ValueError("Wrong evidence protocol or missing silver-boundary status")
    if "SILVER" not in report["experiment"]["reference_type"].upper():
        raise ValueError("Not correctly identified as silver reference")
    if hashlib.sha256(csv_bytes).hexdigest()!=report["experiment"]["per_match_csv_sha256"]:
        raise ValueError("CSV checksum mismatches completed inference")
    rows=list(csv.DictReader(csv_bytes.decode("utf-8").splitlines()))
    if not rows:
        raise ValueError("Matched-object CSV empty")
    sample=report["experiment"]["sampled_frame_ids"]
    if len(sample.get("01",[]))!=8 or len(sample.get("02",[]))!=8:
        raise ValueError("Sampling protocol must preserve eight frames per sequence")
    seen_ref=set()
    seen_pred=set()
    distance={}
    for r in rows:
        key=(r["sequence"],int(r["frame"]))
        if r["sequence"] not in ("01","02") or key[1] not in sample[r["sequence"]]:
            raise ValueError("Matched instance outside preselected frame window")
        gid=(*key,int(r["silver_label"]))
        pid=(*key,int(r["predicted_label"]))
        if gid in seen_ref or pid in seen_pred:
            raise ValueError("Violated one-to-one object matching")
        seen_ref.add(gid)
        seen_pred.add(pid)
        if not .5<=float(r["iou"])<=1:
            raise ValueError("Unmatched / invalid IoU record")
        dy=(float(r["predicted_center_y_px"])-float(r["reference_center_y_px"]))*0.19
        dx=(float(r["predicted_center_x_px"])-float(r["reference_center_x_px"]))*0.19
        physical=math.hypot(dx,dy)
        if not math.isclose(physical,float(r["offset_um"]),abs_tol=1e-6):
            raise ValueError("Error distance not consistent with physical pixel scale")
        if not math.isclose(math.hypot(
            float(r["predicted_center_y_px"])-float(r["reference_center_y_px"]),
            float(r["predicted_center_x_px"])-float(r["reference_center_x_px"]),
        ),float(r["offset_pixels"]),abs_tol=1e-6):
            raise ValueError("Pixel-coordinate offset inconsistent")
        if physical<0 or not math.isfinite(physical):
            raise ValueError("Non-finite offset")
        distance.setdefault(r["sequence"],[]).append(float(r["offset_um"]))
    for seq in ("01","02","all"):
        values=distance["01"]+distance["02"] if seq=="all" else distance[seq]
        summary=report["pooled"] if seq=="all" else report["by_sequence"][seq]
        if len(values)!=summary["matched_instances"]:
            raise ValueError("Matched-object count differs from frozen report")
        stats=summary["centroid_offset_um"]
        calculated={
            "median":statistics.median(values),
            "mean":statistics.fmean(values),
            "p90":percentile(values,90),
            "p95":percentile(values,95),
            "max":max(values),
            "rmse":math.sqrt(statistics.fmean(v*v for v in values)),
        }
        for name,v in calculated.items():
            if not math.isclose(v,float(stats[name]),abs_tol=1e-6):
                raise ValueError(f"{seq} {name} differs from measured CSV")
        if summary["reference_instances"]<len(values):
            raise ValueError("More matched reference objects than annotated")
        if summary["predicted_instances"]<len(values):
            raise ValueError("More matches than model instances")
    if report["experiment"]["total_sampled_frames"]!=16:
        raise ValueError("Total sampled frame count differs")
    frames=report["per_frame"]
    if len(frames)!=16:
        raise ValueError("Missing frame score")
    expected={(s,t) for s,v in sample.items() for t in v}
    if {(f["sequence"],f["frame"]) for f in frames}!=expected:
        raise ValueError("Frame manifests differ")
    for f in frames:
        key=(f["sequence"],f["frame"])
        count=sum((r["sequence"],int(r["frame"]))==key for r in rows)
        if count!=f["matched_instances_iou50"]:
            raise ValueError(f"Frame {key} has inconsistent matched count")
        ref=f["reference_instances"]
        pred=f["predicted_instances"]
        actual=2*count/(ref+pred) if ref+pred else 1
        if not math.isclose(actual,f["frame_f1_iou50"],abs_tol=1e-12):
            raise ValueError("Frame F1 inconsistent with matched counts")
    return {
        "verified_matched_objects":len(rows),
        "median_offset_um":round(statistics.median(distance["01"]+distance["02"]),6),
        "p95_offset_um":round(percentile(distance["01"]+distance["02"],95),6),
        "source_csv_sha256":report["experiment"]["per_match_csv_sha256"],
    }


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report",type=Path,default=REPORT)
    p.add_argument("--csv",type=Path,default=MATCHES)
    a=p.parse_args()
    print(json.dumps(audit(json.loads(a.report.read_text(encoding="utf-8")),a.csv.read_bytes()),indent=2))


if __name__=="__main__":
    main()
