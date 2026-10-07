from __future__ import annotations

import numpy as np
import pandas as pd


def infer_divisions(
    nodes: pd.DataFrame,
    links: pd.DataFrame,
    division_radius_um: float = 5.0,
) -> pd.DataFrame:
    """Infer candidate parent-to-daughter events from track starts."""
    required_nodes = {"node_id", "track_id", "t", "z", "y", "x"}
    required_links = {"source_id", "target_id"}
    if not required_nodes.issubset(nodes.columns):
        raise ValueError("nodes missing lineage columns")
    if not required_links.issubset(links.columns):
        raise ValueError("links missing lineage columns")

    n = nodes.copy()
    incoming = set(links["target_id"].astype(int))
    events = []

    for t in sorted(n["t"].unique())[:-1]:
        cur = n[n["t"] == t]
        nxt = n[n["t"] == t + 1]
        new_tracks = nxt[~nxt["node_id"].astype(int).isin(incoming)]

        for parent in cur.groupby("track_id").tail(1).itertuples(index=False):
            candidates = []
            pxyz = np.array([parent.z, parent.y, parent.x], dtype=float)
            for child in new_tracks.itertuples(index=False):
                if int(child.track_id) == int(parent.track_id):
                    continue
                cxyz = np.array([child.z, child.y, child.x], dtype=float)
                dist = float(np.linalg.norm(pxyz - cxyz))
                if dist <= division_radius_um:
                    candidates.append((dist, int(child.node_id)))

            if len(candidates) < 2:
                continue

            for dist, child_node in sorted(candidates)[:2]:
                events.append(
                    (
                        int(parent.node_id),
                        child_node,
                        dist,
                        "division_parent",
                    )
                )

    return pd.DataFrame(
        events,
        columns=["source_id", "target_id", "distance_um", "edge_type"],
    )
