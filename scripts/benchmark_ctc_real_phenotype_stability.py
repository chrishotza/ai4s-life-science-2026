#!/usr/bin/env python3
"""Real-data CTC phenotype clustering stability on the actual Cellpose output.

* Canonical product fit/transform on 126 image-derived phenotype profiles.
* Seed robustness and sequence-stratified trajectory bootstrap robustness.
* Quality sensitivity (all, >=3 observations, reliability >=0.5).
* Internal unsupervised stability only, NOT validated biological cell states.

Input files are the original CTC Cellpose end-to-end validation artifact
(2026-10-09, GitHub Actions run 37930909373). Source SHA-256 is verified
against its provenance JSON before reading. No raw microscopy redistributed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, silhouette_score

from ai4s_phenotype.discovery import FEATURES, PhenotypeDiscoveryModel

EXPECTED_SOURCE_RUN = "37930909373"


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_original_artifact(folder: Path) -> tuple[pd.DataFrame, dict]:
    provenance_file = folder / "ctc_cellpose_e2e_provenance.json"
    provenance = json.loads(provenance_file.read_text(encoding="utf-8"))
    if str(provenance.get("workflow_run_id")) != EXPECTED_SOURCE_RUN:
        raise ValueError("Unexpected source experiment/workflow ID")

    files = [
        ("01", "sequence_01_phenotypes"),
        ("02", "sequence_02_phenotypes"),
    ]
    frames = []
    for seq, reference_key in files:
        filename = folder / f"ctc_cellpose_phenotypes_seq{seq}.csv"
        expected = provenance["sha256"][reference_key]
        observed = checksum(filename)
        if observed != expected:
            raise ValueError(
                f"CTC Cellpose source checksum mismatch for sequence {seq}"
            )
        frame = pd.read_csv(filename)
        frame.insert(0, "sequence", seq)
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True)
    if len(data) != 126 or data["sequence"].value_counts().to_dict() != {
        "01": 79, "02": 47,
    }:
        raise ValueError("Original complete-sequence phenotype counts changed")
    return data, provenance


def stability_for_cohort(
    cohort: pd.DataFrame, *, n_seeds: int = 20, n_bootstrap: int = 80,
    seed: int = 20261009,
) -> dict:
    if len(cohort) < 9:
        raise ValueError("Insufficient profiles for stability analysis")
    ref = PhenotypeDiscoveryModel.fit(
        cohort, n_clusters=3, random_state=17, scaler="standard",
    )
    original = ref.transform(cohort)["phenotype_cluster"].to_numpy(dtype=int)
    seed_ari = []
    for state in range(n_seeds):
        candidate = PhenotypeDiscoveryModel.fit(
            cohort, n_clusters=3, random_state=state, scaler="standard",
        )
        labels = candidate.transform(cohort)["phenotype_cluster"].to_numpy(dtype=int)
        seed_ari.append(float(adjusted_rand_score(original, labels)))

    rng = np.random.default_rng(seed)
    sequence = cohort["sequence"].to_numpy()
    seq_groups = {
        name: np.flatnonzero(sequence == name)
        for name in sorted(set(sequence))
    }
    boot_ari = []
    for _ in range(n_bootstrap):
        # Preserve both real imaging sequences. Resample complete trajectories,
        # not correlated feature rows; one profile corresponds to one track.
        sampled = np.concatenate([
            rng.choice(ix, size=len(ix), replace=True)
            for ix in seq_groups.values()
        ])
        trained = PhenotypeDiscoveryModel.fit(
            cohort.iloc[sampled], n_clusters=3, random_state=17,
            scaler="standard",
        )
        assigned = trained.transform(cohort)["phenotype_cluster"].to_numpy(dtype=int)
        boot_ari.append(float(adjusted_rand_score(original, assigned)))

    transformed = ref.scaler.transform(cohort[FEATURES].fillna(0.0).to_numpy(float))
    return {
        "n_profiles": int(len(cohort)),
        "n_sequences": len(seq_groups),
        "n_single_observation": int((cohort["observations"] == 1).sum()),
        "n_shorter_than_three": int((cohort["observations"] < 3).sum()),
        "cluster_counts": [
            int(v) for v in np.bincount(original, minlength=3)
        ],
        "silhouette_index": float(silhouette_score(transformed, original)),
        "seed_ari": {
            "n_fits": n_seeds,
            "min": float(np.min(seed_ari)),
            "median": float(np.median(seed_ari)),
            "mean": float(np.mean(seed_ari)),
            "max": float(np.max(seed_ari)),
        },
        "stratified_track_bootstrap_ari": {
            "n_refits": n_bootstrap,
            "min": float(np.min(boot_ari)),
            "p05": float(np.percentile(boot_ari, 5)),
            "median": float(np.median(boot_ari)),
            "p95": float(np.percentile(boot_ari, 95)),
            "max": float(np.max(boot_ari)),
            "definition": (
                "ARI vs full-data baseline, predicting the SAME full cohort "
                "from models fit on sequence-stratified resampled trajectories; "
                "not a confidence interval on biological truth."
            ),
        },
    }


def run(
    input_dir: Path, output_dir: Path, *,
    n_seeds: int = 20, n_bootstrap: int = 80,
) -> dict:
    data, provenance = read_original_artifact(input_dir)
    if (data["track_id"].isna().any()
            or data.duplicated(["sequence", "track_id"]).any()):
        raise ValueError("Repeated or invalid trajectory IDs in source data")
    if not np.isfinite(data[FEATURES].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite phenotype feature value")
    sections = {
        "all": data,
        "min_3_observations": data[data["observations"] >= 3].copy(),
        "reliability_ge_0_5": data[
            data["phenotype_reliability_score"] >= 0.5
        ].copy(),
    }
    outcomes = {
        name: stability_for_cohort(
            sub.reset_index(drop=True),
            n_seeds=n_seeds, n_bootstrap=n_bootstrap,
        ) for name, sub in sections.items()
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    stable_features = ["sequence", "track_id", *FEATURES,
                       "phenotype_reliability_score",
                       "track_integrity_score"]
    snapshot = data[stable_features].copy()
    snapshot.to_csv(output_dir / "ctc_derived_phenotype_features.csv", index=False)
    report = {
        "status": "EMPIRICAL_UNSUPERVISED_CLUSTER_STABILITY_NOT_BIOLOGICAL_VALIDATION",
        "dataset": "CTC DIC-C2DH-HeLa, CellposeSAM-v2, seq01+seq02, 168 frames",
        "source_workflow_run": EXPECTED_SOURCE_RUN,
        "source_commit": provenance["commit_sha"],
        "source_file_sha256": {
            seq: provenance["sha256"][key]
            for seq, key in (("01", "sequence_01_phenotypes"),
                             ("02", "sequence_02_phenotypes"))
        },
        "source_evidence_url": (
            "https://github.com/chrishotza/ai4s-life-science-2026/"
            "actions/runs/37930909373"
        ),
        "features": list(FEATURES),
        "method": (
            "Actual PhenotypeDiscoveryModel with KMeans(k=3,n_init=30), "
            "StandardScaler and random_state=17; seeds 0...n-1; "
            "sequence-stratified bootstrap resampling trajectory rows."
        ),
        "total_profiles": int(len(data)),
        "total_single_observation_tracks": int(
            (data["observations"] == 1).sum()
        ),
        "cohorts": outcomes,
        "interpretation_boundary": (
            "Descriptive stability of algorithm-generated trajectory groups, "
            "not biological ground truth, drug-response separation, "
            "generalization to new batches, or evidence of named phenotypes. "
            "Cohorts and quality thresholds were selected after inspecting "
            "the source output; no inferential p-values are reported. "
            "Sequence-specific original cluster numbers are not compared: "
            "ALL clustering is refit on pooled profiles for each cohort."
        ),
    }
    (output_dir / "stability_summary.json").write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, allow_nan=False), flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifact-directory", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--seeds", type=int, default=20)
    p.add_argument("--bootstraps", type=int, default=80)
    args = p.parse_args()
    if args.seeds < 2 or args.bootstraps < 2:
        p.error("At least two seeds and bootstrap replicates required")
    run(args.artifact_directory, args.output_dir,
        n_seeds=args.seeds, n_bootstrap=args.bootstraps)


if __name__ == "__main__":
    main()
