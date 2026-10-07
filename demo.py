from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from ai4s_tracking import TrackingConfig, track_detections
from ai4s_phenotype import analyze


detections = pd.read_csv(ROOT / "examples" / "detections.csv")
nodes, edges = track_detections(
    detections,
    TrackingConfig(max_distance_um=4.0),
)
phenotypes = analyze(nodes, edges)

print("TRACKING")
print(nodes[["node_id", "t", "z", "y", "x", "track_id"]].to_string(index=False))
print("\nEDGES")
print(edges.to_string(index=False))
print("\nPHENOTYPES")
print(phenotypes.to_string(index=False))
