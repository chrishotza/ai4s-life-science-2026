"""Invariants of the actual exported causal temporal phenotype representation."""
import numpy as np
import pandas as pd
import pytest

from ai4s_phenotype import (
    causal_shape_motion_features, STATIC_FEATURES, MOTION_FEATURES,
    HISTORY_FEATURES,
)


def sample():
    return pd.DataFrame([
        dict(sequence="A", track_id=1, frame=1, xmin=0, ymin=0,
             width=10, height=10, label="EarlyMitosis"),
        dict(sequence="A", track_id=1, frame=3, xmin=4, ymin=0,
             width=12, height=10, label="LateMitosis"),
        dict(sequence="A", track_id=2, frame=1, xmin=100, ymin=0,
             width=20, height=20, label="CellDeath"),
        dict(sequence="A", track_id=1, frame=5, xmin=8, ymin=0,
             width=14, height=12, label="LateMitosis"),
        dict(sequence="B", track_id=1, frame=1, xmin=5, ymin=5,
             width=10, height=10, label="EarlyMitosis"),
    ])


def test_api_schema_and_no_cross_sequence_id_collision():
    result = causal_shape_motion_features(sample())
    assert len(result) == 5
    assert set(STATIC_FEATURES + HISTORY_FEATURES).issubset(result.columns)
    assert set(MOTION_FEATURES).issubset(result.columns)
    first = result[result["obs_age"] == 0]
    assert len(first) == 3
    assert (first["speed_cell_sizes"] == 0).all()
    assert (first["accel_speed"] == 0).all()
    assert (first["cumulative_motion_size"] == 0).all()
    assert all(result.groupby(["sequence", "track_id"])["time_age"].min() == 0)


def test_past_only_no_label_leakage_no_future_leakage():
    original = sample()
    full = causal_shape_motion_features(original)
    stripped = original[~((original.sequence == "A") & (original.track_id == 1)
                          & (original.frame == 5))]
    partial = causal_shape_motion_features(stripped)
    selected = (full.sequence == "A") & (full.track_id == 1) & (full.frame <= 3)
    past = full.loc[selected, list(STATIC_FEATURES + HISTORY_FEATURES)]
    selected_p = (partial.sequence == "A") & (partial.track_id == 1)
    prefix = partial.loc[selected_p, list(STATIC_FEATURES + HISTORY_FEATURES)]
    np.testing.assert_allclose(past.to_numpy(float), prefix.to_numpy(float),
                               rtol=0, atol=1e-12)
    changed = original.copy()
    changed["label"] = ["X"] * len(changed)
    feat = causal_shape_motion_features(changed)
    np.testing.assert_allclose(
        full[list(STATIC_FEATURES + HISTORY_FEATURES)].to_numpy(float),
        feat[list(STATIC_FEATURES + HISTORY_FEATURES)].to_numpy(float),
        rtol=0, atol=1e-12,
    )


def test_input_order_does_not_change_values():
    reference = causal_shape_motion_features(sample())
    shuffled = causal_shape_motion_features(sample().sample(frac=1, random_state=42))
    pd.testing.assert_frame_equal(reference, shuffled)


@pytest.mark.parametrize("mutator", [
    lambda x: x.drop(columns=["frame"]),
    lambda x: x.assign(width=0),
    lambda x: x.assign(xmin=np.nan),
    lambda x: pd.concat([x, x.iloc[[0]]], ignore_index=True),
    lambda x: x.assign(frame=[1.1, 3, 1, 5, 1]),
])
def test_fails_closed_on_invalid_data(mutator):
    with pytest.raises(ValueError):
        causal_shape_motion_features(mutator(sample()))


def test_empty_valid_input():
    result = causal_shape_motion_features(sample().iloc[:0])
    assert len(result) == 0
    assert "speed_cell_sizes" in result
