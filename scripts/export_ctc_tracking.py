from __future__ import annotations

import argparse
import sys
from pathlib import Path

import tifffile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai4s_io import DIC_C2DH_HELA_VOXEL_SIZE_UM, ensure_ctc_dataset, load_ctc_tracking, write_ctc_tracking
from ai4s_tracking import TrackingConfig, track_detections


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export reference-centroid tracking predictions as CTC label images."
    )
    parser.add_argument("--sequence", default="01", choices=["01", "02"])
    parser.add_argument("--distance", type=float, default=8.0)
    parser.add_argument("--output", default="ctc_export")
    args = parser.parse_args()

    dataset_root = ensure_ctc_dataset(ROOT / ".benchmark_cache")
    sequence_root = dataset_root / f"{args.sequence}_GT" / "TRA"

    truth_nodes, _, _ = load_ctc_tracking(sequence_root)
    detections = (
        truth_nodes[["t", "z", "y", "x"]]
        .sort_values(["t", "z", "y", "x"])
        .reset_index(drop=True)
    )

    predicted, _ = track_detections(
        detections,
        TrackingConfig(
            max_distance_um=args.distance,
            method="mutual_nn",
            voxel_size_um=DIC_C2DH_HELA_VOXEL_SIZE_UM,
        ),
    )

    shapes = [
        tuple(tifffile.imread(path).shape)
        for path in sorted(sequence_root.glob("man_track*.tif"))
    ]
    output = Path(args.output) / args.sequence
    mapping = write_ctc_tracking(
        predicted,
        output,
        shapes,
        digits=3,
    )

    print(f"exported={output}")
    print(f"tracks={len(mapping)}")
    print(f"distance_um={args.distance}")


if __name__ == "__main__":
    main()
