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


def audit_track_color_prefixes(
    predicted_masks: np.ndarray,
    tracked_nodes: pd.DataFrame,
    *,
    min_adjacent_iou: float = 0.50,
    min_competitor_margin: float = 0.25,
    max_area_ratio: float = 1.90,
    min_consecutive_frames: int = 3,
) -> dict[int, dict[str, object]]:
    """Find a safe leading contiguous segment of each model-predicted track.

    This is post-hoc visualization QC, not proof of biological identity.
    A suspect association ends the color: it is NEVER silently restored.
    Every cell still remains present in uncolored microscopy.
    """
    masks = np.asarray(predicted_masks)
    if masks.ndim != 3 or masks.shape[0] < 2:
        raise ValueError("expected (t,y,x) masks with at least 2 frames")
    if not np.issubdtype(masks.dtype, np.integer) or (masks < 0).any():
        raise ValueError("masks require nonnegative integer instance labels")
    required = {"t", "track_id", "instance_id"}
    if not required.issubset(tracked_nodes.columns):
        raise ValueError("missing tracking identity fields")
    if tracked_nodes[list(required)].isna().any().any():
        raise ValueError("null identity values")
    if (tracked_nodes[["t", "track_id"]].duplicated().any()
            or tracked_nodes[["t", "instance_id"]].duplicated().any()):
        raise ValueError("ambiguous track or instance ownership")
    if ((tracked_nodes["t"] < 0).any()
            or (tracked_nodes["t"] >= len(masks)).any()):
        raise ValueError("track timestamp outside microscopy")
    if min_consecutive_frames < 2:
        raise ValueError("min_consecutive_frames must be >=2")
    by_frame: list[dict[int, int]] = []
    for t in range(len(masks)):
        rows = tracked_nodes[tracked_nodes["t"].eq(t)]
        actual = {int(v) for v in np.unique(masks[t]) if v > 0}
        expected = {int(v) for v in rows["instance_id"]}
        if actual != expected:
            raise ValueError(f"frame {t}: instance-mask inventory mismatch")
        by_frame.append({int(r.track_id): int(r.instance_id)
                         for r in rows.itertuples(index=False)})
    result = {}
    for track_id in sorted(int(v) for v in tracked_nodes["track_id"].unique()):
        present = [t for t in range(len(masks)) if track_id in by_frame[t]]
        start = present[0]
        last_good = start
        broken = None
        for t in range(start + 1, len(masks)):
            if t not in present or t-1 not in present:
                broken = "missing_temporal_observation"
                break
            a = masks[t-1] == by_frame[t-1][track_id]
            b = masks[t] == by_frame[t][track_id]
            n_a, n_b = int(a.sum()), int(b.sum())
            if not n_a or not n_b:
                broken = "empty_predicted_instance"
                break
            own = float(np.logical_and(a,b).sum()/np.logical_or(a,b).sum())
            competing = 0.0
            for other_id, label in by_frame[t].items():
                if other_id == track_id:
                    continue
                other = masks[t] == label
                competing = max(competing, float(
                    np.logical_and(a,other).sum()/np.logical_or(a,other).sum()
                ))
            if max(n_a,n_b)/min(n_a,n_b) > max_area_ratio:
                broken = "abrupt_mask_area_change"
            elif own < min_adjacent_iou:
                broken = "low_self_overlap"
            elif own - competing < min_competitor_margin:
                broken = "possible_identity_swap"
            if broken:
                break
            last_good = t
        enough = last_good-start+1 >= min_consecutive_frames
        result[track_id] = {
            "first_frame": start,
            "colored_through_frame": last_good if enough else None,
            "observed_frames": len(present),
            "safe_prefix_frames": last_good-start+1,
            "first_failure": broken,
        }
    return result
