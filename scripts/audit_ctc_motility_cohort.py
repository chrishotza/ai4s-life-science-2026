#!/usr/bin/env python3
"""Auditable DESCRIPTIVE sensitivity analysis of image-derived CTC motility.

All values are computed from the existing, frozen 168-frame CellposeSAM-v2
trajectory export. This script does not conduct new biological validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ai4s_phenotype.confidence import DESCRIPTIVE_OK, gate_phenotype_profiles

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FEATURES = ROOT / "docs/evidence/ctc/derived_phenotype_features.csv"
DEFAULT_STABILITY = ROOT / "docs/evidence/ctc/stability_summary.json"

# Pre-declared computational sensitivity rules, NOT validated cell-state thresholds.
COHORT_RULES = (
    ("standard", 3, 0.50),
    ("at_least_10_observations", 10, 0.50),
    ("at_least_20_observations", 20, 0.50),
    ("reliability_at_least_0_65", 3, 0.65),
    ("at_least_10_and_reliability_0_65", 10, 0.65),
)
PERSISTENCE_CUTS = (0.10, 0.20)
EXAMPLE_TRACKS = (("02", 21), ("02", 19))


def _rounded_median(values: pd.Series) -> float | None:
    return round(float(values.median()), 6) if len(values) else None


def _validate_raw_features(features: pd.DataFrame) -> None:
    needed = {
        "sequence", "track_id", "observations", "path_length",
        "displacement", "mean_speed", "directional_persistence",
        "phenotype_reliability_score", "track_integrity_score",
    }
    missing = sorted(needed - set(features.columns))
    if missing:
        raise ValueError("Missing required feature columns: " + ", ".join(missing))
    if features[["sequence", "track_id"]].duplicated().any():
        raise ValueError("Duplicate (sequence, track_id) identities.")
    number_cols = sorted(needed - {"sequence"})
    if not np.isfinite(features[number_cols].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite cell-motion measurement found.")
    if (features["observations"] < 1).any():
        raise ValueError("Invalid temporal observation count.")
    for col in ("path_length", "displacement", "mean_speed"):
        if (features[col] < 0).any():
            raise ValueError("Negative physical motion measure: " + col)
    if (features["displacement"] > features["path_length"] + 1e-8).any():
        raise ValueError("Net displacement exceeds path length.")
    for col in ("directional_persistence", "phenotype_reliability_score",
                "track_integrity_score"):
        if ((features[col] < 0) | (features[col] > 1 + 1e-8)).any():
            raise ValueError("Invalid [0,1] quality/persistence value: " + col)
    eligible = features.loc[
        (features["observations"] >= 3) & (features["path_length"] > 0)
    ]
    ratios = eligible["displacement"] / eligible["path_length"]
    if not np.allclose(
        ratios.to_numpy(), eligible["directional_persistence"].to_numpy(),
        rtol=1e-7, atol=1e-8,
    ):
        raise ValueError("Directional persistence is inconsistent with path and net motion.")


def _cohort(features: pd.DataFrame, minimum: int, reliability: float) -> dict:
    # Reuse production confidence gate instead of reimplementing its semantics.
    eligible = features.loc[
        (features["observations"] >= minimum)
        & (features["phenotype_reliability_score"] >= reliability)
    ].sort_values(["sequence", "track_id"])
    result = {
        "minimum_observations": minimum,
        "minimum_reliability": reliability,
        "n_trajectories": int(len(eligible)),
        "n_by_sequence": {
            str(seq): int((eligible["sequence"] == seq).sum())
            for seq in sorted(features["sequence"].unique())
        },
        "median_directional_persistence": _rounded_median(
            eligible["directional_persistence"]
        ),
        "median_mean_speed_um_per_frame": _rounded_median(eligible["mean_speed"]),
        "median_net_displacement_um": _rounded_median(eligible["displacement"]),
        "persistence_threshold_sensitivity": {},
    }
    result["sequence_stratified_sensitivity"] = {}
    for seq in sorted(features["sequence"].unique()):
        subset = eligible.loc[eligible["sequence"] == seq]
        result["sequence_stratified_sensitivity"][str(seq)] = {
            "n_trajectories": int(len(subset)),
            "persistence_lt_0_20": {
                "count": int((subset["directional_persistence"] < 0.20).sum()),
                "fraction": (
                    round(float((subset["directional_persistence"] < 0.20).mean()), 6)
                    if len(subset) else None
                ),
            },
        }
    for threshold in PERSISTENCE_CUTS:
        n = int((eligible["directional_persistence"] < threshold).sum())
        result["persistence_threshold_sensitivity"][f"lt_{threshold:.2f}"] = {
            "count": n,
            "fraction": round(n / len(eligible), 6) if len(eligible) else None,
        }
    return result


def generate_report(features: pd.DataFrame, stability: dict, *,
                    source_sha256: str = "test-fixture") -> dict:
    data = features.copy()
    data["sequence"] = data["sequence"].astype(str).str.zfill(2)
    data["track_id"] = data["track_id"].astype(int)
    _validate_raw_features(data)
    normal_gate = gate_phenotype_profiles(data, stability)
    baseline_n = normal_gate["counts"][DESCRIPTIVE_OK]
    direct_n = len(data.loc[
        (data["observations"] >= 3)
        & (data["phenotype_reliability_score"] >= 0.50)
    ])
    if baseline_n != direct_n:
        raise AssertionError("Sensitivity cohort disagrees with product's confidence gate.")
    cohorts = {
        label: _cohort(data, minimum, reliability)
        for label, minimum, reliability in COHORT_RULES
    }
    n_standard = cohorts["standard"]["n_trajectories"]
    if n_standard != baseline_n:
        raise AssertionError("Standard cohort has inconsistent track count.")
    for key, minimum, threshold in COHORT_RULES:
        if minimum >= 3 and threshold >= 0.50:
            if cohorts[key]["n_trajectories"] > n_standard:
                raise AssertionError("Stricter gate unexpectedly grows eligible cohort.")

    examples = []
    for seq, tid in EXAMPLE_TRACKS:
        rows = data[(data["sequence"] == seq) & (data["track_id"] == tid)]
        if len(rows) != 1:
            # A test fixture may omit these, but the real report must contain both.
            if source_sha256 != "test-fixture":
                raise AssertionError(f"Real example track {seq}/{tid} is missing")
            continue
        row = rows.iloc[0]
        if row["observations"] < 3 or row["phenotype_reliability_score"] < 0.50:
            raise AssertionError("Example trajectory fails descriptive-confidence gate.")
        examples.append({
            "sequence": seq,
            "track_id": tid,
            "observations": int(row["observations"]),
            "path_length_um": round(float(row["path_length"]), 6),
            "net_displacement_um": round(float(row["displacement"]), 6),
            "mean_speed_um_per_frame": round(float(row["mean_speed"]), 6),
            "directional_persistence": round(float(row["directional_persistence"]), 6),
            "reliability": round(float(row["phenotype_reliability_score"]), 6),
            "selection_policy": "illustrative post-hoc comparison; no inferential test",
        })
    return {
        "status": "DESCRIPTIVE_CTC_MOTILITY_SENSITIVITY_NOT_BIOLOGICAL_VALIDATION",
        "source": {
            "dataset": "CTC DIC-C2DH-HeLa, sequences 01 and 02",
            "raw_image_frames": 168,
            "pretrained_backend": "CellposeSAM-v2",
            "source_workflow_run": "37930909373",
            "committed_feature_csv_sha256": source_sha256,
            "total_image_derived_profiles": int(len(data)),
        },
        "production_confidence_gate_counts": normal_gate["counts"],
        "sensitivity_cohorts": cohorts,
        "measured_illustrative_examples": examples,
        "interpretation_boundary": (
            "Analysis of existing model-predicted tracks, not new independent "
            "biological experiments. Cutpoints 0.10/0.20 for persistence are "
            "exploratory computational descriptors, not biological states. "
            "Sequence differences are descriptive and do not establish generalization. The two sequences are not independent biological replicates. Segmentation centroid jitter or track fragmentation may inflate traveled path. "
            "No causal, drug-response, or cross-domain generalization claim."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--features", type=Path, default=DEFAULT_FEATURES)
    p.add_argument("--stability", type=Path, default=DEFAULT_STABILITY)
    p.add_argument("--output", type=Path, default=Path("/tmp/ctc_motility_cohort_audit.json"))
    args = p.parse_args()
    raw = args.features.read_bytes()
    data = pd.read_csv(args.features, dtype={"sequence": str})
    stability = json.loads(args.stability.read_text(encoding="utf-8"))
    report = generate_report(data, stability, source_sha256=hashlib.sha256(raw).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(report, indent=2, allow_nan=False) + "\n"
    args.output.write_text(serialized, encoding="utf-8")
    print(serialized, flush=True)


if __name__ == "__main__":
    main()
