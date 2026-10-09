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
    max_frame_gap: int = 1

    def __post_init__(self) -> None:
        if not np.isfinite(self.max_distance_um) or self.max_distance_um <= 0:
            raise ValueError("max_distance_um must be finite and positive")
        if self.method not in {
            "mutual_nn",
            "mutual_nn_tree",
            "mutual_rescue",
            "hungarian",
            "velocity_hungarian",
            "gap_hungarian",
        }:
            raise ValueError("unknown tracking method")
        scale = np.asarray(self.voxel_size_um, dtype=float)
        if scale.shape != (3,) or not np.isfinite(scale).all() or np.any(scale <= 0):
            raise ValueError("voxel_size_um must contain three finite positive values")
        if (
            isinstance(self.max_frame_gap, (bool, np.bool_))
            or not isinstance(self.max_frame_gap, (int, np.integer))
            or self.max_frame_gap < 1
        ):
            raise ValueError("max_frame_gap must be a positive integer")
        if self.method != "gap_hungarian" and self.max_frame_gap != 1:
            raise ValueError("max_frame_gap > 1 requires gap_hungarian")


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
    _, reverse = cKDTree(a).query(b, k=1)
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

    rescued = list(protected)
    for ri, ci, distance in _hungarian_pairs(
        a[remaining_a],
        b[remaining_b],
        max_distance,
    ):
        rescued.append((int(remaining_a[ri]), int(remaining_b[ci]), distance))

    rescued.sort(key=lambda item: (item[0], item[1]))
    return rescued


def _gated_assignment_indices(
    normalized_cost: np.ndarray,
    valid: np.ndarray,
) -> list[tuple[int, int]]:
    """Maximize valid assignment cardinality, then minimize normalized cost.

    Valid costs must be normalized to [0, 1]. Assigning any invalid edge costs
    more than the maximum possible sum of all valid edges, so one additional
    valid match always takes precedence over a lower-cost partial matching.
    """
    if normalized_cost.ndim != 2 or valid.shape != normalized_cost.shape:
        raise ValueError("cost and validity matrices must have the same 2-D shape")
    if normalized_cost.size == 0:
        return []
    if not np.isfinite(normalized_cost[valid]).all():
        raise ValueError("valid assignment costs must be finite")
    if ((normalized_cost[valid] < 0.0) | (normalized_cost[valid] > 1.0)).any():
        raise ValueError("valid assignment costs must be normalized to [0, 1]")

    max_pairs = min(normalized_cost.shape)
    cost = np.full(normalized_cost.shape, float(max_pairs + 1), dtype=float)
    cost[valid] = normalized_cost[valid]
    rows, cols = linear_sum_assignment(cost)
    return [(int(i), int(j)) for i, j in zip(rows, cols) if valid[i, j]]


def _hungarian_pairs(
    a: np.ndarray,
    b: np.ndarray,
    max_distance: float,
) -> list[tuple[int, int, float]]:
    if len(a) == 0 or len(b) == 0:
        return []
    d = _distance(a, b)
    valid = d <= max_distance
    pairs = _gated_assignment_indices(d / max_distance, valid)
    return [(i, j, float(d[i, j])) for i, j in pairs]


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


