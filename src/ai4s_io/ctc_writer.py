from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
import tifffile

from ai4s_core import validate_nodes


def write_ctc_tracking(
    nodes: pd.DataFrame,
    output_dir: str | Path,
    frame_shapes: Sequence[tuple[int, ...]] | tuple[int, ...],
    *,
    digits: int = 3,
    prefix: str = "man_track",
) -> dict[int, int]:
    """Write track nodes as deterministic CTC label images.

    Each predicted track receives a positive contiguous label independent of
    the internal zero-based track_id. Collisions after centroid rounding are
    rejected rather than silently overwriting objects.
    """
    validate_nodes(nodes)

    if digits < 1:
        raise ValueError("digits must be >= 1")

    if isinstance(frame_shapes, tuple) and frame_shapes and isinstance(frame_shapes[0], int):
        shapes = [tuple(frame_shapes)] * (int(nodes["t"].max()) + 1 if len(nodes) else 0)
    else:
        shapes = [tuple(shape) for shape in frame_shapes]

    track_ids = sorted(nodes["track_id"].astype(int).unique())
    label_map = {track_id: index + 1 for index, track_id in enumerate(track_ids)}

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for t in sorted(nodes["t"].astype(int).unique()):
        if t < 0 or t >= len(shapes):
            raise ValueError(f"frame {t} has no declared output shape")
        shape = shapes[t]
        if len(shape) not in {2, 3} or any(d <= 0 for d in shape):
            raise ValueError(f"invalid frame shape at t={t}: {shape}")

        canvas = np.zeros(shape, dtype=np.uint32)
        frame_nodes = nodes[nodes["t"].eq(t)]

        for row in frame_nodes.itertuples(index=False):
            coordinates = [int(np.rint(row.y)), int(np.rint(row.x))]
            if len(shape) == 3:
                coordinates = [int(np.rint(row.z)), *coordinates]

            if any(coord < 0 or coord >= shape[axis] for axis, coord in enumerate(coordinates)):
                raise ValueError(
                    f"node {row.node_id} falls outside frame {t}: {coordinates} vs {shape}"
                )

            index = tuple(coordinates)
            if canvas[index] != 0:
                raise ValueError(
                    f"centroid collision in frame {t} at {coordinates}; "
                    "cannot emit lossless CTC labels"
                )

            canvas[index] = label_map[int(row.track_id)]

        tifffile.imwrite(out / f"{prefix}{t:0{digits}d}.tif", canvas)

    return label_map
