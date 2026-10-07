from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai4s_io import load_ctc_tracking
from ai4s_tracking import TrackingConfig, track_detections


DATA_URL = "https://data.celltrackingchallenge.net/training-datasets/DIC-C2DH-HeLa.zip"
VOXEL_SIZE_UM = (1.0, 0.19, 0.19)


def main() -> None:
    work = ROOT / ".benchmark_cache"
    work.mkdir(exist_ok=True)
    archive = work / "DIC-C2DH-HeLa.zip"

    if not archive.exists():
        urlretrieve(DATA_URL, archive)

    extract = work / "dataset"
    dataset_root = extract / "DIC-C2DH-HeLa"
    if not dataset_root.exists():
        extract.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(extract)

    truth_nodes, _, _ = load_ctc_tracking(dataset_root / "01_GT" / "TRA")
    detections = (
        truth_nodes[["t", "z", "y", "x"]]
        .sort_values(["t", "z", "y", "x"])
        .reset_index(drop=True)
    )
    predicted, _ = track_detections(
        detections,
        TrackingConfig(
            max_distance_um=8.0,
            method="mutual_nn",
            voxel_size_um=VOXEL_SIZE_UM,
        ),
    )

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)

    for track_id, group in truth_nodes.groupby("track_id"):
        if len(group) < 8:
            continue
        axes[0].plot(group["x"], group["y"], linewidth=1.0, alpha=0.45)

    for track_id, group in predicted.groupby("track_id"):
        if len(group) < 8:
            continue
        axes[1].plot(group["x"], group["y"], linewidth=1.0, alpha=0.45)

    axes[0].set_title("CTC reference trajectories")
    axes[1].set_title("Predicted trajectories — MNN, 8 µm")
    for ax in axes:
        ax.set_xlabel("x (pixels)")
        ax.set_ylabel("y (pixels)")
        ax.invert_yaxis()
        ax.set_aspect("equal", adjustable="box")

    fig.savefig(ROOT / "ctc_trajectory_comparison.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
