"""Execute the actual CLI product with training and disjoint synthetic tracks."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from scripts.predict_cell_states import run


def examples(sequence):
    rows=[]
    for i,label in ((1,"EarlyMitosis"),(2,"LateMitosis")):
        for frame in range(1,6):
            rows.append(dict(
                sequence=sequence,track_id=i,frame=frame,
                xmin=i*40+frame*i,ymin=i*25,
                width=13+frame+i,height=14+i,label=label,
            ))
    return pd.DataFrame(rows)


def test_train_predict_and_provenance(tmp_path):
    training=tmp_path/"training.csv"
    inputs=tmp_path/"inputs.csv"
    output=tmp_path/"predictions.csv"
    examples("TRAIN").to_csv(training,index=False)
    examples("HOLDOUT").drop(columns=["label"]).to_csv(inputs,index=False)
    record=run(training,inputs,output,feature_set="static_motion")
    scores=pd.read_csv(output)
    assert len(scores)==10
    assert set(scores.predicted_state).issubset({"EarlyMitosis","LateMitosis"})
    assert np.all(scores.score_of_predicted_state.between(0,1))
    assert record["feature_set"]=="static_motion"
    provenance=json.loads(output.with_suffix(".provenance.json").read_text())
    assert provenance["training_sha256"]==record["training_sha256"]
    assert record["training_sequences"]==["TRAIN"]


def test_rejects_training_sequence_in_inference(tmp_path):
    training=tmp_path/"training.csv"
    inputs=tmp_path/"inputs.csv"
    examples("TRAIN").to_csv(training,index=False)
    examples("TRAIN").to_csv(inputs,index=False)
    with pytest.raises(ValueError,match="sequences used for training"):
        run(training,inputs,tmp_path/"bad.csv")


def test_rejects_missing_annotation_features(tmp_path):
    training=tmp_path/"training.csv"
    inputs=tmp_path/"inputs.csv"
    examples("TRAIN").drop(columns=["width"]).to_csv(training,index=False)
    examples("OTHER").to_csv(inputs,index=False)
    with pytest.raises(ValueError,match="Missing train fields"):
        run(training,inputs,tmp_path/"bad.csv")
