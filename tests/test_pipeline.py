import pandas as pd

from ai4s_pipeline import PipelineConfig, TemporalPhenotypeEngine
from ai4s_tracking import TrackingConfig


def test_pipeline_exposes_all_temporal_layers():
    detections = pd.DataFrame(
        [
            (0, 0.0, 0.0, 0.0),
            (0, 0.0, 4.0, 0.0),
            (1, 0.0, 0.5, 0.0),
            (1, 0.0, 4.5, 0.0),
            (2, 0.0, 1.0, 0.0),
            (2, 0.0, 5.0, 0.0),
        ],
        columns=["t", "z", "y", "x"],
    )
    engine = TemporalPhenotypeEngine(
        PipelineConfig(
            tracking=TrackingConfig(max_distance_um=2.0),
            division_radius_um=1.5,
            phenotype_clusters=2,
        )
    )
    result = engine.run(detections)

    assert len(result.nodes) == len(detections)
    assert not result.temporal_edges.empty
    assert set(result.phenotypes["track_id"]) == set(result.nodes["track_id"])
    assert "phenotype_cluster" in result.discovered.columns
