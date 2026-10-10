"""Defensive checks for evidence-only continuous single-cell visualization."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest

from scripts.export_ctc_continuous_cell import (
    normalize_u8, prefix_motion, timeline, visual_frame,
)


def _nodes() -> pd.DataFrame:
    return pd.DataFrame([
        {"node_id": 1, "t": 4, "track_id": 21,
         "x": 3.0, "y": 5.0, "instance_id": 3},
        {"node_id": 2, "t": 5, "track_id": 21,
         "x": 4.0, "y": 5.0, "instance_id": 3},
        {"node_id": 3, "t": 6, "track_id": 21,
         "x": 4.0, "y": 6.0, "instance_id": 3},
        {"node_id": 4, "t": 6, "track_id": 14,
         "x": 2.0, "y": 4.0, "instance_id": 2},
    ])


def test_real_mask_normalization_is_not_synthetic_interpolation():
    x = np.arange(144, dtype=np.uint16).reshape(12, 12)
    result = normalize_u8(x)
    assert result.dtype == np.uint8 and result.shape == x.shape
    assert result.max() == 255
    assert np.all(np.diff(result.ravel()) >= 0)
    assert not normalize_u8(np.ones((12, 12))).any()


def test_actual_track_selects_only_one_identity_and_chronological_frames():
    selected = timeline(_nodes(), 21)
    assert selected["t"].tolist() == [4, 5, 6]
    assert selected["track_id"].nunique() == 1
    with pytest.raises(ValueError, match="absent"):
        timeline(_nodes(), 87)


def test_duplicate_id_frame_is_strictly_rejected():
    v = _nodes()
    duplicate = pd.concat([v, v.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate frames"):
        timeline(duplicate, 21)


def test_no_lookahead_prefix_distance_is_exact_in_physical_units():
    tracks = timeline(_nodes(), 21)
    first = prefix_motion(tracks.iloc[:1])
    second = prefix_motion(tracks.iloc[:2])
    third = prefix_motion(tracks)
    assert first["path_um"] == 0
    assert second["path_um"] == pytest.approx(0.19)
    assert third["path_um"] == pytest.approx(0.38)
    assert third["net_um"] == pytest.approx(0.19 * np.sqrt(2))
    assert third["persistence"] == pytest.approx(np.sqrt(2) / 2)


def test_predicted_label_must_exist_in_actual_mask():
    tracks = timeline(_nodes(), 21)
    raw = np.arange(144, dtype=np.float32).reshape(12, 12)
    pred = np.zeros((12, 12), dtype=np.int32)
    # In frame 4 the identity points to predicted instance label 3.
    with pytest.raises(ValueError, match="not in predicted mask"):
        visual_frame(raw, pred, tracks, 4, 4, 6, 21)
    pred[4:8, 2:5] = 3
    img = visual_frame(raw, pred, tracks, 4, 4, 6, 21)
    assert img.size == (1280, 720)


def test_render_does_not_synthesize_cell_if_unobserved_frame():
    tracks = timeline(_nodes(), 21)
    raw = np.zeros((12, 12), dtype=np.float32)
    pred = np.zeros((12, 12), dtype=np.int32)
    assert visual_frame(raw, pred, tracks, 7, 4, 7, 21).size == (1280, 720)
