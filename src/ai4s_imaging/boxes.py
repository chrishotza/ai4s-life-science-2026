"""Instance-mask → tracker observations with per-cell bounding-box geometry.

Bridges pretrained or supervised instance segmentation to the causal temporal
phenotype-state probe without reading any expert or biological outcome labels.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .supervised import instances_to_detections


def instances_to_box_detections(
    frames: np.ndarray,
    instance_masks: np.ndarray,
    *,
    sequence: str = "sequence",
) -> pd.DataFrame:
    """Return tracker-compatible centroids *and* per-instance bounding boxes.

    Output includes sequence, t,z,y,x,area,mean_intensity,instance_id,
    xmin,ymin,width,height. Box geometry is computed solely from predicted
    instance-mask pixels. Instance IDs need not stay consistent across frames;
    the downstream tracker assigns persistent track_id values.
    """
    if not isinstance(sequence, str) or not sequence.strip():
        raise ValueError("sequence must be a nonempty string")
    data = np.asarray(frames)
    masks = np.asarray(instance_masks)
    if data.ndim != 3 or masks.shape != data.shape:
        raise ValueError("frames and instance_masks must have shape (t,y,x)")
    if not np.issubdtype(masks.dtype, np.integer) or np.any(masks < 0):
        raise ValueError("instance_masks must contain nonnegative integer IDs")
    if not np.isfinite(data).all():
        raise ValueError("frames contain invalid image pixel values")

    observations = instances_to_detections(data, masks).copy()
    observations.insert(0, "sequence", sequence)
    if observations.empty:
        for col in ("xmin", "ymin", "width", "height"):
            observations[col] = pd.Series(dtype="int64")
        return observations

    bounds: dict[tuple[int, int], tuple[int, int, int, int]] = {}
    for t, mask in enumerate(masks):
        for label_id in np.unique(mask):
            if int(label_id) <= 0:
                continue
            yy, xx = np.nonzero(mask == label_id)
            if len(yy) == 0:
                continue
            x0, y0 = int(xx.min()), int(yy.min())
            w, h = int(xx.max()-x0+1), int(yy.max()-y0+1)
            bounds[(t, int(label_id))] = (x0, y0, w, h)
    if len(bounds) != len(observations):
        raise AssertionError("Every prediction must have exactly one box")
    rows = [
        bounds[(int(row.t), int(row.instance_id))]
        for row in observations.itertuples(index=False)
    ]
    observations[["xmin", "ymin", "width", "height"]] = np.asarray(rows,dtype=int)
    return observations
