#!/usr/bin/env python3
"""Exploratory ALFI assay-specific phenotype classification from EXPERT boxes.

No image model is evaluated; measurements rely on annotated boxes and IDs.
Models were compared after inspecting the global result: no untouched test set.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from scripts.evaluate_alfi_expert_labels import (
    LABELS, STATIC, TEMPORAL, engineer_features, load_annotations,
)

MOTION = [
    "speed_cell_sizes", "area_log_deriv", "width_log_deriv",
    "height_log_deriv", "aspect_deriv", "accel_speed",
]
FEATURE_SETS = {
    "static_bbox": STATIC,
    "static_plus_motion_only": STATIC + MOTION,
    "static_plus_all_past": STATIC + TEMPORAL,
}
DOMAINS = ("MI", "CD", "TP")


def macro_f1_confusions(matrices):
    tp = np.diagonal(matrices, axis1=-2, axis2=-1)
    denom = matrices.sum(axis=-1) + matrices.sum(axis=-2)
    values = np.divide(2 * tp, denom, out=np.zeros_like(tp, dtype=float),
                       where=denom > 0)
    return values.mean(axis=-1)


def grouped_predictions(data, input_features, folds, labels):
    predicted = np.empty(len(data), dtype=object)
    for train, test in folds:
        assert not set(data.iloc[train]["sequence"]) & set(data.iloc[test]["sequence"])
        model = make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            LogisticRegression(C=0.25, class_weight="balanced", max_iter=2000),
        )
        model.fit(data.iloc[train][input_features], labels[train])
        predicted[test] = model.predict(data.iloc[test][input_features])
    return predicted


def evaluate_assay(data, domain, bootstrap=10000, seed=20261009):
    rows = data[data["sequence"].str.startswith(domain)].reset_index(drop=True)
    y = rows["label"].to_numpy()
    groups = rows["sequence"].to_numpy()
    classes = [name for name in LABELS if name in set(y)]
    sequences = np.unique(groups)
    if len(sequences) < 5 or len(classes) < 2:
        raise ValueError("Insufficient independent sequences or distinct labels")
    folds = list(GroupKFold(n_splits=5).split(rows, y, groups))
    preds = {
        name: grouped_predictions(rows, cols, folds, y)
        for name, cols in FEATURE_SETS.items()
    }
    # Deliberate negative control: break alignment of past motion with current
    # phenotype WITHIN each sequence while keeping static boxes unchanged.
    permuted = rows.copy()
    rng = np.random.default_rng(seed)
    for seq in sequences:
        ix = np.flatnonzero(groups == seq)
        permuted.loc[ix, MOTION] = (
            rows.iloc[ix][MOTION].iloc[rng.permutation(len(ix))].to_numpy()
        )
    preds["shuffled_motion_negative"] = grouped_predictions(
        permuted, STATIC + MOTION, folds, y
    )
    scores = {}
    confusion = {}
    for name, pred in preds.items():
        scores[name] = {
            "macro_f1": float(f1_score(y, pred, labels=classes,
                                       average="macro", zero_division=0)),
            "per_class_f1": {
                cls: float(f1_score(y, pred, labels=[cls], average="macro",
                                    zero_division=0)) for cls in classes
            },
        }
        confusion[name] = np.array([
            confusion_matrix(y[groups == seq], pred[groups == seq], labels=classes)
            for seq in sequences
        ])
    # Cluster bootstrap of already held-out predictions (not refitting models).
    picks = np.random.default_rng(seed).integers(
        0, len(sequences), size=(bootstrap, len(sequences))
    )
    baseline_scores = macro_f1_confusions(confusion["static_bbox"][picks].sum(axis=1))
    comparisons = {}
    for name in ("static_plus_motion_only", "static_plus_all_past",
                 "shuffled_motion_negative"):
        sampled_scores = macro_f1_confusions(confusion[name][picks].sum(axis=1))
        delta = sampled_scores - baseline_scores
        comparisons[name] = {
            "delta_macro_f1": (scores[name]["macro_f1"]
                               - scores["static_bbox"]["macro_f1"]),
            "sequence_cluster_bootstrap_95pct": [
                float(v) for v in np.percentile(delta, [2.5, 97.5])
            ],
        }
    sequence_details = []
    for seq in sequences:
        sel = groups == seq
        sequence_details.append({
            "sequence": seq, "n_rows": int(sel.sum()),
            "static_macro_f1": float(f1_score(
                y[sel], preds["static_bbox"][sel], labels=classes,
                average="macro", zero_division=0,
            )),
            "motion_macro_f1": float(f1_score(
                y[sel], preds["static_plus_motion_only"][sel],
                labels=classes, average="macro", zero_division=0,
            )),
        })
    return {
        "assay": domain,
        "n_rows": len(rows),
        "n_sequences": len(sequences),
        "class_counts": {cls: int((y == cls).sum()) for cls in classes},
        "scores": scores,
        "compared_to_static": comparisons,
        "per_sequence": sequence_details,
    }


def evaluate_all(features, bootstrap=10000):
    results = {
        domain: evaluate_assay(features, domain, bootstrap=bootstrap)
        for domain in DOMAINS
    }
    return {
        "status": "EXPLORATORY_POSTHOC_ORACLE_EXPERT_BOXES",
        "protocol": "5-fold GroupKFold by complete imaging sequence. Fixed balanced "
                    "logistic regression C=.25, fold-local scaling and imputation. "
                    "Static boxes vs six past-motion/shape-change derivatives vs "
                    "full past features, plus within-sequence shuffled-motion negative.",
        "datasets": results,
        "claim_limits": (
            "Assay-stratified analyses were defined AFTER inspecting the global "
            "ALFI benchmark and other exploratory models; bootstrap intervals "
            "do NOT correct for subgroup/model selection. Input features use "
            "oracle expert bounding boxes and IDs, not images, detection, or "
            "our AI4S phenotype model. No untouched prospective test, causal "
            "cell-death outcome, or Kaggle score. Some phenotype classes are "
            "absent by design in particular assay families."
        ),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--annotations", type=Path, required=True)
    p.add_argument("--out", type=Path,
                   default=Path("external_biology/alfi_assay_robustness.json"))
    p.add_argument("--bootstrap", type=int, default=10000)
    args = p.parse_args()
    expert = load_annotations(args.annotations)
    features = engineer_features(expert)
    results = evaluate_all(features, bootstrap=args.bootstrap)
    results["annotation_integrity"] = {
        "removed_ambiguous_tracks": expert.attrs.get("removed_ambiguous_tracks", 0),
        "removed_ambiguous_rows": expert.attrs.get("removed_ambiguous_rows", 0),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2, allow_nan=False),
                        encoding="utf-8")
    for assay, entry in results["datasets"].items():
        print(assay, "sequences", entry["n_sequences"], "rows", entry["n_rows"])
        print("F1:", {name: round(item["macro_f1"], 5)
                      for name, item in entry["scores"].items()})
        print("Difference:", entry["compared_to_static"])


if __name__ == "__main__":
    main()
