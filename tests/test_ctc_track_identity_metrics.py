import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from benchmark_ctc_phc_psc_association import fast_track_detections, trajectory_identity_metrics
from benchmark_ctc_image_e2e import framewise_match
from ai4s_io import PHC_C2DL_PSC_VOXEL_SIZE_UM
from ai4s_tracking import TrackingConfig, track_detections


def test_pairwise_identity_metrics_penalize_track_merges():
    nodes = pd.DataFrame(
        {
            "reference_track_id": [1, 1, 1, 2, 2, 2],
            "track_id": [10, 10, 10, 10, 10, 10],
        }
    )

    result = trajectory_identity_metrics(nodes)

    assert result["identity_precision"] == pytest.approx(0.4)
    assert result["identity_recall"] == pytest.approx(1.0)
    assert result["identity_f1"] == pytest.approx(4 / 7)
    assert result["track_count_ratio"] == pytest.approx(0.5)
    assert result["merged_predicted_tracks"] == 1
    assert result["fragmented_reference_tracks"] == 0


def test_pairwise_identity_metrics_penalize_track_fragmentation():
    nodes = pd.DataFrame(
        {
            "reference_track_id": [1, 1, 1, 1],
            "track_id": [10, 10, 11, 11],
        }
    )

    result = trajectory_identity_metrics(nodes)

    assert result["identity_precision"] == pytest.approx(1.0)
    assert result["identity_recall"] == pytest.approx(1 / 3)
    assert result["identity_f1"] == pytest.approx(0.5)
    assert result["merged_predicted_tracks"] == 0
    assert result["fragmented_reference_tracks"] == 1


def test_pairwise_identity_metrics_reject_missing_reference_ids():
    with pytest.raises(ValueError, match="reference and predicted track IDs"):
        trajectory_identity_metrics(pd.DataFrame({"track_id": [1]}))



def test_unmatched_centroids_do_not_report_zero_error():
    predicted = pd.DataFrame(
        [{"node_id": 20, "t": 0, "y": 0.0, "x": 0.0}]
    )
    truth = pd.DataFrame(
        [{"node_id": 10, "t": 0, "y": 100.0, "x": 100.0}]
    )

    tp, fp, fn, mean_distance, mapping = framewise_match(predicted, truth, radius_px=6.0)

    assert (tp, fp, fn) == (0, 1, 1)
    assert mean_distance is None
    assert mapping == {}

 

@pytest.mark.parametrize(
    "method",
    ["mutual_nn", "mutual_rescue", "hungarian", "velocity_hungarian"],
)
def test_fast_association_paths_match_production_tracker_on_deterministic_fixture(method):
    detections = pd.DataFrame(
        [
            {"t": 0, "z": 0.0, "y": 0.0, "x": 0.0, "reference_track_id": 1},
            {"t": 0, "z": 0.0, "y": 20.0, "x": 20.0, "reference_track_id": 2},
            {"t": 1, "z": 0.0, "y": 1.0, "x": 0.0, "reference_track_id": 1},
            {"t": 1, "z": 0.0, "y": 19.0, "x": 20.0, "reference_track_id": 2},
            {"t": 1, "z": 0.0, "y": 40.0, "x": 40.0, "reference_track_id": 3},
            {"t": 2, "z": 0.0, "y": 2.0, "x": 0.0, "reference_track_id": 1},
            {"t": 2, "z": 0.0, "y": 18.0, "x": 20.0, "reference_track_id": 2},
            {"t": 2, "z": 0.0, "y": 41.0, "x": 40.0, "reference_track_id": 3},
        ]
    )

    fast_nodes, fast_edges = fast_track_detections(detections, 8.0, method=method)
    production_nodes, production_edges = track_detections(
        detections,
        TrackingConfig(
            max_distance_um=8.0,
            method=method,
            voxel_size_um=PHC_C2DL_PSC_VOXEL_SIZE_UM,
        ),
    )

    assert fast_nodes["track_id"].tolist() == production_nodes["track_id"].tolist()
    assert set(zip(fast_edges["source_id"], fast_edges["target_id"])) == set(
        zip(production_edges["source_id"], production_edges["target_id"])
    )
