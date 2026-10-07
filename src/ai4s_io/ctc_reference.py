from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
import tifffile

from ai4s_core import validate_nodes


def write_ctc_reference_geometry(
    nodes: pd.DataFrame,
    reference_masks: Sequence[str | Path],
    output_dir: str | Path,
    *,
    reference_metadata: pd.DataFrame | None = None,
    digits: int = 3,
    prefix: str = "man_track",
) -> dict[int, int]:
    """Write CTC result masks with reference geometry and predicted IDs."""
    required = {
        "node_id",
        "t",
        "z",
        "y",
        "x",
        "track_id",
        "reference_track_id",
    }
    missing = required - set(nodes.columns)
    if missing:
        raise ValueError(f"nodes missing columns: {sorted(missing)}")
    validate_nodes(nodes[["node_id", "track_id", "t", "z", "y", "x"]])

    mask_paths = [Path(path) for path in reference_masks]
    if not mask_paths:
        raise ValueError("reference_masks must not be empty")

    track_ids = sorted(nodes["track_id"].astype(int).unique())
    label_map = {track_id: index + 1 for index, track_id in enumerate(track_ids)}
    grouped = {int(t): frame for t, frame in nodes.groupby("t", sort=False)}

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for t, path in enumerate(mask_paths):
        mask = tifffile.imread(path)
        frame_nodes = grouped.get(t, nodes.iloc[0:0])
        positive_labels = [int(label) for label in np.unique(mask) if int(label) > 0]

        reference_to_predicted: dict[int, int] = {}
        for row in frame_nodes.itertuples(index=False):
            reference_id = int(row.reference_track_id)
            predicted_id = int(row.track_id)
            previous = reference_to_predicted.get(reference_id)
            if previous is not None and previous != predicted_id:
                raise ValueError(
                    f"reference track {reference_id} maps to multiple predicted tracks at frame {t}"
                )
            reference_to_predicted[reference_id] = predicted_id

        missing_labels = sorted(set(positive_labels) - set(reference_to_predicted))
        if missing_labels:
            raise ValueError(
                f"frame {t} has reference labels without predicted assignments: {missing_labels[:8]}"
            )

        predicted_labels = [
            label_map[reference_to_predicted[reference_id]]
            for reference_id in positive_labels
        ]
        if len(predicted_labels) != len(set(predicted_labels)):
            raise ValueError(f"frame {t} maps multiple reference objects to one predicted track")

        result_mask = np.zeros_like(mask, dtype=np.uint32)
        for reference_id in positive_labels:
            result_mask[mask == reference_id] = label_map[
                reference_to_predicted[reference_id]
            ]
        tifffile.imwrite(out / f"{prefix}{t:0{digits}d}.tif", result_mask)

    parent_map = {track_id: 0 for track_id in track_ids}
    if reference_metadata is not None and not reference_metadata.empty:
        required_metadata = {"track_id", "start_frame", "end_frame", "parent_id"}
        missing_metadata = required_metadata - set(reference_metadata.columns)
        if missing_metadata:
            raise ValueError(
                f"reference_metadata missing columns: {sorted(missing_metadata)}"
            )

        first_prediction: dict[int, tuple[int, int]] = {}
        last_prediction: dict[int, tuple[int, int]] = {}
        for row in nodes.sort_values(["reference_track_id", "t"]).itertuples(index=False):
            reference_id = int(row.reference_track_id)
            prediction_id = int(row.track_id)
            frame = int(row.t)
            first_prediction.setdefault(reference_id, (prediction_id, frame))
            last_prediction[reference_id] = (prediction_id, frame)

        predicted_ranges = (
            nodes.groupby("track_id")["t"]
            .agg(start_frame="min", end_frame="max")
            .astype(int)
        )

        for row in reference_metadata.itertuples(index=False):
            child_reference_id = int(row.track_id)
            parent_reference_id = int(row.parent_id)
            if parent_reference_id <= 0:
                continue
            if child_reference_id not in first_prediction or parent_reference_id not in last_prediction:
                continue

            child_prediction_id, child_start = first_prediction[child_reference_id]
            parent_prediction_id, parent_end = last_prediction[parent_reference_id]
            child_range = predicted_ranges.loc[child_prediction_id]

            compatible = (
                child_prediction_id != parent_prediction_id
                and child_start == int(row.start_frame)
                and parent_end == int(row.end_frame)
                and int(child_range["start_frame"]) == child_start
            )
            if compatible:
                parent_map[child_prediction_id] = label_map[parent_prediction_id]

    track_ranges = (
        nodes.groupby("track_id")["t"]
        .agg(start_frame="min", end_frame="max")
        .astype(int)
        .reset_index()
    )
    with (out / "res_track.txt").open("w", encoding="utf-8") as handle:
        for row in track_ranges.itertuples(index=False):
            prediction_id = int(row.track_id)
            label = label_map[prediction_id]
            parent = parent_map[prediction_id]
            handle.write(f"{label} {int(row.start_frame)} {int(row.end_frame)} {parent}\\n")

    return label_map
