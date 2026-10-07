from __future__ import annotations

from pathlib import Path
import pandas as pd

from ai4s_tracking import TrackingConfig, track_detections
from ai4s_phenotype import analyze

ROOT = Path(__file__).resolve().parent
detections = pd.read_csv(ROOT / "examples" / "detections.csv")

nodes, edges = track_detections(
    detections,
    TrackingConfig(max_distance_um=4.0),
)

# The phenotype engine expects one node identity across observations.
phenotype_nodes = nodes.copy()
phenotype_nodes["node_id"] = phenotype_nodes["track_id"]

# This demo validates trajectory phenotypes. Lineage/division edges are
# evaluated separately once true division annotations are available.
phenotypes = analyze(
    phenotype_nodes,
    pd.DataFrame(columns=["source_id", "target_id"]),
)

print("TRACKING")
print(nodes[["node_id", "t", "z", "y", "x", "track_id"]].to_string(index=False))
print("\nEDGES")
print(edges.to_string(index=False))
print("\nPHENOTYPES")
print(phenotypes.to_string(index=False))
