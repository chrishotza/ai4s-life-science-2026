"""Model-predicted cell colors persist across masks and block ambiguous splits."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai4s_imaging.track_colors import stable_rgb, track_color_map, tracked_color_overlay


def nodes():
    return pd.DataFrame([
        {"node_id":0,"t":0,"track_id":7,"x":5,"y":5,"instance_id":1},
        {"node_id":1,"t":1,"track_id":7,"x":6,"y":5,"instance_id":3},
        {"node_id":2,"t":2,"track_id":8,"x":4,"y":4,"instance_id":1},
        {"node_id":3,"t":2,"track_id":9,"x":8,"y":5,"instance_id":2},
        {"node_id":4,"t":3,"track_id":8,"x":4,"y":6,"instance_id":2},
        {"node_id":5,"t":3,"track_id":9,"x":9,"y":5,"instance_id":1},
    ])


def edges():
    return pd.DataFrame([
        {"source_id":1,"target_id":2,"edge_type":"division_parent"},
        {"source_id":1,"target_id":3,"edge_type":"division_parent"},
    ])


def test_color_stable_across_frames_even_if_instance_id_changes():
    assert stable_rgb(7) == stable_rgb(7)
    assert stable_rgb(7) != stable_rgb(8)
    with pytest.raises(ValueError):
        stable_rgb(-1)
    colors = track_color_map(nodes())
    assert colors[7].rgb == stable_rgb(7)
    assert not colors[7].lineage_candidate


def test_two_unambiguous_candidate_daughters_inherit_related_not_identical_hues():
    colors = track_color_map(nodes(), edges())
    assert colors[8].origin_id == colors[9].origin_id == 7
    assert colors[8].lineage_candidate and colors[9].lineage_candidate
    assert len({colors[7].rgb, colors[8].rgb, colors[9].rgb}) == 3


def test_ongoing_parent_cannot_be_declared_divided():
    continuing = pd.concat([nodes(), pd.DataFrame([{
        "node_id":6,"t":2,"track_id":7,"x":7,"y":5,"instance_id":3
    }])],ignore_index=True)
    colors = track_color_map(continuing, edges())
    assert not colors[8].lineage_candidate
    assert not colors[9].lineage_candidate


def test_ambiguous_two_parent_child_rejected():
    extra = pd.DataFrame([{"node_id":6,"t":1,"track_id":10,
                           "x":4,"y":4,"instance_id":4}])
    more = pd.DataFrame([{"source_id":6,"target_id":2,
                          "edge_type":"division_parent"}])
    colors = track_color_map(pd.concat([nodes(),extra],ignore_index=True),
                             pd.concat([edges(),more],ignore_index=True))
    assert not colors[8].lineage_candidate
    assert not colors[9].lineage_candidate


def test_overlay_uses_track_id_not_ephemeral_instance_mask_id():
    selected = nodes().iloc[:2]
    colors = track_color_map(selected)
    raw = np.arange(256,dtype=np.uint16).reshape(16,16)
    a = np.zeros((16,16),np.int32);a[3:8,3:8]=1
    b = np.zeros((16,16),np.int32);b[3:8,4:9]=3
    result_a = np.asarray(tracked_color_overlay(raw,a,selected,0,colors))
    result_b = np.asarray(tracked_color_overlay(raw,b,selected,1,colors))
    assert result_a.shape == result_b.shape == (16,16,3)
    with pytest.raises(ValueError,match="predicted instances"):
        tracked_color_overlay(raw,a,selected,1,colors)


def test_duplicate_detection_nodes_are_rejected():
    corrupted = pd.concat([nodes(), nodes().iloc[[0]]],ignore_index=True)
    with pytest.raises(ValueError,match="duplicate detection"):
        track_color_map(corrupted)
