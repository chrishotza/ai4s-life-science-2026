"""Contract tests for the deployable, causal supervised temporal state probe."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai4s_phenotype import TemporalStateProbe


def make_labeled(sequence, shift=0.0):
    rows=[]
    for ident, cls, speed in ((1, "EarlyMitosis", 1.0),
                              (2, "LateMitosis", 5.0)):
        for t in range(1, 8):
            rows.append(dict(
                sequence=sequence, track_id=ident, frame=t,
                xmin=speed*t+shift, ymin=10+ident, width=10+ident+t*0.2,
                height=11+ident, label=cls,
            ))
    return pd.DataFrame(rows)


def test_probe_can_fit_and_predict_heldout_sequences_without_labels():
    train=make_labeled("TRAIN")
    holdout=make_labeled("HOLDOUT",10).drop(columns=["label"])
    classifier=TemporalStateProbe.fit(train,feature_set="static_motion")
    outcome=classifier.predict(holdout,require_heldout_sequences=True)
    assert len(outcome)==len(holdout)
    assert set(outcome["predicted_state"]).issubset({"EarlyMitosis","LateMitosis"})
    assert np.all((outcome["score_of_predicted_state"] >= 0) &
                  (outcome["score_of_predicted_state"] <= 1))
    np.testing.assert_allclose(
        outcome["score_EarlyMitosis"]+outcome["score_LateMitosis"],
        np.ones(len(outcome)),atol=1e-12,
    )
    assert "label" not in outcome.columns
    assert outcome["has_temporal_motion"].sum() == 12
    assert (outcome.loc[~outcome["has_temporal_motion"], "prior_observations"] == 0).all()
    assert (outcome["last_observation_gap"] <= 1).all()


def test_static_ablation_is_equal_capacity_and_disables_motion():
    train=make_labeled("TRAIN")
    baseline=TemporalStateProbe.fit(train,feature_set="static")
    temporal=TemporalStateProbe.fit(train,feature_set="static_motion")
    assert len(baseline.feature_columns)==4
    assert len(temporal.feature_columns)==10


def test_blocks_in_sample_scientific_evaluation():
    classifier=TemporalStateProbe.fit(make_labeled("TRAIN"))
    with pytest.raises(ValueError,match="sequences used for training"):
        classifier.predict(make_labeled("TRAIN"),require_heldout_sequences=True)


def test_fit_rejects_missing_labels_and_one_class():
    with pytest.raises(ValueError):
        TemporalStateProbe.fit(make_labeled("TRAIN").drop(columns=["label"]))
    with pytest.raises(ValueError):
        TemporalStateProbe.fit(make_labeled("TRAIN").assign(label="one"))
    with pytest.raises(ValueError):
        TemporalStateProbe.fit(make_labeled("TRAIN"),feature_set="fake")


def test_future_frames_do_not_modify_past_phase_scores():
    train=make_labeled("TRAIN")
    full=make_labeled("HOLDOUT").drop(columns=["label"])
    classifier=TemporalStateProbe.fit(train)
    a=classifier.predict(full)
    last=full[full["frame"]<=4]
    b=classifier.predict(last)
    key=["sequence","track_id","frame"]
    m=a.merge(b,on=key,suffixes=("_full","_prefix"))
    assert len(m)==len(last)
    np.testing.assert_allclose(
        m["score_of_predicted_state_full"],
        m["score_of_predicted_state_prefix"],rtol=0,atol=1e-12,
    )
