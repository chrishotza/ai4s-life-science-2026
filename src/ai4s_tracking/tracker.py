from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree

from ai4s_core import validate_nodes


@dataclass(frozen=True)
class TrackingConfig:
    max_distance_um: float = 8.0
    method: str = "mutual_nn"
    voxel_size_um: tuple[float, float, float] = (1.0, 1.0, 1.0)

    def __post_init__(self) -> None:
        if self.max_distance_um <= 0:
            raise ValueError("max_distance_um must be positive")
        if self.method not in {"mutual_nn", "mutual_nn_tree", "mutual_rescue", "hungarian", "velocity_hungarian"}:
            raise ValueError("unknown tracking method")
        if len(self.voxel_size_um) != 3 or any(value <= 0 for value in self.voxel_size_um):
            raise ValueError("voxel_size_um must contain three positive values")


def _distance(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    d = a[:, None, :] - b[None, :, :]
    return np.sqrt((d * d).sum(axis=2))


def _mutual_pairs(a: np.ndarray, b: np.ndarray, max_distance: float):
    if len(a) == 0 or len(b) == 0:
        return []
    d = _distance(a, b)
    forward = d.argmin(axis=1)
    reverse = d.argmin(axis=0)
    return [
        (i, int(j), float(d[i, j]))
        for i, j in enumerate(forward)
        if reverse[j] == i and d[i, j] <= max_distance
    ]


def _mutual_tree_pairs(
    a: np.ndarray,
    b: np.ndarray,
    max_distance: float,
) -> list[tuple[int, int, float]]:
    if len(a) == 0 or len(b) == 0:
        return []

    forward_dist, forward = cKDTree(b).query(a, k=1)
    reverse_dist, reverse = cKDTree(a).query(b, k=1)
    pairs = []
    for i, (distance, j) in enumerate(zip(forward_dist, forward)):
        j = int(j)
        if reverse[j] == i and float(distance) <= max_distance:
            pairs.append((i, j, float(distance)))
    return pairs


def _mutual_rescue_pairs(
    a: np.ndarray,
    b: np.ndarray,
    max_distance: float,
) -> list[tuple[int, int, float]]:
    if len(a) == 0 or len(b) == 0:
        return []

    protected = _mutual_pairs(a, b, max_distance)
    used_a = {i for i, _, _ in protected}
    used_b = {j for _, j, _ in protected}
    remaining_a = [i for i in range(len(a)) if i not in used_a]
    remaining_b = [j for j in range(len(b)) if j not in used_b]

    if not remaining_a or not remaining_b:
        return protected

    d = _distance(a[remaining_a], b[remaining_b])
    rows, cols = linear_sum_assignment(d)
    rescued = list(protected)
    for ri, ci in zip(rows, cols):
        distance = float(d[ri, ci])
        if distance <= max_distance:
            rescued.append((int(remaining_a[ri]), int(remaining_b[ci]), distance))

    rescued.sort(key=lambda item: (item[0], item[1]))
    return rescued


def _hungarian_pairs(
    a: np.ndarray,
    b: np.ndarray,
    max_distance: float,
) -> list[tuple[int, int, float]]:
    if len(a) == 0 or len(b) == 0:
        return []
    d = _distance(a, b)
    rows, cols = linear_sum_assignment(d)
    return [
        (int(i), int(j), float(d[i, j]))
        for i, j in zip(rows, cols)
        if d[i, j] <= max_distance
    ]


def _assign_pairs(
    previous: np.ndarray,
    current: np.ndarray,
    max_distance: float,
    method: str,
) -> list[tuple[int, int, float]]:
    if method == "mutual_nn":
        return _mutual_pairs(previous, current, max_distance)
    if method == "mutual_nn_tree":
        return _mutual_tree_pairs(previous, current, max_distance)
    if method == "mutual_rescue":
        return _mutual_rescue_pairs(previous, current, max_distance)
    return _hungarian_pairs(previous, current, max_distance)


def track_detections(
    detections: pd.DataFrame,
    config: TrackingConfig = TrackingConfig(),
):
    """Track frame-wise 3-D detections with deterministic association.

    Distances are computed in physical units using voxel_size_um=(z,y,x).

    Methods:
    - mutual_nn: mutually nearest detections using an exact distance matrix.
    - mutual_nn_tree: mutually nearest detections using KD-tree nearest-neighbor queries.
    - mutual_rescue: protect mutual matches, then solve remaining ambiguity globally.
    - hungarian: globally optimal one-to-one distance assignment.
    - velocity_hungarian: Hungarian assignment to constant-velocity predictions.
    """
    required = {"t", "z", "y", "x"}
    missing = required - set(detections.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")

    if set(detections.columns) < required:
        raise ValueError(f"missing columns: {sorted(required - set(detections.columns))}")

    df = (
        detections.copy()
        .sort_values(["t", "z", "y", "x"])
        .reset_index(drop=True)
    )
    df["node_id"] = np.arange(len(df), dtype=int)
    df["track_id"] = -1

    scale = np.asarray(config.voxel_size_um, dtype=float)
    edges = []
    next_track = 0
    active: dict[int, int] = {}
    history: dict[int, list[tuple[int, np.ndarray]]] = {}

    for t in sorted(df.t.unique()):
        cur_idx = df.index[df.t.eq(t)].to_numpy()
        cur_xyz = df.loc[cur_idx, ["z", "y", "x"]].to_numpy(float) * scale

        if not active:
            for i in cur_idx:
                tr = next_track
                next_track += 1
                df.loc[i, "track_id"] = tr
                active[tr] = int(i)
                position = df.loc[i, ["z", "y", "x"]].to_numpy(float) * scale
                history[tr] = [(int(t), position)]
            continue

        prev_tracks = sorted(active)
        prev_idx = np.array([active[k] for k in prev_tracks], dtype=int)
        prev_xyz = df.loc[prev_idx, ["z", "y", "x"]].to_numpy(float) * scale

        if config.method == "velocity_hungarian":
            predicted = []
            for tr in prev_tracks:
                hist = history.get(tr, [])
                if len(hist) >= 2:
                    t0, p0 = hist[-2]
                    t1, p1 = hist[-1]
                    dt = max(1, t1 - t0)
                    predicted.append(p1 + (p1 - p0) / dt * (t - t1))
                else:
                    predicted.append(hist[-1][1])
            predicted_xyz = np.asarray(predicted, dtype=float)
            pairs = _hungarian_pairs(predicted_xyz, cur_xyz, config.max_distance_um)
        else:
            pairs = _assign_pairs(
                prev_xyz,
                cur_xyz,
                config.max_distance_um,
                config.method,
            )

        used = set()
        new_active: dict[int, int] = {}
        for pi, ci, dist in pairs:
            tr = prev_tracks[pi]
            src = int(prev_idx[pi])
            dst = int(cur_idx[ci])
            df.loc[dst, "track_id"] = tr
            used.add(ci)
            new_active[tr] = dst
            position = df.loc[dst, ["z", "y", "x"]].to_numpy(float) * scale
            history.setdefault(tr, []).append((int(t), position))
            history[tr] = history[tr][-3:]
            edges.append((src, dst, dist, "link"))

        for ci, dst in enumerate(cur_idx):
            if ci not in used:
                tr = next_track
                next_track += 1
                df.loc[dst, "track_id"] = tr
                new_active[tr] = int(dst)
                position = df.loc[dst, ["z", "y", "x"]].to_numpy(float) * scale
                history[tr] = [(int(t), position)]

        active = new_active

    validate_nodes(df)

    edge_df = pd.DataFrame(
        edges,
        columns=["source_id", "target_id", "distance_um", "edge_type"],
    )
    if edge_df.empty:
        edge_df = pd.DataFrame(
            columns=["source_id", "target_id", "distance_um", "edge_type"]
        )
    return df, edge_df
