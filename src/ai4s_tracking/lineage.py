from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from ai4s_core import validate_edges, validate_nodes


def infer_divisions(
    nodes: pd.DataFrame,
    links: pd.DataFrame,
    division_radius_um: float = 5.0,
    voxel_size_um: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> pd.DataFrame:
    """Infer candidate parent-to-daughter events from track starts."""
    required_nodes = {"node_id", "track_id", "t", "z", "y", "x"}
    required_links = {"source_id", "target_id"}
    if not required_nodes.issubset(nodes.columns):
        raise ValueError("nodes missing lineage columns")
    if not required_links.issubset(links.columns):
        raise ValueError("links missing lineage columns")

    if division_radius_um <= 0:
        raise ValueError("division_radius_um must be positive")
    if len(voxel_size_um) != 3 or any(value <= 0 for value in voxel_size_um):
        raise ValueError("voxel_size_um must contain three positive values")

    n = nodes.copy()
    validate_nodes(n)
    validate_edges(links, n)
    scale = np.asarray(voxel_size_um, dtype=float)
    incoming = set(links["target_id"].astype(int))
    events = []

    for t in sorted(n["t"].unique())[:-1]:
        cur = n[n["t"] == t]
        nxt = n[n["t"] == t + 1]
        new_tracks = nxt[~nxt["node_id"].astype(int).isin(incoming)]
        if new_tracks.empty:
            continue

        child_records = list(
            new_tracks[["node_id", "track_id", "z", "y", "x"]].itertuples(index=False)
        )
        child_xyz = np.asarray(
            [[row.z, row.y, row.x] for row in child_records],
            dtype=float,
        ) * scale
        tree = cKDTree(child_xyz)

        for parent in cur.groupby("track_id").tail(1).itertuples(index=False):
            pxyz = np.array([parent.z, parent.y, parent.x], dtype=float) * scale
            candidate_indices = tree.query_ball_point(pxyz, division_radius_um)
            candidates = []
            for index in candidate_indices:
                child = child_records[index]
                if int(child.track_id) == int(parent.track_id):
                    continue
                cxyz = child_xyz[index]
                dist = float(np.linalg.norm(pxyz - cxyz))
                candidates.append((dist, int(child.node_id)))

            if len(candidates) < 2:
                continue

            for dist, child_node in sorted(candidates, key=lambda item: (item[0], item[1]))[:2]:
                events.append(
                    (
                        int(parent.node_id),
                        child_node,
                        dist,
                        "division_parent",
                    )
                )

    result = pd.DataFrame(
        events,
        columns=["source_id", "target_id", "distance_um", "edge_type"],
    )
    if result.empty:
        result = result.astype(
            {
                "source_id": "int64",
                "target_id": "int64",
                "distance_um": "float64",
                "edge_type": "object",
            }
        )
    return result
