from __future__ import annotations

import numpy as np
import pandas as pd

NODE_COLUMNS = ("node_id", "track_id", "t", "z", "y", "x")
EDGE_COLUMNS = ("source_id", "target_id")


def validate_nodes(
    nodes: pd.DataFrame,
    *,
    require_track_ids: bool = True,
    require_unique_track_time: bool = True,
) -> None:
    missing = [column for column in NODE_COLUMNS if column not in nodes.columns]
    if missing:
        raise ValueError(f"nodes missing columns: {missing}")

    if nodes.empty:
        return

    if nodes["node_id"].duplicated().any():
        raise ValueError("node_id values must be unique")

    if require_track_ids and nodes["track_id"].isna().any():
        raise ValueError("track_id values must not be missing")

    if not pd.api.types.is_numeric_dtype(nodes["t"]):
        raise ValueError("t values must be numeric")
    t_values = nodes["t"].to_numpy(float)
    if not np.isfinite(t_values).all() or not np.all(t_values == np.floor(t_values)):
        raise ValueError("t values must be finite frame indices")

    if require_unique_track_time and nodes.duplicated(["track_id", "t"]).any():
        raise ValueError("a track cannot contain multiple observations at the same frame")

    xyz = nodes[["z", "y", "x"]].to_numpy(float)
    if not np.isfinite(xyz).all():
        raise ValueError("node coordinates must be finite")


def validate_edges(
    edges: pd.DataFrame,
    nodes: pd.DataFrame | None = None,
    *,
    require_unique: bool = True,
    require_consecutive: bool = False,
    require_forward_time: bool = False,
) -> None:
    missing = [column for column in EDGE_COLUMNS if column not in edges.columns]
    if missing:
        raise ValueError(f"edges missing columns: {missing}")

    if edges.empty:
        return

    pairs = edges[["source_id", "target_id"]].astype(int)
    if require_unique and pairs.duplicated().any():
        raise ValueError("duplicate source-target edges are not allowed")
    if (pairs["source_id"] == pairs["target_id"]).any():
        raise ValueError("self-edges are not allowed")

    if nodes is None:
        return

    node_ids = set(nodes["node_id"].astype(int))
    if not set(pairs["source_id"]).issubset(node_ids):
        raise ValueError("edge source_id references an unknown node")
    if not set(pairs["target_id"]).issubset(node_ids):
        raise ValueError("edge target_id references an unknown node")

    indexed = nodes.set_index("node_id")
    dt = indexed.loc[pairs["target_id"].to_numpy(), "t"].to_numpy() - indexed.loc[
        pairs["source_id"].to_numpy(), "t"
    ].to_numpy()
    if require_forward_time and not np.all(dt > 0):
        raise ValueError("edges must point forward in time")
    if require_consecutive and not np.all(dt == 1):
        raise ValueError("temporal edges must connect consecutive frames")


def scale_coordinates(
    nodes: pd.DataFrame,
    voxel_size_um: tuple[float, float, float],
) -> pd.DataFrame:
    if len(voxel_size_um) != 3 or any(value <= 0 for value in voxel_size_um):
        raise ValueError("voxel_size_um must contain three positive values")
    out = nodes.copy()
    out[["z", "y", "x"]] = out[["z", "y", "x"]].to_numpy(float) * np.asarray(
        voxel_size_um,
        dtype=float,
    )
    return out
