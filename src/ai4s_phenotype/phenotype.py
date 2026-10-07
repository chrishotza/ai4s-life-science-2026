from __future__ import annotations

from collections import defaultdict, deque

import numpy as np
import pandas as pd

from ai4s_core import validate_edges, validate_nodes


DETECTION_COLUMNS = ["node_id", "track_id", "t", "z", "y", "x"]
EDGE_COLUMNS = ["source_id", "target_id"]


def _validate(nodes: pd.DataFrame, edges: pd.DataFrame) -> None:
    missing_nodes = [c for c in DETECTION_COLUMNS if c not in nodes.columns]
    missing_edges = [c for c in EDGE_COLUMNS if c not in edges.columns]
    if missing_nodes:
        raise ValueError(f"nodes missing columns: {missing_nodes}")
    if missing_edges:
        raise ValueError(f"edges missing columns: {missing_edges}")


def _descendants(root: int, children: dict[int, list[int]]) -> set[int]:
    seen: set[int] = set()
    queue = deque(children.get(root, []))
    while queue:
        node = queue.popleft()
        if node in seen:
            continue
        seen.add(node)
        queue.extend(children.get(node, []))
    return seen


def analyze(nodes: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    """Extract interpretable temporal phenotypes from tracked cells.

    One row is returned per track_id. Detection-level edges are converted to
    track-level lineage edges before lineage/event features are calculated.
    """
    _validate(nodes, edges)
    validate_nodes(nodes)
    validate_edges(edges, nodes, require_forward_time=True)

    n = nodes.copy()
    n["node_id"] = n["node_id"].astype(int)
    n["track_id"] = n["track_id"].astype(int)
    n["t"] = n["t"].astype(int)
    n = n.sort_values(["track_id", "t", "node_id"]).reset_index(drop=True)

    node_to_track = dict(zip(n["node_id"], n["track_id"]))
    children: dict[int, list[int]] = defaultdict(list)
    parents: dict[int, list[int]] = defaultdict(list)

    for row in edges[["source_id", "target_id"]].itertuples(index=False):
        s = int(row.source_id)
        d = int(row.target_id)
        if s not in node_to_track or d not in node_to_track:
            continue
        parent_track = int(node_to_track[s])
        child_track = int(node_to_track[d])
        if parent_track == child_track:
            continue
        if child_track not in children[parent_track]:
            children[parent_track].append(child_track)
        if parent_track not in parents[child_track]:
            parents[child_track].append(parent_track)

    out = []
    for track_id, g in n.groupby("track_id", sort=False):
        g = g.sort_values("t")
        xyz = g[["z", "y", "x"]].to_numpy(float)
        dt = np.diff(g["t"].to_numpy(float))
        step = np.linalg.norm(np.diff(xyz, axis=0), axis=1) if len(g) > 1 else np.array([])
        valid_dt = dt > 0
        speed = float(np.mean(step[valid_dt] / dt[valid_dt])) if valid_dt.any() else 0.0
        displacement = float(np.linalg.norm(xyz[-1] - xyz[0])) if len(g) > 1 else 0.0
        path = float(step.sum())
        directional_persistence = (
            displacement / path if len(xyz) > 2 and path > 0
            else (1.0 if len(xyz) > 1 else 0.0)
        )

        child_ids = children.get(int(track_id), [])
        division_event = len(child_ids) >= 2
        descendants = _descendants(int(track_id), children)

        out.append(
            {
                "track_id": int(track_id),
                "t_start": int(g["t"].min()),
                "t_end": int(g["t"].max()),
                "duration": int(g["t"].max() - g["t"].min()),
                "observations": int(len(g)),
                "displacement": displacement,
                "path_length": path,
                "mean_speed": speed,
                "directional_persistence": float(directional_persistence),
                "parent_count": int(len(parents.get(int(track_id), []))),
                "child_count": int(len(child_ids)),
                "division_event": bool(division_event),
                "descendant_count": int(len(descendants)),
            }
        )

    result = pd.DataFrame(out)
    if result.empty:
        return result

    result["phenotype_flag"] = np.select(
        [
            result["division_event"],
            result["directional_persistence"] < 0.35,
            result["mean_speed"] > result["mean_speed"].median(),
        ],
        ["division", "highly_non_directional", "high_mobility"],
        default="stable_or_unclassified",
    )
    return result
