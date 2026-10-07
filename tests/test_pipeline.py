from pathlib import Path

import pandas as pd

from ai4s_tracking import TrackingConfig, track_detections
from ai4s_phenotype import analyze


ROOT = Path(__file__).resolve().parents[1]


def test_tracking_assigns_all_detections_and_preserves_two_tracks():
    detections = pd.read_csv(ROOT / "examples" / "detections.csv")
    nodes, edges = track_detections(detections, TrackingConfig(max_distance_um=4.0))

    assert len(nodes) == len(detections)
    assert nodes["track_id"].notna().all()
    assert nodes["track_id"].nunique() == 2
    assert len(edges) == len(detections) - 2


def test_phenotype_is_one_row_per_track():
    detections = pd.read_csv(ROOT / "examples" / "detections.csv")
    nodes, edges = track_detections(detections, TrackingConfig(max_distance_um=4.0))
    phenotypes = analyze(nodes, edges)

    assert len(phenotypes) == nodes["track_id"].nunique()
    assert set(["track_id", "duration", "observations", "mean_speed", "phenotype_flag"]).issubset(
        phenotypes.columns
    )
    assert not phenotypes["division_event"].any()
