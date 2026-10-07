from __future__ import annotations

from pathlib import Path
import zipfile
from urllib.request import urlretrieve

import numpy as np
import pandas as pd
import tifffile

from ai4s_core import validate_edges, validate_lineage_graph, validate_nodes

CTC_DIC_C2DH_HELA_URL = "https://data.celltrackingchallenge.net/training-datasets/DIC-C2DH-HeLa.zip"
DIC_C2DH_HELA_VOXEL_SIZE_UM = (1.0, 0.19, 0.19)


def ensure_ctc_dataset(cache_root: str | Path) -> Path:
    """Download and unpack DIC-C2DH-HeLa into a reusable local cache."""
    cache = Path(cache_root)
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / "DIC-C2DH-HeLa.zip"
    dataset_root = cache / "dataset" / "DIC-C2DH-HeLa"

    if not archive.exists():
        print(f"Downloading {CTC_DIC_C2DH_HELA_URL}", flush=True)
        urlretrieve(CTC_DIC_C2DH_HELA_URL, archive)

    if not dataset_root.exists():
        dataset_root.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dataset_root.parent)

    return dataset_root


def _marker_centroids(mask: np.ndarray) -> list[tuple[int, float, float, float]]:
    arr = np.asarray(mask)
    if arr.ndim == 2:
        labels = np.unique(arr)
        out = []
        for label in labels:
            if label <= 0:
                continue
            yy, xx = np.nonzero(arr == label)
            out.append((int(label), 0.0, float(yy.mean()), float(xx.mean())))
        return out

    if arr.ndim == 3:
        out = []
        for label in np.unique(arr):
            if label <= 0:
                continue
            zz, yy, xx = np.nonzero(arr == label)
            out.append((int(label), float(zz.mean()), float(yy.mean()), float(xx.mean())))
        return out

    raise ValueError("CTC marker image must be 2-D or 3-D")


def load_ctc_tracking(sequence_dir: str | Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load Cell Tracking Challenge marker annotations.

    Returns detection nodes, temporal/lineage edges, and track metadata.
    """
    root = Path(sequence_dir)
    marker_files = sorted(root.glob("man_track*.tif"))
    if not marker_files:
        raise FileNotFoundError(f"no man_track*.tif files found in {root}")

    rows = []
    for path in marker_files:
        digits = "".join(ch for ch in path.stem if ch.isdigit())
        if not digits:
            continue
        t = int(digits)
        image = tifffile.imread(path)
        for label, z, y, x in _marker_centroids(image):
            rows.append((len(rows), label, t, z, y, x))

    nodes = pd.DataFrame(
        rows,
        columns=["node_id", "track_id", "t", "z", "y", "x"],
    ).sort_values(["t", "track_id"]).reset_index(drop=True)

    by_key = {
        (int(row.track_id), int(row.t)): int(row.node_id)
        for row in nodes.itertuples(index=False)
    }

    edges = []
    for track_id in nodes["track_id"].unique():
        frames = sorted(nodes.loc[nodes["track_id"] == track_id, "t"].astype(int))
        for a, b in zip(frames, frames[1:]):
            if b == a + 1:
                edges.append((by_key[(int(track_id), a)], by_key[(int(track_id), b)], "link"))

    metadata_path = root / "man_track.txt"
    metadata_rows = []
    if metadata_path.exists():
        for line in metadata_path.read_text().splitlines():
            fields = line.split()
            if len(fields) < 4:
                continue
            track_id, start, end, parent = map(int, fields[:4])
            metadata_rows.append((track_id, start, end, parent))

            if parent > 0:
                parent_nodes = nodes[nodes["track_id"] == parent]
                child_nodes = nodes[nodes["track_id"] == track_id]
                if not parent_nodes.empty and not child_nodes.empty:
                    parent_node = int(parent_nodes.loc[parent_nodes["t"].idxmax(), "node_id"])
                    child_node = int(child_nodes.loc[child_nodes["t"].idxmin(), "node_id"])
                    edges.append((parent_node, child_node, "division_parent"))

    edge_df = pd.DataFrame(edges, columns=["source_id", "target_id", "edge_type"])
    if edge_df.empty:
        edge_df = pd.DataFrame(columns=["source_id", "target_id", "edge_type"])

    metadata = pd.DataFrame(
        metadata_rows,
        columns=["track_id", "start_frame", "end_frame", "parent_id"],
    )

    known_tracks = set(nodes["track_id"].astype(int))
    for row in metadata.itertuples(index=False):
        track_id = int(row.track_id)
        if track_id not in known_tracks:
            raise ValueError(f"metadata references unknown track_id {track_id}")
        observed = nodes[nodes["track_id"].eq(track_id)]
        observed_start = int(observed["t"].min())
        observed_end = int(observed["t"].max())
        if observed_start != int(row.start_frame) or observed_end != int(row.end_frame):
            raise ValueError(
                f"metadata frame range mismatch for track_id {track_id}: "
                f"metadata=({row.start_frame},{row.end_frame}) "
                f"observed=({observed_start},{observed_end})"
            )
        parent_id = int(row.parent_id)
        if parent_id > 0 and parent_id not in known_tracks:
            raise ValueError(f"metadata references unknown parent_id {parent_id}")
    validate_nodes(nodes)
    validate_edges(edge_df, nodes, require_forward_time=True)
    division_edges = edge_df[edge_df["edge_type"].eq("division_parent")][["source_id", "target_id"]]
    if not division_edges.empty:
        validate_lineage_graph(nodes, division_edges)
    return nodes, edge_df, metadata
