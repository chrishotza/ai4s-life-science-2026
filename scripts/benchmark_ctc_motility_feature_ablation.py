#!/usr/bin/env python3
"""Reproducible motility-only vs legacy cluster ablation on frozen real CTC tracks.

Descriptive, exploratory and retrospective: no held-out biological labels.
Fit each variant with the actual ai4s_phenotype.PhenotypeDiscoveryModel.
80 paired sequence-stratified resamples of complete trajectories, never frames.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, silhouette_score

from ai4s_phenotype import PhenotypeDiscoveryModel

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/evidence/ctc/derived_phenotype_features.csv"
N_BOOTSTRAP = 80
N_SEEDS = 20
TRAIN_SEED = 17
RESAMPLE_SEED = 20261009
VARIANTS = ("trajectory_lineage", "motion_only")


def analyze_cohort(data: pd.DataFrame) -> dict:
    """Compare feature sets on IDENTICAL profiles and resampling indices."""
    cohort = data.reset_index(drop=True).copy()
    if len(cohort) < 9 or (cohort["observations"] < 3).any():
        raise ValueError("requires >=9 trajectories, all with >=3 observations")
    sequence = cohort["sequence"].astype(str).to_numpy()
    groups = [np.flatnonzero(sequence == s) for s in sorted(set(sequence))]
    if len(groups) != 2 or min(map(len, groups)) < 3:
        raise ValueError("expected both CTC image sequences")

    rng = np.random.default_rng(RESAMPLE_SEED)
    resamples = [
        np.concatenate([rng.choice(g, size=len(g), replace=True) for g in groups])
        for _ in range(N_BOOTSTRAP)
    ]

    results = {}
    for variant in VARIANTS:
        def fitting(frame: pd.DataFrame, seed: int) -> PhenotypeDiscoveryModel:
            return PhenotypeDiscoveryModel.fit(
                frame, n_clusters=3, random_state=seed,
                scaler="standard", feature_set=variant,
            )

        reference = fitting(cohort, TRAIN_SEED)
        original = reference.transform(cohort)["phenotype_cluster"].to_numpy(int)
        x = cohort[list(reference.feature_names)].to_numpy(float)
        scaled = reference.scaler.transform(x)
        silhouette = float(silhouette_score(scaled, original))

        seed_scores = [
            float(adjusted_rand_score(
                original,
                fitting(cohort, seed).transform(cohort)["phenotype_cluster"].to_numpy(int),
            ))
            for seed in range(N_SEEDS)
        ]
        boot_scores = [
            float(adjusted_rand_score(
                original,
                fitting(cohort.iloc[sample], TRAIN_SEED)
                .transform(cohort)["phenotype_cluster"].to_numpy(int),
            ))
            for sample in resamples
        ]
        results[variant] = {
            "feature_names": list(reference.feature_names),
            "cluster_counts": np.bincount(original, minlength=3).astype(int).tolist(),
            "silhouette": silhouette,
            "seed_ari_min": float(np.min(seed_scores)),
            "seed_ari_mean": float(np.mean(seed_scores)),
            "bootstrap_ari_p05": float(np.percentile(boot_scores, 5)),
            "bootstrap_ari_median": float(np.median(boot_scores)),
            "bootstrap_ari_p95": float(np.percentile(boot_scores, 95)),
            "n_seeds": N_SEEDS,
            "n_bootstraps": N_BOOTSTRAP,
        }
    return {
        "profiles": len(cohort),
        "sequences": {str(s): int((sequence == s).sum()) for s in sorted(set(sequence))},
        "results": results,
        "delta_motility_minus_legacy": {
            "silhouette": (results["motion_only"]["silhouette"]
                           - results["trajectory_lineage"]["silhouette"]),
            "bootstrap_ari_median": (
                results["motion_only"]["bootstrap_ari_median"]
                - results["trajectory_lineage"]["bootstrap_ari_median"]
            ),
            "bootstrap_ari_p05": (
                results["motion_only"]["bootstrap_ari_p05"]
                - results["trajectory_lineage"]["bootstrap_ari_p05"]
            ),
        },
    }


def run(path: Path = DATA) -> dict:
    data = pd.read_csv(path, dtype={"sequence": str})
    if len(data) != 126:
        raise ValueError("expected archived 126 real CellposeSAM-v2 trajectories")
    if data["sequence"].value_counts().to_dict() != {"01": 79, "02": 47}:
        raise ValueError("source sequence counts changed")
    if data[["sequence", "track_id"]].duplicated().any():
        raise ValueError("duplicate trajectory identifier")
    required = {
        "observations", "phenotype_reliability_score", "mean_speed",
        "directional_persistence", "duration", "displacement", "path_length",
        "parent_count", "child_count", "descendant_count",
    }
    if missing := required - set(data.columns):
        raise ValueError("missing required columns: " + ",".join(sorted(missing)))
    if not np.isfinite(data[list(required)].to_numpy(dtype=float)).all():
        raise ValueError("nonfinite archived phenotype features")
    if (data["observations"] < 1).any():
        raise ValueError("non-positive observation count")
    eligible = data[data["observations"] >= 3].copy()
    confident = eligible[eligible["phenotype_reliability_score"] >= 0.5].copy()
    if len(eligible) != 72 or len(confident) != 51:
        raise ValueError("frozen confidence cohorts no longer match 72 / 51")
    outcomes = {
        "min_3_observations": analyze_cohort(eligible),
        "descriptive_ok_reliability_ge_0_5": analyze_cohort(confident),
    }
    return {
        "status": "EXPLORATORY_UNSUPERVISED_FEATURE_ABLATION_NOT_BIOLOGICAL_VALIDATION",
        "provenance": {
            "source": "CTC DIC-C2DH-HeLa sequences 01 + 02, 168 raw images, "
                      "CellposeSAM-v2 predicted masks",
            "source_workflow_run": "37930909373",
            "source_csv_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "original_profiles": len(data),
            "singletons": int((data["observations"] == 1).sum()),
        },
        "protocol": {
            "estimator": "Actual repository PhenotypeDiscoveryModel, KMeans(k=3,n_init=30), StandardScaler",
            "paired_sequence_stratified_track_bootstraps": N_BOOTSTRAP,
            "paired_random_seed": RESAMPLE_SEED,
            "seed_refits": N_SEEDS,
            "cohorts": "Retrospective post-hoc quality checks; fit only >=3 observations",
        },
        "cohorts": outcomes,
        "interpretation_limits": (
            "Both approaches cluster the same already-analyzed cell tracks. "
            "Improved internal silhouette/bootstrap median is NOT evidence of "
            "mitosis/biological phenotype accuracy, external generalization, "
            "or a statistically significant difference. The lower bootstrap "
            "tail can worsen. This is an exploratory design ablation after "
            "earlier inspection of the same two microscope sequences."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=DATA)
    p.add_argument("--output", type=Path, default=Path("/tmp/ai4s_motion_ablation.json"))
    args = p.parse_args()
    report = run(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    for cohort, data in report["cohorts"].items():
        print(cohort, data["profiles"], json.dumps(data["delta_motility_minus_legacy"]))
    print("Artifact:", args.output)


if __name__ == "__main__":
    main()
