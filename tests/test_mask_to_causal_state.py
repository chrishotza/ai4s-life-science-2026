"""Masks -> bounding boxes -> actual tracker -> causal state predictions."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai4s_imaging import instances_to_box_detections
from ai4s_tracking import TrackingConfig, track_detections
from ai4s_phenotype import causal_shape_motion_features, TemporalStateProbe


def synthetic_instance_video():
    frames = np.zeros((7, 96, 96), dtype=np.float32)
    masks = np.zeros_like(frames, dtype=np.int32)
    for t in range(7):
        # IDs intentionally alternate, proving the tracker, not mask labels,
        # creates persistent biological-observation identities.
        masks[t, 15:25, 12+t:22+t] = 1+t*10
        masks[t, 55:67, 65-t:77-t] = 2+t*10
        frames[t][masks[t] > 0] = 100
    return frames, masks


def test_predicted_masks_to_real_tracking_and_causal_features():
    images, masks = synthetic_instance_video()
    detections = instances_to_box_detections(images, masks, sequence="PRED")
    assert len(detections) == 14
    assert set(("sequence", "t", "x", "y", "z", "xmin", "ymin",
                "width", "height", "instance_id")).issubset(detections.columns)
    assert set(detections["width"]) == {10, 12}
    assert set(detections["height"]) == {10, 12}
    nodes, links = track_detections(
        detections, TrackingConfig(method="hungarian", max_distance_um=6.0)
    )
    assert nodes["track_id"].nunique() == 2
    assert len(links) == 12
    causal = causal_shape_motion_features(nodes.rename(columns={"t": "frame"}))
    assert len(causal) == 14
    assert causal.groupby(["sequence", "track_id"])["frame"].nunique().eq(7).all()
    # Fit only on separate synthetic tracks, then infer on predicted-mask data.
    train = nodes.rename(columns={"t": "frame"}).copy()
    train["sequence"] = "TRAIN"
    train["label"] = np.where(train["track_id"] == train["track_id"].min(),
                              "EarlyMitosis", "LateMitosis")
    probe = TemporalStateProbe.fit(train)
    predicted = probe.predict(
        nodes.rename(columns={"t": "frame"}),
        require_heldout_sequences=True,
    )
    assert len(predicted) == len(nodes)
    assert set(predicted["predicted_state"]).issubset(
        {"EarlyMitosis", "LateMitosis"}
    )
    assert predicted["score_of_predicted_state"].between(0, 1).all()


def test_empty_masks_preserve_box_schema():
    f = np.zeros((2, 32, 32), dtype="float32")
    m = np.zeros_like(f, dtype="int32")
    result = instances_to_box_detections(f, m, sequence="TEST")
    assert result.empty
    assert {"xmin", "ymin", "width", "height"}.issubset(result.columns)


def test_invalid_mask_ids_are_rejected():
    f, masks = synthetic_instance_video()
    with pytest.raises(ValueError):
        instances_to_box_detections(f, masks.astype(float))
    masks[0, 0, 0] = -1
    with pytest.raises(ValueError):
        instances_to_box_detections(f, masks)
