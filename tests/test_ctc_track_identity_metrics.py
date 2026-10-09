import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from benchmark_ctc_phc_psc_association import trajectory_identity_metrics


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
