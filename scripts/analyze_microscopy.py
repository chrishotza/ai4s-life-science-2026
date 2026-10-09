from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tifffile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai4s_pipeline import PipelineConfig, TemporalPhenotypeEngine
from ai4s_tracking import TrackingConfig


TIFF_SUFFIXES = {".tif", ".tiff"}


def _natural_key(path: Path) -> tuple[object, ...]:
    """Sort frame0002.tif before frame0010.tif."""
    parts = re.split(r"(\d+)", path.name.lower())
    return tuple(int(part) if part.isdigit() else part for part in parts)


def load_image_sequence(source: Path) -> tuple[np.ndarray, list[str]]:
    """Load one grayscale TIFF stack or a directory of 2-D TIFF frames.

    A directory is interpreted as a time series: one TIFF file per time point.
    A stack TIFF may contain (t, y, x) frames or (t, z, y, x) volumes.
    """
    source = source.expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"Input path does not exist: {source}")

    if source.is_dir():
        paths = sorted(
            (p for p in source.iterdir() if p.is_file() and p.suffix.lower() in TIFF_SUFFIXES),
            key=_natural_key,
        )
        if not paths:
            raise FileNotFoundError(f"No .tif or .tiff frames found in {source}")
        frames: list[np.ndarray] = []
        for path in paths:
            image = np.asarray(tifffile.imread(path))
            image = np.squeeze(image)
            if image.ndim != 2:
                raise ValueError(
                    f"Each file in a frame directory must be a 2-D grayscale image; "
                    f"got {image.shape} at {path.name}"
                )
            frames.append(image)
        shapes = {frame.shape for frame in frames}
        if len(shapes) != 1:
            raise ValueError(f"All frames must have the same shape; found {sorted(shapes)}")
        return np.stack(frames, axis=0), [str(p) for p in paths]

    if source.suffix.lower() not in TIFF_SUFFIXES:
        raise ValueError(f"Input must be a TIFF file or a directory of TIFF frames: {source}")

    stack = np.asarray(tifffile.imread(source))
    stack = np.squeeze(stack)
    if stack.ndim == 2:
        stack = stack[None, ...]
    if stack.ndim not in {3, 4}:
        raise ValueError(
            "A TIFF stack must have shape (t, y, x) or (t, z, y, x) after "
            f"removing singleton dimensions; got {stack.shape}"
        )
    if any(size == 0 for size in stack.shape):
        raise ValueError(f"TIFF stack has an empty dimension: {stack.shape}")
    return stack, [str(source)]


