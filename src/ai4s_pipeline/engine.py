from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ai4s_phenotype import analyze, discover_phenotypes
from ai4s_tracking import TrackingConfig, infer_divisions, track_detections


@dataclass(frozen=True)
class PipelineConfig:
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    division_radius_um: float = 5.0
    phenotype_clusters: int = 3
    phenotype_random_state: int = 17
    phenotype_scaler: str = "standard"
    phenotype_log_transform: bool = False

    def __post_init__(self) -> None:
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


class TemporalPhenotypeEngine:
    """Single orchestration boundary from detections to temporal phenotype."""

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()

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
        if len(phenotypes) >= self.config.phenotype_clusters:
            discovered = discover_phenotypes(
                phenotypes,
                n_clusters=self.config.phenotype_clusters,
                random_state=self.config.phenotype_random_state,
                scaler=self.config.phenotype_scaler,
                log_transform=self.config.phenotype_log_transform,
            )
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
        )
