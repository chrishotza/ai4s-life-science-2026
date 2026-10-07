from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from ai4s_imaging import segment_frames
from ai4s_imaging.synthetic import moving_blobs
from ai4s_pipeline import PipelineConfig, TemporalPhenotypeEngine
from ai4s_tracking import TrackingConfig


frames = moving_blobs(frames=12, height=96, width=96, cells=8, seed=19)
detections = segment_frames(frames, threshold=0.45, min_area=8)

engine = TemporalPhenotypeEngine(
    PipelineConfig(
        tracking=TrackingConfig(
            max_distance_um=5.0,
            voxel_size_um=(1.0, 1.0, 1.0),
        ),
        division_radius_um=5.0,
        phenotype_clusters=3,
        phenotype_random_state=17,
    )
)
result = engine.run(detections[["t", "z", "y", "x"]])

nodes = result.nodes
links = result.temporal_edges
division_edges = result.lineage_edges
phenotypes = result.phenotypes
discovered = result.discovered

print("INPUT")
print(f"frames={frames.shape[0]}  detections={len(detections)}")

print("\nTRACKING")
print(f"tracks={nodes['track_id'].nunique()}  links={len(links)}")
print(f"candidate_division_edges={len(division_edges)}")

print("\nPHENOTYPES")
print(phenotypes.to_string(index=False))

print("\nDISCOVERED PHENOTYPES")
print(discovered[[
    "track_id",
    "mean_speed",
    "directional_persistence",
    "division_event",
    "phenotype_cluster",
    "phenotype_cluster_name",
]].to_string(index=False))
