#!/usr/bin/env python3
"""Frozen MI01-MI04 train vs MI05-MI08 test of actual TemporalStateProbe.

Independent of segmenter quality: ALL object boxes/IDs here are oracle expert
ALFI annotations. The full ALFI corpus has been explored previously, so this
is not an untouched/prospective external validation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sklearn.metrics import f1_score, balanced_accuracy_score, confusion_matrix

from ai4s_phenotype import TemporalStateProbe
from scripts.evaluate_alfi_expert_labels import load_annotations

TRAIN = tuple(f"MI{i:02d}" for i in range(1, 5))
TEST = tuple(f"MI{i:02d}" for i in range(5, 9))
CLASSES = ("EarlyMitosis", "LateMitosis")


def evaluate(inputs: Path) -> dict:
    data = load_annotations(inputs)
    mi = data[data["sequence"].isin(TRAIN + TEST)].copy()
    if set(mi["label"]) != set(CLASSES):
        raise ValueError("Unexpected labels in ALFI MI phenotype table")
    training = mi[mi["sequence"].isin(TRAIN)]
    testing = mi[mi["sequence"].isin(TEST)]
    if len(training) < 200 or len(testing) < 200:
        raise ValueError("Insufficient labeled MI observations")
    results = {}
    for feature_set in ("static", "static_motion"):
        probe = TemporalStateProbe.fit(training, c=0.25, feature_set=feature_set)
        predicted = probe.predict(
            testing.drop(columns=["label"]), require_heldout_sequences=True
        )
        merged = testing[["sequence", "track_id", "frame", "label"]].merge(
            predicted, on=["sequence", "track_id", "frame"],
            how="inner", validate="one_to_one",
        )
        if len(merged) != len(testing):
            raise AssertionError("Lost heldout annotation records")
        y = merged["label"].to_numpy()
        p = merged["predicted_state"].to_numpy()
        results[feature_set] = dict(
            macro_f1=float(f1_score(y, p, labels=CLASSES, average="macro")),
            balanced_accuracy=float(balanced_accuracy_score(y, p)),
            confusion_matrix=confusion_matrix(y, p, labels=CLASSES).tolist(),
            feature_names=list(probe.feature_columns),
            per_sequence={
                seq: {
                    "n":int(sum(merged["sequence"]==seq)),
                    "macro_f1":float(f1_score(
                        y[merged["sequence"]==seq],
                        p[merged["sequence"]==seq],
                        labels=CLASSES,average="macro",zero_division=0))
                } for seq in TEST
            },
            per_class_f1={
                cls:float(f1_score(y,p,labels=[cls],average="macro",zero_division=0))
                for cls in CLASSES
            },
        )
    return dict(
        status="REAL_ALFI_ORACLE_BOX_BIOLOGICAL_LABELS_PRODUCT_PROBE",
        source="ALFI expert PhenoTruth, Antonelli et al, CC BY",
        train_sequences=list(TRAIN), test_sequences=list(TEST),
        train_rows=len(training), test_rows=len(testing),
        train_tracks=int(training[["sequence","track_id"]].drop_duplicates().shape[0]),
        test_tracks=int(testing[["sequence","track_id"]].drop_duplicates().shape[0]),
        model="Identical class-balanced logistic C=0.25, fold/training-only scaling",
        models=results,
        delta_macro_f1_motion_minus_static=(
            results["static_motion"]["macro_f1"]-results["static"]["macro_f1"]
        ),
        claim_boundary=(
            "Expert oracle boxes and identities used as model INPUT, not inferred "
            "microscopy. Static and motion variants use the deployed "
            "ai4s_phenotype.TemporalStateProbe and a frozen chronological-feature "
            "computation. Despite heldout sequences for this split, the ALFI "
            "corpus and MI subgroup were analyzed earlier; these are not "
            "previously unseen confirmatory test sequences. No Kaggle score, "
            "full biological validation or image end-to-end claim."
        ),
    )


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--annotations",required=True,type=Path)
    p.add_argument("--out",type=Path,default=Path(
        "external_biology/alfi_expert/product_state_probe.json"))
    a=p.parse_args()
    report=evaluate(a.annotations)
    a.out.parent.mkdir(exist_ok=True,parents=True)
    a.out.write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps(report,indent=2,allow_nan=False),flush=True)


if __name__=="__main__":
    main()
