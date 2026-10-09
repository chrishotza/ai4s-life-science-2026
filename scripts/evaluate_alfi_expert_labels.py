#!/usr/bin/env python3
"""ALFI expert bounding-box label validation. NO images, no learned detections.

A sequence-heldout, leak-audited comparison of static expert bounding-box
geometry against geometry plus PAST-ONLY features from expert track IDs.
Ground-truth boxes are oracle inputs, not inference from microscopy.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ai4s_phenotype import causal_shape_motion_features

LABELS = ["EarlyMitosis", "LateMitosis", "CellDeath", "Multipolar"]
STATIC = ["log_width", "log_height", "log_area", "aspect"]
TEMPORAL = [
    "obs_age", "time_age", "time_step", "speed_cell_sizes",
    "area_log_deriv", "width_log_deriv", "height_log_deriv",
    "aspect_deriv", "accel_speed", "cumulative_motion_size",
]


def load_annotations(path: Path) -> pd.DataFrame:
    rows = []

    def add(name: str, raw: bytes) -> None:
        if not name.endswith("_PhenoTruth.csv") or not raw.startswith(b"ImNo,"):
            return
        seq = Path(name).name.split("_")[0]
        for record in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
            if record["Class"] not in LABELS:
                raise ValueError(f"Unknown phenotype class: {record['Class']}")
            rows.append(dict(
                sequence=seq, frame=int(record["ImNo"]),
                track_id=int(record["ID"]), label=record["Class"],
                xmin=float(record["xmin"]), ymin=float(record["ymin"]),
                width=float(record["width"]), height=float(record["height"]),
            ))

    if path.is_file() and path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.endswith("_PhenoTruth.csv"):
                    add(name, archive.read(name))
    elif path.is_dir():
        for file in sorted(path.rglob("*_PhenoTruth.csv")):
            add(file.name, file.read_bytes())
    else:
        raise ValueError("Pass the downloaded expert-annotation ZIP or CSV folder")

    data = pd.DataFrame(rows)
    if data.empty:
        raise ValueError("No ALFI expert phenotype annotations were found")
    duplicates = data.duplicated(
        subset=["sequence", "track_id", "frame"], keep=False
    )
    ambiguous = set(zip(data.loc[duplicates, "sequence"],
                        data.loc[duplicates, "track_id"]))
    n_rows = len(data)
    if ambiguous:
        data = data.loc[
            [(seq, track) not in ambiguous for seq, track in
             zip(data["sequence"], data["track_id"])]
        ].copy()
    data.attrs["removed_ambiguous_tracks"] = len(ambiguous)
    data.attrs["removed_ambiguous_rows"] = n_rows - len(data)
    return data.sort_values(
        ["sequence", "track_id", "frame"]
    ).reset_index(drop=True)


def engineer_features(data: pd.DataFrame) -> pd.DataFrame:
    """Delegate validated past-only geometry to the real phenotype product API."""
    return causal_shape_motion_features(data)


def evaluate(features: pd.DataFrame, n_splits=5, bootstrap=300) -> dict:
    groups = features["sequence"].to_numpy()
    labels = features["label"].to_numpy()
    splits = list(GroupKFold(n_splits=n_splits).split(features, labels, groups))
    preds = {}
    for name, cols in [
        ("static_bbox", STATIC),
        ("static_plus_past_temporal", STATIC + TEMPORAL),
    ]:
        predictions = np.empty(len(features), dtype=object)
        for train, test in splits:
            assert not (set(groups[train]) & set(groups[test]))
            model = make_pipeline(
                SimpleImputer(strategy="median"),
                StandardScaler(),
                LogisticRegression(
                    C=0.25, max_iter=2000, class_weight="balanced",
                    random_state=0,
                ),
            )
            model.fit(features.iloc[train][cols], labels[train])
            predictions[test] = model.predict(features.iloc[test][cols])
        preds[name] = predictions

    scored = {}
    for name, predictions in preds.items():
        scored[name] = dict(
            macro_f1=float(f1_score(
                labels, predictions, labels=LABELS,
                average="macro", zero_division=0,
            )),
            weighted_f1=float(f1_score(
                labels, predictions, labels=LABELS,
                average="weighted", zero_division=0,
            )),
            balanced_accuracy=float(balanced_accuracy_score(labels, predictions)),
            confusion_matrix=confusion_matrix(
                labels, predictions, labels=LABELS
            ).tolist(),
            per_class_f1={
                cls: float(f1_score(
                    labels, predictions, labels=[cls],
                    average="macro", zero_division=0,
                )) for cls in LABELS
            },
        )
    delta = (scored["static_plus_past_temporal"]["macro_f1"]
             - scored["static_bbox"]["macro_f1"])

    rng = np.random.default_rng(20261009)
    sequences = np.unique(groups)
    bootstrapped = []
    for _ in range(bootstrap):
        sampled = rng.choice(sequences, len(sequences), replace=True)
        sample_indices = np.concatenate(
            [np.flatnonzero(groups == seq) for seq in sampled]
        )
        original = f1_score(
            labels[sample_indices], preds["static_bbox"][sample_indices],
            labels=LABELS, average="macro", zero_division=0,
        )
        temporal = f1_score(
            labels[sample_indices],
            preds["static_plus_past_temporal"][sample_indices],
            labels=LABELS, average="macro", zero_division=0,
        )
        bootstrapped.append(temporal - original)

    return dict(
        status="EXPERT_BBOX_LABELS_NOT_RAW_IMAGE_END_TO_END",
        rows=int(len(features)),
        n_sequences=int(len(sequences)),
        n_tracks=int(features[["sequence", "track_id"]].drop_duplicates().shape[0]),
        labels=dict(Counter(labels)),
        n_folds=n_splits, classes=LABELS, models=scored,
        delta_macro_f1_temporal_minus_static=float(delta),
        cluster_bootstrap_delta_macro_f1_95pct=[
            float(v) for v in np.percentile(bootstrapped, [2.5, 97.5])
        ],
        model_note=(
            "Sequence-heldout GroupKFold, class-balanced LogisticRegression "
            "C=0.25. Fold-local median imputation and standardization. "
            "Past-only geometry and expert annotation track IDs."
        ),
        claim_boundary=(
            "Oracle expert bounding-box geometry, not detections from images. "
            "Phenotype classifier is a simple baseline, NOT AI4S's own "
            "image-to-tracks-to-phenotypes pipeline. Cannot claim superiority, "
            "independent prospective validation, or Kaggle score."
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--output", type=Path,
                        default=Path("external_biology/alfi_geometry_result.json"))
    parser.add_argument("--bootstrap", type=int, default=300)
    args = parser.parse_args()
    raw = load_annotations(args.annotations)
    feats = engineer_features(raw)
    summary = evaluate(feats, bootstrap=args.bootstrap)
    summary["source_annotation_audit"] = {
        "removed_ambiguous_tracks": raw.attrs.get("removed_ambiguous_tracks", 0),
        "removed_ambiguous_rows": raw.attrs.get("removed_ambiguous_rows", 0),
    }
    args.output.parent.mkdir(exist_ok=True, parents=True)
    args.output.write_text(json.dumps(summary, indent=2, allow_nan=False),
                           encoding="utf-8")
    print(json.dumps(summary, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
