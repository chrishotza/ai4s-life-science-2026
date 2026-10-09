"""Causal per-observation morphology and motion features.

No future observations or phenotype labels are used as predictors.
Annotations may provide track IDs and boxes, or predicted tracking can do so.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

STATIC_FEATURES = ("log_width", "log_height", "log_area", "aspect")
MOTION_FEATURES = (
    "speed_cell_sizes", "area_log_deriv", "width_log_deriv",
    "height_log_deriv", "aspect_deriv", "accel_speed",
)
HISTORY_FEATURES = (
    "obs_age", "time_age", "time_step", "speed_cell_sizes",
    "area_log_deriv", "width_log_deriv", "height_log_deriv",
    "aspect_deriv", "accel_speed", "cumulative_motion_size",
)
_REQUIRED = ("sequence", "track_id", "frame", "xmin", "ymin", "width", "height")


def causal_shape_motion_features(observations: pd.DataFrame) -> pd.DataFrame:
    """One causal feature row per detected/annotated cell observation.

    Frames must be unique within a (sequence, track_id). Predictions at time t
    use only geometry at or before time t. The optional label is forwarded
    solely as metadata for a separate evaluation.
    """
    missing = set(_REQUIRED) - set(observations.columns)
    if missing:
        raise ValueError(f"Missing observation fields: {sorted(missing)}")
    data = observations.copy()
    for field in ("frame", "xmin", "ymin", "width", "height"):
        try:
            data[field] = pd.to_numeric(data[field], errors="raise")
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid numeric values in {field}") from exc
        if not np.isfinite(data[field].to_numpy(dtype=float)).all():
            raise ValueError(f"Nonfinite geometry in {field}")
    if np.any(data["width"] <= 0) or np.any(data["height"] <= 0):
        raise ValueError("Width and height must be positive")
    if np.any(data["frame"] != data["frame"].astype(np.int64)):
        raise ValueError("Frame numbers must be integers")
    if data.duplicated(["sequence", "track_id", "frame"]).any():
        raise ValueError("Duplicate sequence/track/frame observations")
    data = data.sort_values(["sequence", "track_id", "frame"]).reset_index(drop=True)
    if data.empty:
        cols = ["sequence", "track_id", "frame"]
        if "label" in data:
            cols.append("label")
        return pd.DataFrame(columns=cols+list(STATIC_FEATURES)+list(HISTORY_FEATURES))

    g = data.groupby(["sequence", "track_id"], sort=False)
    width = data["width"].to_numpy(dtype=float)
    height = data["height"].to_numpy(dtype=float)
    area = width * height
    cx = data["xmin"].to_numpy(dtype=float) + width / 2
    cy = data["ymin"].to_numpy(dtype=float) + height / 2
    aspect = width / height
    frame = data["frame"].to_numpy(dtype=np.int64)
    prior_frame = g["frame"].shift().to_numpy(dtype=float)
    first = np.isnan(prior_frame)
    dt = np.where(first, 1, frame - prior_frame)
    if (dt <= 0).any():
        raise ValueError("Non-increasing frame")
    pw = g["width"].shift().to_numpy(dtype=float)
    ph = g["height"].shift().to_numpy(dtype=float)
    pa = pw * ph
    paspect = pw / ph
    pcx = (g["xmin"].shift()+g["width"].shift()/2).to_numpy(dtype=float)
    pcy = (g["ymin"].shift()+g["height"].shift()/2).to_numpy(dtype=float)
    speed = np.where(
        first, 0.0, np.hypot(cx-pcx, cy-pcy) /
        (np.maximum(np.sqrt((area+pa)/2), 1.0)*dt)
    )
    speed[first] = 0.0

    def deriv(now, prior):
        value = np.zeros(len(data), dtype=float)
        valid = ~first
        value[valid] = (now[valid]-prior[valid])/dt[valid]
        return value

    previous_speed = pd.Series(speed).groupby(
        [data["sequence"], data["track_id"]], sort=False
    ).shift().fillna(0).to_numpy()
    cumulative = pd.Series(speed*np.where(first, 0, dt)).groupby(
        [data["sequence"], data["track_id"]], sort=False
    ).cumsum().to_numpy()
    out = data[["sequence", "track_id", "frame"]].copy()
    if "label" in data:
        out["label"] = data["label"].to_numpy()
    out["log_width"] = np.log(width)
    out["log_height"] = np.log(height)
    out["log_area"] = np.log(area)
    out["aspect"] = aspect
    out["obs_age"] = g.cumcount().to_numpy()
    out["time_age"] = frame - g["frame"].transform("min").to_numpy()
    out["time_step"] = np.where(first, 0, dt)
    out["speed_cell_sizes"] = speed
    out["area_log_deriv"] = deriv(np.log(area), np.log(pa))
    out["width_log_deriv"] = deriv(np.log(width), np.log(pw))
    out["height_log_deriv"] = deriv(np.log(height), np.log(ph))
    out["aspect_deriv"] = deriv(aspect, paspect)
    out["accel_speed"] = np.where(first, 0, (speed-previous_speed)/dt)
    out["cumulative_motion_size"] = cumulative
    values = out[list(STATIC_FEATURES)+list(HISTORY_FEATURES)].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite calculated temporal features")
    return out
