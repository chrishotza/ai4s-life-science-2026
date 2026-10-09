"""Confidence gates for interpreting temporal phenotype profiles.

The gates here are intentionally conservative. They do not validate a
biological phenotype; they only state what kind of computational claim is
permitted by each trajectory's temporal evidence and reliability score.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

STATUS = "CONFIDENCE_GATED_PHENOTYPE_INTERPRETATION"
AUDIT_ONLY = "audit_only"
DESCRIPTIVE_LOW_CONFIDENCE = "descriptive_low_confidence"
DESCRIPTIVE_OK = "descriptive_ok"
BLOCKED_BIOLOGICAL_CLAIM = "blocked_biological_claim"
DESCRIPTIVE_COMPUTATIONAL_GROUP_ONLY = "descriptive_computational_group_only"


def _bootstrap_median(stability_summary: dict[str, Any], cohort: str) -> float | None:
    try:
        return float(
            stability_summary["cohorts"][cohort]["stratified_track_bootstrap_ari"]["median"]
        )
    except KeyError:
        return None


def _count(values: list[str], ordered_keys: list[str]) -> dict[str, int]:
    counts = Counter(values)
    return {key: int(counts.get(key, 0)) for key in ordered_keys}


def _track_row(
    row: pd.Series, *, min_motion_observations: int, reliable_threshold: float,
) -> dict[str, Any]:
    observations = int(row["observations"])
    reliability = float(row["phenotype_reliability_score"])
    integrity = row.get("track_integrity_score")
    if observations < min_motion_observations:
        permission = AUDIT_ONLY
        gate = BLOCKED_BIOLOGICAL_CLAIM
        reason = "insufficient_temporal_evidence"
    elif reliability < reliable_threshold:
        permission = DESCRIPTIVE_LOW_CONFIDENCE
        gate = BLOCKED_BIOLOGICAL_CLAIM
        reason = "low_phenotype_reliability"
    else:
        permission = DESCRIPTIVE_OK
        gate = DESCRIPTIVE_COMPUTATIONAL_GROUP_ONLY
        reason = "sufficient_temporal_evidence"
    return {
        "sequence": str(row["sequence"]),
        "track_id": str(row["track_id"]),
        "observations": observations,
        "phenotype_reliability_score": reliability,
        "track_integrity_score": None if pd.isna(integrity) else float(integrity),
        "interpretation_permission": permission,
        "claim_gate": gate,
        "primary_reason": reason,
    }


def gate_phenotype_profiles(
    features: pd.DataFrame,
    stability_summary: dict[str, Any],
    *,
    min_motion_observations: int = 3,
    reliable_threshold: float = 0.5,
) -> dict[str, Any]:
    """Return conservative interpretation gates for phenotype profiles.

    The returned per-track gates preserve every trajectory as audit evidence,
    while preventing short or low-reliability tracks from being summarized as
    biological phenotypes. A `descriptive_ok` track is still only a
    computational trajectory group, not a named biological state.
    """
    required = {"sequence", "track_id", "observations", "phenotype_reliability_score"}
    missing = sorted(required - set(features.columns))
    if missing:
        raise ValueError(f"Missing required phenotype columns: {', '.join(missing)}")
    if min_motion_observations < 2:
        raise ValueError("min_motion_observations must be at least 2")
    if not 0 <= reliable_threshold <= 1:
        raise ValueError("reliable_threshold must be in [0, 1]")

    ordered = features.sort_values(["sequence", "track_id"]).reset_index(drop=True)
    tracks = [
        _track_row(
            row,
            min_motion_observations=min_motion_observations,
            reliable_threshold=reliable_threshold,
        )
        for _, row in ordered.iterrows()
    ]
    permissions = [track["interpretation_permission"] for track in tracks]
    gates = [track["claim_gate"] for track in tracks]
    permission_counts = _count(
        permissions, [AUDIT_ONLY, DESCRIPTIVE_LOW_CONFIDENCE, DESCRIPTIVE_OK],
    )
    gate_counts = _count(
        gates, [BLOCKED_BIOLOGICAL_CLAIM, DESCRIPTIVE_COMPUTATIONAL_GROUP_ONLY],
    )
    counts = {
        "total_profiles": int(len(tracks)),
        AUDIT_ONLY: permission_counts[AUDIT_ONLY],
        DESCRIPTIVE_LOW_CONFIDENCE: permission_counts[DESCRIPTIVE_LOW_CONFIDENCE],
        DESCRIPTIVE_OK: permission_counts[DESCRIPTIVE_OK],
        BLOCKED_BIOLOGICAL_CLAIM: gate_counts[BLOCKED_BIOLOGICAL_CLAIM],
        DESCRIPTIVE_COMPUTATIONAL_GROUP_ONLY: gate_counts[DESCRIPTIVE_COMPUTATIONAL_GROUP_ONLY],
        "by_interpretation_permission": permission_counts,
        "by_claim_gate": gate_counts,
    }
    return {
        "status": STATUS,
        "dataset": stability_summary.get("dataset"),
        "policy": {
            "min_motion_observations": int(min_motion_observations),
            "reliable_threshold": float(reliable_threshold),
            "short_track_rule": (
                "Tracks with fewer than min_motion_observations are retained "
                "for audit only and blocked from motion-phenotype claims."
            ),
            "reliability_rule": (
                "Tracks meeting the temporal-history threshold but below the "
                "reliability threshold are descriptive_low_confidence."
            ),
        },
        "provenance": {
            "source_workflow_run": stability_summary.get("source_workflow_run"),
            "source_commit": stability_summary.get("source_commit"),
            "source_file_sha256": stability_summary.get("source_file_sha256"),
            "source_evidence_url": stability_summary.get("source_evidence_url"),
            "stability_status": stability_summary.get("status"),
        },
        "counts": counts,
        "stability_context": {
            "all_track_bootstrap_median_ari": _bootstrap_median(stability_summary, "all"),
            "min_3_observations_track_bootstrap_median_ari": _bootstrap_median(
                stability_summary, "min_3_observations",
            ),
            "reliability_ge_0_5_track_bootstrap_median_ari": _bootstrap_median(
                stability_summary, "reliability_ge_0_5",
            ),
            "min_3_observations_profiles": stability_summary.get("cohorts", {})
            .get("min_3_observations", {})
            .get("n_profiles"),
            "reliability_ge_0_5_profiles": stability_summary.get("cohorts", {})
            .get("reliability_ge_0_5", {})
            .get("n_profiles"),
        },
        "tracks": tracks,
        "interpretation_boundary": (
            "Confidence gates describe computational evidence quality only. "
            "They do not validate biological cell states, drug responses, "
            "or transfer to new microscopy domains."
        ),
    }


def artifact_summary(report: dict[str, Any]) -> dict[str, Any]:
    """Return the compact, stable artifact form without per-track rows."""
    return {
        key: value
        for key, value in report.items()
        if key != "tracks"
    }
