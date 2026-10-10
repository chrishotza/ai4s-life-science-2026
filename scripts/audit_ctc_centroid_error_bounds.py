#!/usr/bin/env python3
"""Conservative geometry bounds for CTC trajectory motility under centroid error.

All distances are in micrometers. This is a mathematical HYPOTHETICAL
sensitivity analysis, not an empirical measurement of segmentation noise.
For a fixed track with n positions, each displaced from its true centroid
by at most epsilon in Euclidean space, by triangle inequalities:

    max(0, P - 2 epsilon (n - 1)) <= P_true <= P + 2 epsilon (n - 1)
    max(0, D - 2 epsilon) <= D_true <= D + 2 epsilon

P is accumulated path length, D is endpoint displacement. Divide bounds
to obtain a conservative interval for directional persistence D_true/P_true
(clip upper bound to 1). This is conditional on correct cell identities and
does not account for track switching, fragmentation or biologic validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

from ai4s_phenotype.confidence import DESCRIPTIVE_OK, gate_phenotype_profiles

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/evidence/ctc/derived_phenotype_features.csv"
STABILITY = ROOT / "docs/evidence/ctc/stability_summary.json"
PIXEL_SIZE_UM = 0.19  # DIC_C2DH_HELA_VOXEL_SIZE_UM=(1, 0.19, 0.19)
ERROR_BOUNDS_UM = (0.0, 0.05, 0.10, 0.25, 0.50, 1.00)
LOW_PERSISTENCE_CUTOFF = 0.20
EXAMPLES = (("02", 21), ("02", 19))


def persistence_interval(
    n: int, path_um: float, displacement_um: float, epsilon_um: float,
) -> tuple[float, float]:
    """Return conservative min/max true persistence at fixed track identity."""
    if not isinstance(n, int) or n < 3:
        raise ValueError("requires a track with at least 3 observations")
    if any(not math.isfinite(v) for v in (path_um, displacement_um, epsilon_um)):
        raise ValueError("non-finite physical units")
    if path_um < 0 or displacement_um < 0 or epsilon_um < 0:
        raise ValueError("negative lengths or error radius")
    if displacement_um > path_um + 1e-8:
        raise ValueError("net displacement exceeds path length")
    min_path = max(0.0, path_um - 2.0 * epsilon_um * (n - 1))
    max_path = path_um + 2.0 * epsilon_um * (n - 1)
    min_displacement = max(0.0, displacement_um - 2.0 * epsilon_um)
    max_displacement = displacement_um + 2.0 * epsilon_um
    lower = min(1.0, min_displacement / max_path) if max_path > 0 else 0.0
    upper = min(1.0, max_displacement / min_path) if min_path > 0 else 1.0
    if lower > upper + 1e-8:
        raise ValueError("invalid persistence interval")
    return max(0.0, lower), max(0.0, upper)


def _classify(lower: float, upper: float, cutoff: float) -> str:
    if upper < cutoff:
        return "certain_below"
    if lower >= cutoff:
        return "certain_at_or_above"
    return "indeterminate"


def generate(features: pd.DataFrame, stability: dict, *, input_sha: str) -> dict:
    required = {
        "sequence", "track_id", "observations", "path_length",
        "displacement", "directional_persistence", "phenotype_reliability_score",
    }
    if missing := (required - set(features.columns)):
        raise ValueError("missing features: " + ", ".join(sorted(missing)))
    d = features.copy()
    d["sequence"] = d["sequence"].astype(str).str.zfill(2)
    d["track_id"] = d["track_id"].astype(int)
    if d[["sequence", "track_id"]].duplicated().any():
        raise ValueError("duplicate track")
    gate = gate_phenotype_profiles(d, stability)
    approved = {(x["sequence"], int(x["track_id"]))
                for x in gate["tracks"]
                if x["interpretation_permission"] == DESCRIPTIVE_OK}
    f = d[d.apply(lambda row: (row["sequence"], int(row["track_id"])) in approved, axis=1)]
    f = f.sort_values(["sequence", "track_id"]).reset_index(drop=True)
    if len(f) != gate["counts"][DESCRIPTIVE_OK]:
        raise AssertionError("production confidence gate mismatch")
    results = []
    for eps in ERROR_BOUNDS_UM:
        rows = []
        for row in f.itertuples(index=False):
            n = int(row.observations)
            path = float(row.path_length)
            displacement = float(row.displacement)
            measured = float(row.directional_persistence)
            low, high = persistence_interval(n, path, displacement, eps)
            if not math.isfinite(measured) or not 0 <= measured <= 1:
                raise ValueError("invalid measured persistence")
            if not math.isclose(measured, displacement / path, rel_tol=1e-7, abs_tol=1e-8):
                raise ValueError("inconsistent derived directional persistence")
            if not (low - 1e-8 <= measured <= high + 1e-8):
                raise AssertionError("observed persistence lies outside its own bounds")
            rows.append({
                "sequence": str(row.sequence),
                "track_id": int(row.track_id),
                "class": _classify(low, high, LOW_PERSISTENCE_CUTOFF),
                "observed_below": bool(measured < LOW_PERSISTENCE_CUTOFF),
                "lower": low,
                "upper": high,
            })
        classifications = {}
        for seq in ("all", *sorted(f["sequence"].unique())):
            group = rows if seq == "all" else [r for r in rows if r["sequence"] == seq]
            classifications[seq] = {
                "n": len(group),
                "observed_below": sum(r["observed_below"] for r in group),
                "certain_below": sum(r["class"] == "certain_below" for r in group),
                "indeterminate": sum(r["class"] == "indeterminate" for r in group),
                "certain_at_or_above": sum(r["class"] == "certain_at_or_above" for r in group),
            }
            counts = classifications[seq]
            if counts["certain_below"] + counts["indeterminate"] + counts["certain_at_or_above"] != counts["n"]:
                raise AssertionError("classification does not partition cohort")
        examples = []
        for seq, track_id in EXAMPLES:
            selected = [r for r in rows if r["sequence"] == seq and r["track_id"] == track_id]
            if len(selected) != 1:
                raise AssertionError("source example track missing")
            item = selected[0]
            examples.append({
                "sequence": seq, "track_id": track_id,
                "persistence_lower": round(item["lower"], 6),
                "persistence_upper": round(item["upper"], 6),
                "classification": item["class"],
            })
        results.append({
            "max_centroid_error_um": eps,
            "max_error_in_image_pixels": round(eps / PIXEL_SIZE_UM, 4),
            "classification_bounds": classifications,
            "measured_example_tracks": examples,
        })
    # Larger bounded coordinate errors cannot create new certain-below or certain-above findings.
    total_low = [r["classification_bounds"]["all"]["certain_below"] for r in results]
    total_high = [r["classification_bounds"]["all"]["certain_at_or_above"] for r in results]
    if total_low != sorted(total_low, reverse=True) or total_high != sorted(total_high, reverse=True):
        raise AssertionError("robust classification must be monotone in uncertainty radius")
    return {
        "status": "CONDITIONAL_GEOMETRIC_BOUNDS_NOT_MEASURED_CENTROID_ERROR",
        "provenance": {
            "source_workflow_run": "37930909373",
            "source_csv": "docs/evidence/ctc/derived_phenotype_features.csv",
            "source_csv_sha256": input_sha,
            "dataset": "DIC-C2DH-HeLa 01 and 02, pretrained CellposeSAM-v2 masks",
            "original_frame_count": 168,
            "input_profiles": len(d),
            "production_gate_descriptive_profiles": len(f),
        },
        "exploratory_persistence_cutoff": LOW_PERSISTENCE_CUTOFF,
        "pixel_size_um_xy": PIXEL_SIZE_UM,
        "scenarios": results,
        "assumptions": [
            "Each tracked center has Euclidean positional error at most epsilon in physical units; epsilon is assumed, not estimated from CTC data.",
            "Identity associations are held fixed: wrong links, division misassignment and fragmented tracks are outside these bounds.",
            "Bounds arise from triangle inequalities on observed path and endpoints, not a synthetic noise-injection experiment or confidence interval.",
            "The 0.20 cutoff is an exploratory computational descriptor, never a validated biological-cell-state threshold.",
            "An indeterminate track is NOT established to change classification; merely its class cannot be guaranteed from these summary statistics.",
            "The same two CTC sequences as the primary run are analyzed; no new external biological measurements were collected.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--stability", type=Path, default=STABILITY)
    parser.add_argument("--output", type=Path, default=Path("/tmp/ctc_centroid_error_bounds.json"))
    args = parser.parse_args()
    raw = args.input.read_bytes()
    data = pd.read_csv(args.input, dtype={"sequence": str})
    stable = json.loads(args.stability.read_text(encoding="utf-8"))
    report = generate(data, stable, input_sha=hashlib.sha256(raw).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, allow_nan=False) + "\n"
    args.output.write_text(payload, encoding="utf-8")
    print(payload, flush=True)


if __name__ == "__main__":
    main()
