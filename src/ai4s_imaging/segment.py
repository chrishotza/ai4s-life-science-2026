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
    """Segment bright cellular objects from 2-D+t or 3-D+t microscopy.

    This is an intentionally transparent baseline: global thresholding followed
    by connected components and centroid extraction. It is suitable for
    reproducible benchmarking and for feeding the temporal phenotype engine.
    """
    arr = np.asarray(frames, dtype=float)
    if arr.ndim not in {3, 4}:
        raise ValueError("frames must have shape (t, y, x) or (t, z, y, x)")
    spatial_ndim = arr.ndim - 1

    if min_area < 1:
        raise ValueError("min_area must be >= 1")
    if threshold is not None and not np.isfinite(threshold):
        raise ValueError("threshold must be finite when provided")

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

            if spatial_ndim == 2:
                y0, x0 = slc[0].start, slc[1].start
                yy = coords[:, 0] + y0
                xx = coords[:, 1] + x0
                zz = np.full(len(coords), float(z), dtype=float)
            else:
                z0, y0, x0 = slc[0].start, slc[1].start, slc[2].start
                zz = coords[:, 0] + z0
                yy = coords[:, 1] + y0
                xx = coords[:, 2] + x0

            rows.append(
                {
                    "t": int(t),
                    "z": float(np.mean(zz)),
                    "y": float(np.mean(yy)),
                    "x": float(np.mean(xx)),
                    "area": area,
                    "mean_intensity": float(frame[tuple(
                        coords[:, axis] + slc[axis].start for axis in range(spatial_ndim)
                    )].mean()),
                }
            )

    return pd.DataFrame(rows, columns=["t", "z", "y", "x", "area", "mean_intensity"])
