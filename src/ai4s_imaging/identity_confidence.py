"""Conservative identity-color eligibility from predicted masks and track IDs.

A stable appearance is not independent verification of biological identity.
This QA uses predictions only and must not influence ground-truth scoring.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def audit_track_color_continuity(
    predicted_masks: np.ndarray,
    tracked_nodes: pd.DataFrame,
    *,
    min_neighbor_iou: float = 0.60,
    min_competitor_margin: float = 0.40,
    max_area_ratio: float = 1.60,
) -> dict[int, dict[str, object]]:
    """Score full-window predicted tracks; ambiguous identities are not colored.

    A track is display-eligible only if it exists on *every* raw-image frame,
    matches exactly one predicted instance on each frame, never changes
    mask area too abruptly, and has a sufficiently strong same-ID overlap
    versus all competing tracks in the next frame. This is a conservative
    VIDEO criterion, NOT a biological validation or an official tracking metric.
    """
    masks = np.asarray(predicted_masks)
    if masks.ndim != 3 or masks.shape[0] < 2:
        raise ValueError("predicted_masks must have (>=2 frames,y,x) shape")
    if not np.issubdtype(masks.dtype, np.integer) or np.any(masks < 0):
        raise ValueError("instance masks must contain nonnegative integer labels")
    required = {"t", "track_id", "instance_id"}
    if not required.issubset(tracked_nodes.columns):
        raise ValueError("missing t, track_id or instance_id")
    if tracked_nodes[list(required)].isna().any().any():
        raise ValueError("null track/mask ID")
    if tracked_nodes[["t", "instance_id"]].duplicated().any():
        raise ValueError("ambiguous instance ID within a frame")
    if tracked_nodes[["t", "track_id"]].duplicated().any():
        raise ValueError("duplicate track identity within a frame")
    if (tracked_nodes["t"] < 0).any() or (tracked_nodes["t"] >= len(masks)).any():
        raise ValueError("tracking timestamps exceed the raw-image window")

    by_time: list[dict[int, np.ndarray]] = []
    for t in range(len(masks)):
        mapping = {}
        rows = tracked_nodes[tracked_nodes["t"].eq(t)]
        predicted = {int(z) for z in np.unique(masks[t]) if int(z) > 0}
        observed = {int(z) for z in rows["instance_id"]}
        if predicted != observed:
            raise ValueError(f"frame {t}: predicted instances differ from tracked observations")
        for row in rows.itertuples(index=False):
            mapping[int(row.track_id)] = masks[t] == int(row.instance_id)
        by_time.append(mapping)
    ids = sorted(int(x) for x in tracked_nodes["track_id"].unique())
    all_frames = set(range(len(masks)))
    output = {}
    for ident in ids:
        present = {t for t in range(len(masks)) if ident in by_time[t]}
        if present != all_frames:
            output[ident] = {"eligible": False, "reason": "not_all_frames",
                             "observations": len(present)}
            continue
        overlaps, margins, area_ratios = [], [], []
        for t in range(len(masks)-1):
            old, nxt = by_time[t][ident], by_time[t+1][ident]
            own = float(np.logical_and(old, nxt).sum() / np.logical_or(old, nxt).sum())
            competitors = [
                float(np.logical_and(old, other).sum() / np.logical_or(old, other).sum())
                for other_id, other in by_time[t+1].items() if other_id != ident
            ]
            area = (float(old.sum()), float(nxt.sum()))
            if min(area) == 0:
                raise ValueError("predicted tracked cell has empty mask")
            overlaps.append(own)
            margins.append(own-max(competitors, default=0.0))
            area_ratios.append(max(area)/min(area))
        reason = (
            "abrupt_mask_change" if max(area_ratios) > max_area_ratio
            else "low_temporal_overlap" if min(overlaps) < min_neighbor_iou
            else "identity_ambiguous" if min(margins) < min_competitor_margin
            else "eligible"
        )
        output[ident] = {
            "eligible": reason == "eligible",
            "reason": reason,
            "observations": len(present),
            "minimum_adjacent_mask_iou": float(min(overlaps)),
            "minimum_competitor_margin": float(min(margins)),
            "maximum_adjacent_area_ratio": float(max(area_ratios)),
        }
    return output
