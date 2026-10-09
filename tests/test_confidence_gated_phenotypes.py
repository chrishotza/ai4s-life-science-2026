"""Contracts for confidence-gated phenotype interpretation evidence."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from ai4s_phenotype.confidence import gate_phenotype_profiles


def _features() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "sequence": "01",
            "track_id": 1,
            "observations": 1,
            "phenotype_reliability_score": 0.95,
            "track_integrity_score": 0.90,
        },
        {
            "sequence": "01",
            "track_id": 2,
            "observations": 2,
            "phenotype_reliability_score": 0.90,
            "track_integrity_score": 0.80,
        },
        {
            "sequence": "02",
            "track_id": 3,
            "observations": 3,
            "phenotype_reliability_score": 0.20,
            "track_integrity_score": 0.70,
        },
        {
            "sequence": "02",
            "track_id": 4,
            "observations": 5,
            "phenotype_reliability_score": 0.75,
            "track_integrity_score": 0.85,
        },
    ])


def _stability() -> dict:
    return {
        "status": "EMPIRICAL_UNSUPERVISED_CLUSTER_STABILITY_NOT_BIOLOGICAL_VALIDATION",
        "dataset": "synthetic CTC confidence-gate fixture",
        "source_workflow_run": "37930909373",
        "source_commit": "abc123",
        "source_file_sha256": {"01": "sha01", "02": "sha02"},
        "cohorts": {
            "all": {"stratified_track_bootstrap_ari": {"median": 0.94}},
            "min_3_observations": {
                "n_profiles": 2,
                "stratified_track_bootstrap_ari": {"median": 0.68},
            },
            "reliability_ge_0_5": {
                "n_profiles": 3,
                "stratified_track_bootstrap_ari": {"median": 0.81},
            },
        },
    }


def test_confidence_gate_blocks_short_tracks_from_motion_phenotype_claims():
    report = gate_phenotype_profiles(_features(), _stability())
    per_track = {
        (row["sequence"], row["track_id"]): row
        for row in report["tracks"]
    }

    singleton = per_track[("01", "1")]
    assert singleton["interpretation_permission"] == "audit_only"
    assert singleton["claim_gate"] == "blocked_biological_claim"
    assert singleton["primary_reason"] == "insufficient_temporal_evidence"

    two_frame = per_track[("01", "2")]
    assert two_frame["interpretation_permission"] == "audit_only"
    assert two_frame["claim_gate"] == "blocked_biological_claim"


def test_confidence_gate_separates_low_reliability_from_descriptive_profiles():
    report = gate_phenotype_profiles(_features(), _stability())
    per_track = {
        (row["sequence"], row["track_id"]): row
        for row in report["tracks"]
    }

    low_reliability = per_track[("02", "3")]
    assert low_reliability["interpretation_permission"] == "descriptive_low_confidence"
    assert low_reliability["claim_gate"] == "blocked_biological_claim"
    assert low_reliability["primary_reason"] == "low_phenotype_reliability"

    descriptive = per_track[("02", "4")]
    assert descriptive["interpretation_permission"] == "descriptive_ok"
    assert descriptive["claim_gate"] == "descriptive_computational_group_only"
    assert descriptive["primary_reason"] == "sufficient_temporal_evidence"


def test_confidence_gate_count_summary_is_conserved():
    report = gate_phenotype_profiles(_features(), _stability())
    counts = report["counts"]
    assert counts["total_profiles"] == 4
    assert counts["audit_only"] == 2
    assert counts["descriptive_low_confidence"] == 1
    assert counts["descriptive_ok"] == 1
    assert counts["blocked_biological_claim"] == 3
    assert counts["descriptive_computational_group_only"] == 1
    assert sum(counts["by_interpretation_permission"].values()) == 4
    assert sum(counts["by_claim_gate"].values()) == 4


def test_cli_writes_confidence_gated_summary(tmp_path: Path):
    features_path = tmp_path / "features.csv"
    stability_path = tmp_path / "stability.json"
    output_path = tmp_path / "summary.json"
    _features().to_csv(features_path, index=False)
    stability_path.write_text(json.dumps(_stability()), encoding="utf-8")

    subprocess.run([
        sys.executable,
        "scripts/generate_confidence_gated_ctc_summary.py",
        "--features",
        str(features_path),
        "--stability",
        str(stability_path),
        "--output",
        str(output_path),
    ], check=True)

    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["status"] == "CONFIDENCE_GATED_PHENOTYPE_INTERPRETATION"
    assert report["counts"]["total_profiles"] == 4
    assert report["provenance"]["source_workflow_run"] == "37930909373"
