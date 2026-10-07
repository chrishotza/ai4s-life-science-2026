from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ai4s_imaging import segment_frames
from ai4s_phenotype import PhenotypeDiscoveryModel, analyze
from ai4s_tracking import TrackingConfig, infer_divisions, track_detections


@dataclass(frozen=True)
class PipelineConfig:
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    detection_threshold: float | None = None
    detection_min_area: int = 12
    detection_z: float = 0.0
    division_radius_um: float = 5.0
    phenotype_clusters: int = 3
    phenotype_random_state: int = 17
    phenotype_scaler: str = "standard"
    phenotype_log_transform: bool = False

    def __post_init__(self) -> None:
        if self.detection_min_area < 1:
            raise ValueError("detection_min_area must be >= 1")
        if self.division_radius_um <= 0:
            raise ValueError("division_radius_um must be positive")
        if self.phenotype_clusters < 2:
            raise ValueError("phenotype_clusters must be at least 2")


@dataclass(frozen=True)
class PipelineResult:
    nodes: pd.DataFrame
    temporal_edges: pd.DataFrame
    lineage_edges: pd.DataFrame
    phenotypes: pd.DataFrame
    discovered: pd.DataFrame
    discovery_model: PhenotypeDiscoveryModel | None


class TemporalPhenotypeEngine:
    """Single orchestration boundary from detections to temporal phenotype."""

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()

    def run_frames(self, frames: np.ndarray) -> PipelineResult:
        detections = segment_frames(
            frames,
            threshold=self.config.detection_threshold,
            min_area=self.config.detection_min_area,
            z=self.config.detection_z,
        )
        return self.run(detections)

    def run(self, detections: pd.DataFrame) -> PipelineResult:
        nodes, temporal_edges = track_detections(
            detections[["t", "z", "y", "x"]],
            self.config.tracking,
        )
        lineage_edges = infer_divisions(
            nodes,
            temporal_edges,
            division_radius_um=self.config.division_radius_um,
            voxel_size_um=self.config.tracking.voxel_size_um,
        )
        edges = pd.concat(
            [temporal_edges, lineage_edges],
            ignore_index=True,
        )
        phenotypes = analyze(nodes, edges)
        discovery_model = None
        if len(phenotypes) >= self.config.phenotype_clusters:
            discovery_model = PhenotypeDiscoveryModel.fit(
                phenotypes,
                n_clusters=self.config.phenotype_clusters,
                random_state=self.config.phenotype_random_state,
                scaler=self.config.phenotype_scaler,
                log_transform=self.config.phenotype_log_transform,
            )
            discovered = discovery_model.transform(phenotypes)
        else:
            discovered = phenotypes.assign(
                phenotype_cluster=-1,
                phenotype_cluster_name="insufficient_cells",
            )
        return PipelineResult(
            nodes=nodes,
            temporal_edges=temporal_edges,
            lineage_edges=lineage_edges,
            phenotypes=phenotypes,
            discovered=discovered,
            discovery_model=discovery_model,
        )
