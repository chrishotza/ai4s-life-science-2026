from __future__ import annotations

from collections import defaultdict, deque

import numpy as np
import pandas as pd

from ai4s_core import validate_edges, validate_lineage_graph, validate_nodes


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


def _attribute_features(group: pd.DataFrame) -> dict[str, float]:
    excluded = {
        "node_id",
        "track_id",
        "t",
        "z",
        "y",
        "x",
    }
    out: dict[str, float] = {}
    for column in group.columns:
        lowered = column.lower()
        if column in excluded or lowered.startswith("truth_") or lowered.startswith("label_"):
            continue
        if lowered.endswith("_id") or lowered in {"source", "target"}:
            continue
        if not pd.api.types.is_numeric_dtype(group[column]):
            continue
        values = group[column].to_numpy(float)
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            continue
        out[f"mean_{column}"] = float(np.mean(finite))
        out[f"std_{column}"] = float(np.std(finite))
        out[f"min_{column}"] = float(np.min(finite))
        out[f"max_{column}"] = float(np.max(finite))
    return out


def analyze(nodes: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    """Extract interpretable temporal phenotypes from tracked cells.

    One row is returned per track_id. Detection-level edges are converted to
    track-level lineage edges before lineage/event features are calculated.
    """
    _validate(nodes, edges)
    validate_nodes(nodes)
    validate_edges(edges, nodes, require_forward_time=True)
    if "edge_type" in edges.columns:
        lineage_edges = edges[edges["edge_type"].eq("division_parent")][["source_id", "target_id"]]
        if not lineage_edges.empty:
            validate_lineage_graph(nodes, lineage_edges)

    n = nodes.copy()
    n["node_id"] = n["node_id"].astype(int)
    n["track_id"] = n["track_id"].astype(int)
    n["t"] = n["t"].astype(int)
    n = n.sort_values(["track_id", "t", "node_id"]).reset_index(drop=True)

    node_to_track = dict(zip(n["node_id"], n["track_id"]))
    children: dict[int, list[int]] = defaultdict(list)
    parents: dict[int, list[int]] = defaultdict(list)
    temporal_link_stats: dict[int, list[float]] = defaultdict(list)
    temporal_link_confidences: dict[int, list[float]] = defaultdict(list)

    temporal_edge_mask = (
        edges["edge_type"].eq("link")
        if "edge_type" in edges.columns
        else pd.Series(True, index=edges.index)
    )
    temporal_edges = edges.loc[temporal_edge_mask].copy()

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

    if not temporal_edges.empty:
        columns = ["source_id"]
        if "distance_um" in temporal_edges.columns:
            columns.append("distance_um")
        if "link_confidence" in temporal_edges.columns:
            columns.append("link_confidence")
        for row in temporal_edges[columns].itertuples(index=False):
            source_track = int(node_to_track[int(row.source_id)])
            if "distance_um" in columns:
                temporal_link_stats[source_track].append(float(row.distance_um))
            if "link_confidence" in columns:
                temporal_link_confidences[source_track].append(float(row.link_confidence))

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
        t_start = int(g["t"].min())
        t_end = int(g["t"].max())
        temporal_span = max(0, t_end - t_start)
        observation_fraction = len(g) / max(1, temporal_span + 1)
        positive_gaps = dt[valid_dt]
        gap_count = int((positive_gaps > 1).sum()) if len(positive_gaps) else 0
        max_gap = int(positive_gaps.max()) if len(positive_gaps) else 0
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
                "t_start": t_start,
                "t_end": t_end,
                "duration": temporal_span,
                "observations": int(len(g)),
                "observation_fraction": float(observation_fraction),
                "gap_count": gap_count,
                "max_gap": max_gap,
                "displacement": displacement,
                "path_length": path,
                "mean_speed": speed,
                "directional_persistence": float(directional_persistence),
                "parent_count": int(len(parents.get(int(track_id), []))),
                "child_count": int(len(child_ids)),
                "division_event": bool(division_event),
                "descendant_count": int(len(descendants)),
                "link_count": int(len(temporal_link_stats.get(int(track_id), []))),
                "mean_link_distance_um": (
                    float(np.mean(temporal_link_stats[int(track_id)]))
                    if temporal_link_stats.get(int(track_id))
                    else 0.0
                ),
                "max_link_distance_um": (
                    float(np.max(temporal_link_stats[int(track_id)]))
                    if temporal_link_stats.get(int(track_id))
                    else 0.0
                ),
                "mean_link_confidence": (
                    float(np.mean(temporal_link_confidences[int(track_id)]))
                    if temporal_link_confidences.get(int(track_id))
                    else 0.0
                ),
                "min_link_confidence": (
                    float(np.min(temporal_link_confidences[int(track_id)]))
                    if temporal_link_confidences.get(int(track_id))
                    else 0.0
                ),
                "low_confidence_link_fraction": (
                    float(
                        np.mean(
                            np.asarray(temporal_link_confidences[int(track_id)]) < 0.25
                        )
                    )
                    if temporal_link_confidences.get(int(track_id))
                    else 0.0
                ),
                **_attribute_features(g),
                "track_integrity_score": float(
                    np.clip(
                        (
                            observation_fraction
                            * (
                                float(np.mean(temporal_link_confidences[int(track_id)]))
                                if temporal_link_confidences.get(int(track_id))
                                else 0.0
                            )
                            * (
                                1.0
                                - float(
                                    np.mean(
                                        np.asarray(temporal_link_confidences[int(track_id)]) < 0.25
                                    )
                                )
                                if temporal_link_confidences.get(int(track_id))
                                else 0.0
                            )
                        )
                        ** (1.0 / 3.0),
                        0.0,
                        1.0,
                    )
                ),
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
