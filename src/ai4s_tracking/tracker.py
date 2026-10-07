from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class TrackingConfig:
    max_distance_um: float = 8.0
    mutual: bool = True

def _distance(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    d = a[:, None, :] - b[None, :, :]
    return np.sqrt((d * d).sum(axis=2))

def _mutual_pairs(a: np.ndarray, b: np.ndarray, max_distance: float):
    if len(a) == 0 or len(b) == 0: return []
    d = _distance(a, b)
    f, r = d.argmin(axis=1), d.argmin(axis=0)
    return [(i, int(j), float(d[i, j])) for i, j in enumerate(f) if r[j] == i and d[i, j] <= max_distance]

def track_detections(detections: pd.DataFrame, config: TrackingConfig = TrackingConfig()):
    required = {"t", "z", "y", "x"}
    missing = required - set(detections.columns)
    if missing: raise ValueError(f"missing columns: {sorted(missing)}")
    df = detections.copy().sort_values(["t","z","y","x"]).reset_index(drop=True)
    df["node_id"] = np.arange(len(df), dtype=int)
    df["track_id"] = -1
    edges = []
    next_track = 0
    active = {}
    for t in sorted(df.t.unique()):
        cur_idx = df.index[df.t.eq(t)].to_numpy()
        cur_xyz = df.loc[cur_idx, ["z","y","x"]].to_numpy(float)
        if not active:
            for i in cur_idx:
                df.loc[i,"track_id"] = next_track; active[next_track] = int(i); next_track += 1
            continue
        prev_tracks = sorted(active)
        prev_idx = np.array([active[k] for k in prev_tracks], dtype=int)
        pairs = _mutual_pairs(df.loc[prev_idx, ["z","y","x"]].to_numpy(float), cur_xyz, config.max_distance_um) if config.mutual else []
        used, new_active = set(), {}
        for pi, ci, dist in pairs:
            tr, src, dst = prev_tracks[pi], int(prev_idx[pi]), int(cur_idx[ci])
            df.loc[dst,"track_id"] = tr; used.add(ci); new_active[tr] = dst
            edges.append((src,dst,dist,"link"))
        for ci, dst in enumerate(cur_idx):
            if ci not in used:
                df.loc[dst,"track_id"] = next_track; new_active[next_track] = int(dst); next_track += 1
        active = new_active
    edge_df = pd.DataFrame(edges, columns=["source_id","target_id","distance_um","edge_type"])
    if edge_df.empty: edge_df = pd.DataFrame(columns=["source_id","target_id","distance_um","edge_type"])
    return df, edge_df
