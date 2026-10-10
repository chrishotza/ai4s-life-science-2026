"""Regression checks for non-inferential CTC trajectory sensitivity audit."""
from __future__ import annotations

import json

import pandas as pd
import pytest

from scripts.audit_ctc_motility_cohort import generate_report


def _features() -> pd.DataFrame:
    return pd.DataFrame([
        {"sequence": "01", "track_id": 1, "observations": 20,
         "path_length": 10.0, "displacement": 2.0, "mean_speed": 0.5,
         "directional_persistence": 0.2, "phenotype_reliability_score": 0.7,
         "track_integrity_score": 0.9},
        {"sequence": "02", "track_id": 2, "observations": 11,
         "path_length": 30.0, "displacement": 0.9, "mean_speed": 3.0,
         "directional_persistence": 0.03, "phenotype_reliability_score": 0.55,
         "track_integrity_score": 0.8},
        {"sequence": "02", "track_id": 3, "observations": 1,
         "path_length": 0.0, "displacement": 0.0, "mean_speed": 0.0,
         "directional_persistence": 0.0, "phenotype_reliability_score": 0.9,
         "track_integrity_score": 1.0},
        {"sequence": "01", "track_id": 4, "observations": 8,
         "path_length": 8.0, "displacement": 4.0, "mean_speed": 1.0,
         "directional_persistence": 0.5, "phenotype_reliability_score": 0.4,
         "track_integrity_score": 0.9},
    ])


def test_stability_to_input_order_and_gate_monotonicity():
    features = _features()
    left = generate_report(features, {}, source_sha256="test-fixture")
    right = generate_report(features.iloc[::-1], {}, source_sha256="test-fixture")
    assert left == right
    assert left["production_confidence_gate_counts"]["descriptive_ok"] == 2
    assert left["production_confidence_gate_counts"]["audit_only"] == 1
    assert left["production_confidence_gate_counts"]["descriptive_low_confidence"] == 1
    cohorts = left["sensitivity_cohorts"]
    assert cohorts["standard"]["n_trajectories"] == 2
    assert cohorts["at_least_10_observations"]["n_trajectories"] == 2
    assert cohorts["at_least_20_observations"]["n_trajectories"] == 1
    assert cohorts["reliability_at_least_0_65"]["n_trajectories"] == 1
    assert cohorts["standard"]["persistence_threshold_sensitivity"]["lt_0.10"] == {
        "count": 1, "fraction": 0.5,
    }
    assert cohorts["standard"]["n_by_sequence"] == {"01": 1, "02": 1}
    assert "NOT_BIOLOGICAL_VALIDATION" in left["status"]
    assert json.loads(json.dumps(left)) == left


def test_rejects_duplicated_track_id_within_sequence():
    features = _features()
    features.loc[3, ["sequence", "track_id"]] = ["02", 2]
    with pytest.raises(ValueError, match="Duplicate"):
        generate_report(features, {})


def test_rejects_inconsistent_movement_geometry():
    features = _features()
    features.loc[0, "directional_persistence"] = 0.6
    with pytest.raises(ValueError, match="inconsistent"):
        generate_report(features, {})


def test_rejects_physically_impossible_displacement():
    features = _features()
    features.loc[0, "displacement"] = 10.1
    with pytest.raises(ValueError, match="exceeds"):
        generate_report(features, {})


def test_rejects_missing_or_non_finite_inputs():
    features = _features()
    with pytest.raises(ValueError, match="Missing"):
        generate_report(features.drop(columns=["path_length"]), {})
    features.loc[0, "mean_speed"] = float("nan")
    with pytest.raises(ValueError, match="Non-finite"):
        generate_report(features, {})
