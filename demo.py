from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from ai4s_imaging import segment_frames
from ai4s_imaging.synthetic import moving_blobs
from ai4s_tracking import TrackingConfig, infer_divisions, track_detections
from ai4s_phenotype import analyze, discover_phenotypes


frames = moving_blobs(frames=12, height=96, width=96, cells=8, seed=19)
detections = segment_frames(frames, threshold=0.45, min_area=8)

nodes, links = track_detections(
    detections[["t", "z", "y", "x"]],
    TrackingConfig(max_distance_um=5.0),
)
division_edges = infer_divisions(nodes, links, division_radius_um=5.0)
edges = pd.concat([links, division_edges], ignore_index=True)

phenotypes = analyze(nodes, edges)

if len(phenotypes) >= 3:
    discovered = discover_phenotypes(phenotypes, n_clusters=3)
else:
    discovered = phenotypes.assign(
        phenotype_cluster=-1,
        phenotype_cluster_name="insufficient_cells",
    )

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