def _track_gap_hungarian(
    df: pd.DataFrame,
    config: TrackingConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Track while retaining unmatched tracks for a bounded temporal gap."""
    scale = np.asarray(config.voxel_size_um, dtype=float)
    edges = []
    next_track = 0
    active: dict[int, tuple[int, int]] = {}
    last_position: dict[int, np.ndarray] = {}

    for t in sorted(df["t"].unique()):
        cur_idx = df.index[df["t"].eq(t)].to_numpy()
        cur_xyz = df.loc[cur_idx, ["z", "y", "x"]].to_numpy(float) * scale

        eligible = [
            tr
            for tr, (_, last_t) in active.items()
            if 0 < int(t) - last_t <= config.max_frame_gap
        ]

        assigned_current: set[int] = set()
        next_active: dict[int, tuple[int, int]] = {}

        if eligible and len(cur_idx):
            track_positions = np.asarray([last_position[tr] for tr in eligible], dtype=float)
            last_times = np.asarray([active[tr][1] for tr in eligible], dtype=int)
            frame_gaps = int(t) - last_times
            distances = _distance(track_positions, cur_xyz)
            allowed = config.max_distance_um * frame_gaps[:, None]
            valid = distances <= allowed
            normalized_cost = distances / allowed
            pairs = _gated_assignment_indices(normalized_cost, valid)

            for row_idx, col_idx in pairs:
                frame_gap = int(frame_gaps[row_idx])
                distance = float(distances[row_idx, col_idx])
                tr = eligible[row_idx]
                src = int(active[tr][0])
                dst = int(cur_idx[col_idx])
                confidence = max(0.0, 1.0 - distance / float(allowed[row_idx, col_idx]))
                df.loc[dst, "track_id"] = tr
                assigned_current.add(int(col_idx))
                next_active[tr] = (dst, int(t))
                last_position[tr] = cur_xyz[col_idx]
                edges.append((src, dst, distance, confidence, frame_gap, "link"))

        for col_idx, dst in enumerate(cur_idx):
            if col_idx in assigned_current:
                continue
            tr = next_track
            next_track += 1
            df.loc[dst, "track_id"] = tr
            next_active[tr] = (int(dst), int(t))
            last_position[tr] = cur_xyz[col_idx]

        for tr, (last_idx, last_t) in active.items():
            if tr not in next_active and int(t) - last_t < config.max_frame_gap:
                next_active[tr] = (last_idx, last_t)

        active = next_active

    validate_nodes(df)
    edge_df = pd.DataFrame(
        edges,
        columns=[
            "source_id",
            "target_id",
            "distance_um",
            "link_confidence",
            "frame_gap",
            "edge_type",
        ],
    )
    if edge_df.empty:
        edge_df = pd.DataFrame(
            columns=[
                "source_id",
                "target_id",
                "distance_um",
                "link_confidence",
                "frame_gap",
                "edge_type",
            ]
        )
    return df, edge_df


def _validate_detection_inputs(detections: pd.DataFrame) -> None:
    """Validate frame indices and coordinates before distance computations."""
    required = {"t", "z", "y", "x"}
    missing = required - set(detections.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    if detections.empty:
        return

    for column in ("t", "z", "y", "x"):
        if not pd.api.types.is_numeric_dtype(detections[column]):
            raise ValueError(f"{column} values must be numeric")
        values = detections[column].to_numpy(dtype=float, na_value=np.nan)
        if not np.isfinite(values).all():
            raise ValueError(f"{column} values must be finite")
        if column == "t" and not np.all(values == np.floor(values)):
            raise ValueError("t values must be finite frame indices")


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
    - gap_hungarian: retain tracks for a bounded number of missing frames.
    """
    _validate_detection_inputs(detections)

    df = (
        detections.copy()
        .sort_values(["t", "z", "y", "x"])
        .reset_index(drop=True)
    )
    df["node_id"] = np.arange(len(df), dtype=int)
    df["track_id"] = -1

    if config.method == "gap_hungarian":
        return _track_gap_hungarian(df, config)

    scale = np.asarray(config.voxel_size_um, dtype=float)
    edges = []
    next_track = 0
    active: dict[int, int] = {}
    history: dict[int, list[tuple[int, np.ndarray]]] = {}
    last_processed_time: float | None = None

    for t in sorted(df.t.unique()):
        cur_idx = df.index[df.t.eq(t)].to_numpy()
        cur_xyz = df.loc[cur_idx, ["z", "y", "x"]].to_numpy(float) * scale

        # Only gap_hungarian may connect across missing frames.
        current_time = float(t)
        if last_processed_time is not None and current_time - last_processed_time != 1.0:
            active = {}
        last_processed_time = current_time

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
            link_confidence = max(0.0, 1.0 - dist / config.max_distance_um)
            edges.append((src, dst, dist, link_confidence, "link"))

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
        columns=[
            "source_id",
            "target_id",
            "distance_um",
            "link_confidence",
            "edge_type",
        ],
    )
    if edge_df.empty:
        edge_df = pd.DataFrame(
            columns=[
                "source_id",
                "target_id",
                "distance_um",
                "link_confidence",
                "edge_type",
            ]
        )
    return df, edge_df
