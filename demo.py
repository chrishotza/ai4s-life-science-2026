from __future__ import annotations
from pathlib import Path
import pandas as pd
from ai4s_tracking import track_detections, TrackingConfig
from ai4s_phenotype.phenotype import build_phenotype_table

ROOT = Path(__file__).resolve().parent
detections = pd.read_csv(ROOT / "examples" / "detections.csv")
nodes, edges = track_detections(detections, TrackingConfig(max_distance_um=4.0))
phenotypes = build_phenotype_table(nodes, edges)

print("TRACKING")
print(nodes[["node_id","t","z","y","x","track_id"]].to_string(index=False))
print("
EDGES")
print(edges.to_string(index=False))
print("
PHENOTYPES")
print(phenotypes.to_string(index=False))
