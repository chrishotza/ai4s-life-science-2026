from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai4s_io import (
    DIC_C2DH_HELA_VOXEL_SIZE_UM,
    ensure_ctc_dataset,
    load_ctc_tracking,
)
from ai4s_io.ctc_reference import write_ctc_reference_geometry
from ai4s_tracking import TrackingConfig, track_detections


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export reference-geometry CTC results for TRA/LNK isolation."
    )
    parser.add_argument("--sequence", default="01", choices=["01", "02"])
    parser.add_argument("--distance", type=float, default=8.0)
    parser.add_argument("--output", default="ctc_reference_export")
    parser.add_argument(
        "--lineage-mode",
        choices=["oracle-compatible", "none"],
        default="oracle-compatible",
        help="Whether to carry frame-compatible reference parent edges into res_track.txt.",
    )
    args = parser.parse_args()

    dataset_root = ensure_ctc_dataset(ROOT / ".benchmark_cache")
    sequence_root = dataset_root / f"{args.sequence}_GT" / "TRA"

    truth_nodes, _, metadata = load_ctc_tracking(sequence_root)
    detections = truth_nodes[["t", "z", "y", "x"]].copy()
    detections["reference_track_id"] = truth_nodes["track_id"].to_numpy()

    predicted, _ = track_detections(
        detections,
        TrackingConfig(
            max_distance_um=args.distance,
            method="mutual_nn",
            voxel_size_um=DIC_C2DH_HELA_VOXEL_SIZE_UM,
        ),
    )

    reference_masks = sorted(sequence_root.glob("man_track*.tif"))
    output = Path(args.output) / args.sequence
    mapping = write_ctc_reference_geometry(
        predicted,
        reference_masks,
        output,
        reference_metadata=metadata if args.lineage_mode == "oracle-compatible" else None,
    )

    print(f"exported={output}")
    print(f"tracks={len(mapping)}")
    print(f"distance_um={args.distance}")
    print("geometry=reference")
    print(f"lineage={args.lineage_mode}")


if __name__ == "__main__":
    main()