def save_trajectory_plot(
    nodes: pd.DataFrame,
    discovered: pd.DataFrame,
    output_path: Path,
) -> None:
    """Render actual pipeline outputs; this is a diagnostic, not a validation score."""
    fig, (ax_tracks, ax_features) = plt.subplots(1, 2, figsize=(13, 5.5), dpi=130)

    cluster_by_track: dict[int, int] = {}
    if {"track_id", "phenotype_cluster"}.issubset(discovered.columns):
        cluster_by_track = {
            int(row.track_id): int(row.phenotype_cluster)
            for row in discovered[["track_id", "phenotype_cluster"]].itertuples(index=False)
        }
    cmap = plt.get_cmap("tab10")

    if nodes.empty:
        ax_tracks.text(0.5, 0.5, "No detections produced", ha="center", va="center")
        ax_features.text(0.5, 0.5, "No phenotype profiles produced", ha="center", va="center")
    else:
        for track_id, group in nodes.sort_values("t").groupby("track_id", sort=True):
            group = group.sort_values("t")
            cluster = cluster_by_track.get(int(track_id), -1)
            color = cmap(cluster % 10) if cluster >= 0 else "0.55"
            if len(group) > 1:
                ax_tracks.plot(group["x"], group["y"], color=color, linewidth=1.2, alpha=0.8)
            ax_tracks.scatter(group["x"], group["y"], color=[color], s=9, alpha=0.85)
        ax_tracks.invert_yaxis()
        ax_tracks.set_xlabel("x (pixels)")
        ax_tracks.set_ylabel("y (pixels)")
        ax_tracks.set_title("Image-derived trajectories")

        if {"mean_speed", "directional_persistence"}.issubset(discovered.columns):
            for cluster, group in discovered.groupby("phenotype_cluster", sort=True):
                label = (
                    str(group["phenotype_cluster_name"].iloc[0])
                    if "phenotype_cluster_name" in group.columns
                    else f"cluster {cluster}"
                )
                color = cmap(int(cluster) % 10) if int(cluster) >= 0 else "0.55"
                ax_features.scatter(
                    group["mean_speed"],
                    group["directional_persistence"],
                    s=35,
                    alpha=0.8,
                    color=color,
                    label=label,
                )
            if not discovered.empty:
                ax_features.legend(fontsize=8, loc="best")
            ax_features.set_xlabel("Mean speed (physical units/frame)")
            ax_features.set_ylabel("Directional persistence")
            ax_features.set_title("Temporal phenotype profiles")
        else:
            ax_features.text(0.5, 0.5, "Insufficient tracks for discovery", ha="center", va="center")

    for axis in (ax_tracks, ax_features):
        axis.grid(alpha=0.18)
    fig.suptitle("Temporal Cellular Phenotype Engine — observed input, computed outputs", fontsize=13)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def write_report(output_dir: Path, summary: dict[str, object]) -> None:
    pipeline = summary["pipeline"]
    assert isinstance(pipeline, dict)
    text = [
        "# Temporal Cellular Phenotype Engine — run report",
        "",
        "## Input and execution",
        f"- Input: `{summary['input']}`",
        f"- Frames: {summary['frames']}",
        f"- Frame/volume shape: `{summary['frame_shape']}`",
        f"- Detected observations: {pipeline['detections']}",
        f"- Predicted tracks: {pipeline['tracks']}",
        f"- Temporal links: {pipeline['temporal_links']}",
        f"- Candidate lineage edges: {pipeline['lineage_edges']}",
        f"- Phenotype profiles: {pipeline['phenotype_rows']}",
        f"- Discovered groups: {pipeline['discovered_clusters']}",
        "",
        "## Interpretation boundary",
        "",
        "This run reports image-derived observations and trajectory features. Cluster names are",
        "descriptive groups, not validated biological states or clinical diagnoses. The default",
        "detector is a transparent threshold/connected-component baseline; image quality, contrast,",
        "crowding, pixel calibration, and detection settings can materially affect the result.",
        "For scientific claims, compare against independent annotations and report held-out metrics.",
        "",
        "## Output files",
        "",
        "- `nodes.csv`: observations with track identifiers and measured object attributes.",
        "- `temporal_edges.csv`: links between observations across frames.",
        "- `lineage_candidates.csv`: candidate parent/child events, not confirmed divisions.",
        "- `phenotypes.csv`: trajectory-level features.",
        "- `discovered_phenotypes.csv`: descriptive unsupervised groups and diagnostics.",
        "- `summary.json`: machine-readable run configuration and counts.",
        "- `overview.png`: visualization of computed trajectories and phenotype features.",
        "",
    ]
    (output_dir / "report.md").write_text("\n".join(text), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Temporal Cellular Phenotype Engine on a TIFF stack or a directory "
            "containing one 2-D grayscale TIFF per time point."
        )
    )
    parser.add_argument("input", type=Path, help="TIFF stack (.tif/.tiff) or frame directory")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Absolute detector threshold; default is the 92nd percentile of finite input pixels",
    )
    parser.add_argument("--min-area", type=int, default=12, help="Minimum connected-component size")
    parser.add_argument(
        "--max-distance-um",
        type=float,
        default=5.0,
        help="Maximum allowed distance between detections, in physical units",
    )
    parser.add_argument(
        "--voxel-size-um",
        type=float,
        nargs=3,
        metavar=("Z", "Y", "X"),
        default=(1.0, 1.0, 1.0),
        help="Physical sampling in micrometers for z, y, x (default: 1 1 1)",
    )
    parser.add_argument("--clusters", type=int, default=3, help="Number of descriptive phenotype groups")
    parser.add_argument("--random-state", type=int, default=17, help="Random seed for phenotype discovery")
    parser.add_argument(
        "--z-coordinate",
        type=float,
        default=0.0,
        help="Fixed z coordinate for 2-D input",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.min_area < 1:
        raise SystemExit("--min-area must be >= 1")
    if args.max_distance_um <= 0:
        raise SystemExit("--max-distance-um must be > 0")
    if args.clusters < 2:
        raise SystemExit("--clusters must be >= 2")

    frames, input_files = load_image_sequence(args.input)
    output_dir = args.output.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    voxel_size = tuple(float(v) for v in args.voxel_size_um)
    config = PipelineConfig(
        tracking=TrackingConfig(
            max_distance_um=args.max_distance_um,
            voxel_size_um=voxel_size,
        ),
        detection_threshold=args.threshold,
        detection_min_area=args.min_area,
        detection_z=args.z_coordinate,
        phenotype_clusters=args.clusters,
        phenotype_random_state=args.random_state,
    )
    result = TemporalPhenotypeEngine(config).run_frames(frames)

    outputs = {
        "nodes.csv": result.nodes,
        "temporal_edges.csv": result.temporal_edges,
        "lineage_candidates.csv": result.lineage_edges,
        "phenotypes.csv": result.phenotypes,
        "discovered_phenotypes.csv": result.discovered,
    }
    for filename, frame in outputs.items():
        frame.to_csv(output_dir / filename, index=False)

    summary: dict[str, object] = {
        "input": str(args.input.expanduser().resolve()),
        "input_files": input_files,
        "frames": int(frames.shape[0]),
        "frame_shape": tuple(int(v) for v in frames.shape[1:]),
        "parameters": {
            "detection_threshold": args.threshold,
            "detection_min_area": args.min_area,
            "max_distance_um": args.max_distance_um,
            "voxel_size_um": voxel_size,
            "phenotype_clusters": args.clusters,
            "random_state": args.random_state,
        },
        "pipeline": result.summary(),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    save_trajectory_plot(result.nodes, result.discovered, output_dir / "overview.png")
    write_report(output_dir, summary)

    print(json.dumps(summary, indent=2, default=str))
    print(f"\nOutputs written to: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
