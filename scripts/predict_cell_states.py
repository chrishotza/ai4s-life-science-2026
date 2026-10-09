#!/usr/bin/env python3
"""Reproducible train-and-predict CLI for expert/predicted track-box CSVs.

Training CSV columns: sequence,track_id,frame,xmin,ymin,width,height,label.
Test CSV needs same fields except label. No future frames or expert class
labels from test are used as predictors. The test must be sequence-disjoint.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from ai4s_phenotype import TemporalStateProbe

REQUIRED=("sequence","track_id","frame","xmin","ymin","width","height")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(train_csv: Path, input_csv: Path, out: Path,
        *, feature_set: str = "static_motion") -> dict:
    train=pd.read_csv(train_csv)
    test=pd.read_csv(input_csv)
    missing_test=set(REQUIRED)-set(test.columns)
    missing_train=(set(REQUIRED)|{"label"})-set(train.columns)
    if missing_train or missing_test:
        raise ValueError(f"Missing train fields {sorted(missing_train)}, "
                         f"input fields {sorted(missing_test)}")
    # Explicitly drop any test labels rather than allowing accidental leakage.
    test=test.drop(columns=["label"],errors="ignore")
    probe=TemporalStateProbe.fit(train,feature_set=feature_set)
    out_data=probe.predict(test,require_heldout_sequences=True)
    out.parent.mkdir(parents=True,exist_ok=True)
    out_data.to_csv(out,index=False)
    record=dict(
        status="SUPERVISED_CAUSAL_ORACLE_OR_PREDICTED_BOX_STATE_PROBE",
        training_sha256=sha256(train_csv),input_sha256=sha256(input_csv),
        train_rows=len(train),test_rows=len(test),
        training_sequences=sorted(probe.training_sequences),
        tested_sequences=sorted(set(out_data.sequence)),
        feature_set=feature_set,feature_names=list(probe.feature_columns),
        model="Balanced logistic C=.25, training-only scaling and imputation",
        results_csv=str(out),
        limits=(
            "State score columns are UNCALIBRATED model probabilities. "
            "Training labels from independent biological annotations required. "
            "Predicted source geometry may contain segmentation/tracking errors; "
            "no official Kaggle or independent clinical result is implied."
        ),
    )
    summary=out.with_suffix(".provenance.json")
    summary.write_text(json.dumps(record,indent=2),encoding="utf-8")
    print(json.dumps(record,indent=2),flush=True)
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--training-boxes",required=True,type=Path)
    p.add_argument("--input-boxes",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--features",choices=("static","static_motion"),
                   default="static_motion")
    args=p.parse_args()
    run(args.training_boxes,args.input_boxes,args.output,
        feature_set=args.features)


if __name__=="__main__":
    main()
