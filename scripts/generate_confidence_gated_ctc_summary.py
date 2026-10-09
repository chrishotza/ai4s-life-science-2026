#!/usr/bin/env python3
"""Generate a confidence-gated CTC phenotype summary from persisted evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ai4s_phenotype.confidence import artifact_summary, gate_phenotype_profiles


def generate(
    features_path: Path,
    stability_path: Path,
    output_path: Path,
    *,
    min_motion_observations: int = 3,
    reliable_threshold: float = 0.5,
) -> dict:
    features = pd.read_csv(features_path)
    stability = json.loads(stability_path.read_text(encoding="utf-8"))
    gated = gate_phenotype_profiles(
        features,
        stability,
        min_motion_observations=min_motion_observations,
        reliable_threshold=reliable_threshold,
    )
    summary = artifact_summary(gated)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, allow_nan=False), flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--features",
        type=Path,
        default=Path("docs/evidence/ctc/derived_phenotype_features.csv"),
    )
    parser.add_argument(
        "--stability",
        type=Path,
        default=Path("docs/evidence/ctc/stability_summary.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/evidence/ctc/confidence_gated_phenotype_summary.json"),
    )
    parser.add_argument("--min-motion-observations", type=int, default=3)
    parser.add_argument("--reliable-threshold", type=float, default=0.5)
    args = parser.parse_args()
    generate(
        args.features,
        args.stability,
        args.output,
        min_motion_observations=args.min_motion_observations,
        reliable_threshold=args.reliable_threshold,
    )


if __name__ == "__main__":
    main()
