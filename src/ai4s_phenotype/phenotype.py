from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable

import numpy as np
import pandas as pd


NODE_COLUMNS = ["node_id", "t", "z", "y", "x"]
EDGE_COLUMNS = ["source_id", "target_id"]


def _validate(nodes: pd.DataFrame, edges: pd.DataFrame) -> None:
    missing_nodes = [c for c in NODE_COLUMNS if c not in nodes.columns]
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

    Nodes require: node_id, t, z, y, x.
    Edges require: source_id, target_id.

    One row is returned per node with trajectory, lineage and event features.
    """
    _validate(nodes, edges)

    n = nodes.copy()
    n["node_id"] = n["node_id"].astype(int)
    n["t"] = n["t"].astype(int)
    n = n.sort_values(["node_id", "t"]).reset_index(drop=True)

    children: dict[int, list[int]] = defaultdict(list)
    parents: dict[int, list[int]] = defaultdict(list)
    for row in edges[["source_id", "target_id"]].itertuples(index=False):
        s, d = int(row.source_id), int(row.target_id)
        children[s].append(d)
        parents[d].append(s)

    out = []
    for node_id, g in n.groupby("node_id", sort=False):
        g = g.sort_values("t")
        xyz = g[["z", "y", "x"]].to_numpy(float)
        dt = np.diff(g["t"].to_numpy(float))
        step = np.linalg.norm(np.diff(xyz, axis=0), axis=1) if len(g) > 1 else np.array([])
        valid_dt = dt > 0
        speed = float(np.mean(step[valid_dt] / dt[valid_dt])) if valid_dt.any() else 0.0
        displacement = float(np.linalg.norm(xyz[-1] - xyz[0])) if len(g) > 1 else 0.0
        path = float(step.sum())

        if len(xyz) > 2 and path > 0:
            directional_persistence = displacement / path
        else:
            directional_persistence = 1.0 if len(xyz) > 1 else 0.0

        child_ids = children.get(int(node_id), [])
        division_event = len(child_ids) >= 2
        descendants = _descendants(int(node_id), children)

        out.append(
            {
                "node_id": int(node_id),
                "t_start": int(g["t"].min()),
                "t_end": int(g["t"].max()),
                "duration": int(g["t"].max() - g["t"].min()),
                "observations": int(len(g)),
                "displacement": displacement,
                "path_length": path,
                "mean_speed": speed,
                "directional_persistence": float(directional_persistence),
                "parent_count": int(len(parents.get(int(node_id), []))),
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
