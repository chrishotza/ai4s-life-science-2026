"""Independent external reviewer: true model-prediction identity audit contracts."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from benchmark_ctc_cellpose import matched_image_identity_audit


def _inputs():
    reference = pd.DataFrame([
        {"node_id": 90, "track_id": 1, "t": 0},
        {"node_id": 91, "track_id": 2, "t": 0},
        {"node_id": 92, "track_id": 1, "t": 1},
        {"node_id": 93, "track_id": 2, "t": 1},
        {"node_id": 94, "track_id": 3, "t": 0},
    ])
    prediction = pd.DataFrame([
        {"node_id": 10, "track_id": 10, "t": 0},
        {"node_id": 11, "track_id": 20, "t": 0},
        {"node_id": 12, "track_id": 20, "t": 1},
        {"node_id": 13, "track_id": 10, "t": 1},
        {"node_id": 14, "track_id": 30, "t": 0},
    ])
    edges = pd.DataFrame([
        {"source_id": 10, "target_id": 13},
        {"source_id": 11, "target_id": 12},
    ])
    return prediction, reference, edges, {10:90, 11:91, 12:92, 13:93}


def test_real_identity_diagnostic_detects_two_cross_swaps_and_excludes_unmatched():
    predicted, reference, edges, mapping = _inputs()
    result = matched_image_identity_audit(predicted, reference, edges, mapping)
    assert result["matched_detections"] == 4
    assert result["unmatched_reference_detections"] == 1
    assert result["unmatched_predicted_detections"] == 1
    assert result["reference_detection_coverage"] == pytest.approx(0.8)
    assert result["pairwise_identity_f1_matched_only"] == 0.0
    assert result["error_profile_matched_only"]["identity_switches"] == 2
    assert result["error_profile_matched_only"]["merged_predicted_tracks"] == 2
    assert result["error_profile_matched_only"]["fragmented_truth_tracks"] == 2
    assert result["not_full_population_identity_recall"] is True


def test_unmatched_everything_cannot_be_reported_as_perfect_identity():
    predicted, reference, edges, _ = _inputs()
    result = matched_image_identity_audit(predicted, reference, edges, {})
    assert result["matched_detections"] == 0
    assert result["reference_detection_coverage"] == 0.0
    assert result["pairwise_identity_f1_matched_only"] is None
    assert result["error_profile_matched_only"] is None


def test_duplicate_reference_match_fails_closed():
    predicted, reference, edges, mapping = _inputs()
    mapping[13] = 90
    with pytest.raises(ValueError, match="multiple predictions"):
        matched_image_identity_audit(predicted, reference, edges, mapping)


def test_cross_frame_match_fails_closed():
    predicted, reference, edges, mapping = _inputs()
    mapping[13] = 91
    with pytest.raises(ValueError, match="different times"):
        matched_image_identity_audit(predicted, reference, edges, mapping)


def test_preserved_identity_scores_one_on_full_matching():
    predicted, reference, _, mapping = _inputs()
    prediction = predicted.copy()
    prediction.loc[prediction["node_id"].eq(12), "track_id"] = 10
    prediction.loc[prediction["node_id"].eq(13), "track_id"] = 20
    edges = pd.DataFrame([
        {"source_id": 10, "target_id": 12},
        {"source_id": 11, "target_id": 13},
    ])
    result = matched_image_identity_audit(prediction, reference, edges, mapping)
    assert result["pairwise_identity_f1_matched_only"] == pytest.approx(1.0)
    assert result["error_profile_matched_only"]["identity_switches"] == 0
