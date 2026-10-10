"""Regression gates preventing attractive but misleading cell color swaps."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai4s_imaging.identity_confidence import audit_track_color_continuity


def _nodes(n: int = 3) -> pd.DataFrame:
    return pd.DataFrame([
        {"t": t, "track_id": ident, "instance_id": ident + 1}
        for t in range(n) for ident in (0, 1)
    ])


def _clean() -> np.ndarray:
    masks = np.zeros((3, 30, 30), dtype=np.int32)
    for t in range(3):
        masks[t, 3:9, 3+t:9+t] = 1
        masks[t, 18:24, 19-t:25-t] = 2
    return masks


def test_model_native_tracks_remain_distinct_with_mask_ids_moving():
    result = audit_track_color_continuity(_clean(), _nodes())
    assert set(result) == {0, 1}
    assert all(item["eligible"] for item in result.values())
    assert min(row["minimum_competitor_margin"] for row in result.values()) > 0.6


def test_apparent_identity_swap_is_suppressed_not_recolored():
    masks = _clean()
    masks[1] = np.where(masks[1] == 1, 2, np.where(masks[1] == 2, 1, 0))
    result = audit_track_color_continuity(masks, _nodes())
    assert not result[0]["eligible"]
    assert not result[1]["eligible"]


def test_appearance_gap_blocks_synthetic_continuity():
    masks = _clean()
    masks[1, 3:9, 4:10] = 0
    nodes = _nodes()
    nodes = nodes[~(nodes["t"].eq(1) & nodes["track_id"].eq(0))]
    result = audit_track_color_continuity(masks, nodes)
    assert result[0]["reason"] == "not_all_frames"


def test_sudden_segmentation_merger_area_change_is_blocked():
    masks = _clean()
    masks[1, :15, :15] = 1
    result = audit_track_color_continuity(masks, _nodes())
    assert result[0]["reason"] == "abrupt_mask_change"


def test_inconsistent_instance_labels_fail_closed():
    masks = _clean()
    nodes = _nodes().iloc[:-1]
    with pytest.raises(ValueError, match="instances differ"):
        audit_track_color_continuity(masks, nodes)


def test_duplicated_instance_ownership_is_rejected():
    nodes = _nodes()
    nodes.loc[1, "instance_id"] = 1
    with pytest.raises(ValueError, match="ambiguous instance ID"):
        audit_track_color_continuity(_clean(), nodes)
