from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import ndimage


def segment_frames(
    frames: np.ndarray,
    *,
    threshold: float | None = None,
    min_area: int = 12,
    z: float = 0.0,
) -> pd.DataFrame:
    """Segment bright cellular objects from a 2-D time-lapse stack.

    This is an intentionally transparent baseline: global thresholding followed
    by connected components and centroid extraction. It is suitable for
    reproducible benchmarking and for feeding the temporal phenotype engine.
    """
    arr = np.asarray(frames, dtype=float)
    if arr.ndim != 3:
        raise ValueError("frames must have shape (t, y, x)")
    if min_area < 1:
        raise ValueError("min_area must be >= 1")

    positive = arr[np.isfinite(arr)]
    if positive.size == 0:
        return pd.DataFrame(columns=["t", "z", "y", "x", "area", "mean_intensity"])

    if threshold is None:
        threshold = float(np.nanpercentile(positive, 92))

    rows: list[dict[str, float | int]] = []
    for t, frame in enumerate(arr):
        mask = np.isfinite(frame) & (frame >= threshold)
        labels, count = ndimage.label(mask)
        if count == 0:
            continue
        objects = ndimage.find_objects(labels)
        for label_id, slc in enumerate(objects, start=1):
            if slc is None:
                continue
            coords = np.argwhere(labels[slc] == label_id)
            area = int(coords.shape[0])
            if area < min_area:
                continue
            yy0, xx0 = slc[0].start, slc[1].start
            yy = coords[:, 0] + yy0
            xx = coords[:, 1] + xx0
            rows.append(
                {
                    "t": int(t),
                    "z": float(z),
                    "y": float(yy.mean()),
                    "x": float(xx.mean()),
                    "area": area,
                    "mean_intensity": float(frame[yy, xx].mean()),
                }
            )

    return pd.DataFrame(rows, columns=["t", "z", "y", "x", "area", "mean_intensity"])
