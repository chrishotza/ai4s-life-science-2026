from __future__ import annotations

import pandas as pd

from .contracts import validate_edges, validate_nodes


def validate_lineage_graph(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    *,
    max_parents_per_node: int = 1,
) -> None:
    """Validate a parent/child lineage graph against tracked nodes."""
    if max_parents_per_node < 1:
        raise ValueError("max_parents_per_node must be at least 1")

    validate_nodes(nodes)
    validate_edges(edges, nodes, require_forward_time=True)

    if edges.empty:
        return

    indexed = nodes.set_index("node_id")
    child_parent_counts = edges.groupby("target_id")["source_id"].nunique()
    if (child_parent_counts > max_parents_per_node).any():
        raise ValueError("lineage graph contains a node with too many parents")

    source_tracks = indexed.loc[edges["source_id"].astype(int), "track_id"].to_numpy()
    target_tracks = indexed.loc[edges["target_id"].astype(int), "track_id"].to_numpy()
    if (source_tracks == target_tracks).any():
        raise ValueError("lineage graph contains an intra-track lineage edge")

    if "edge_type" in edges.columns:
        unknown = set(edges["edge_type"].dropna().astype(str)) - {"link", "division_parent"}
        if unknown:
            raise ValueError(f"unknown lineage edge types: {sorted(unknown)}")
