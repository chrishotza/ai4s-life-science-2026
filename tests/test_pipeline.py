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
    assert result.discovery_model is not None

from ai4s_imaging.synthetic import moving_blobs


def test_pipeline_can_start_from_microscopy_frames():
    frames = moving_blobs(frames=8, height=64, width=64, cells=4, seed=7)
    engine = TemporalPhenotypeEngine(
        PipelineConfig(
            detection_threshold=0.45,
            detection_min_area=4,
            tracking=TrackingConfig(max_distance_um=4.0),
            phenotype_clusters=3,
        )
    )

    result = engine.run_frames(frames)

    assert len(result.nodes) > 0
    assert "mean_speed" in result.phenotypes.columns
