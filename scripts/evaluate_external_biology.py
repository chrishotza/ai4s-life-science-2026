#!/usr/bin/env python
"""Grouped external-biology evaluation for processed time-lapse tables.

Designed for GIDE/S-BIAD2515-style tables that already contain independent
biological labels such as well, dose and time. The script does not download or
recompute raw images; it tests whether numeric phenotype/features carry signal
on held-out biological units.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

METADATA_HINTS = (
    "metadata", "well", "dose", "time", "plate", "site", "field", "fov",
    "object", "track", "cell_id", "label", "split",
)


@dataclass(frozen=True)
class FeatureSet:
    name: str
    regex: str | None = None


def read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".tsv", ".txt"}:
        return pd.read_csv(path, sep="\t")
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported table extension {suffix!r}; use csv, tsv or parquet")


def dose_to_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace("nM", "", regex=False), errors="coerce")


def parse_feature_sets(items: list[str] | None) -> list[FeatureSet]:
    if not items:
        return [FeatureSet("all_numeric", None)]
    out: list[FeatureSet] = []
    for item in items:
        if ":" not in item:
            raise ValueError("--feature-set must be NAME:REGEX")
        name, regex = item.split(":", 1)
        if not name.strip() or not regex.strip():
            raise ValueError(f"Invalid feature set: {item!r}")
        out.append(FeatureSet(name.strip(), regex.strip()))
    return out


def metadata_columns(df: pd.DataFrame, explicit: list[str]) -> set[str]:
    explicit_lower = {c.lower() for c in explicit if c}
    cols: set[str] = set()
    for col in df.columns:
        low = col.lower()
        if low in explicit_lower or any(hint in low for hint in METADATA_HINTS):
            cols.add(col)
    return cols


def numeric_features(df: pd.DataFrame, metadata: set[str], regex: str | None) -> list[str]:
    cols = [c for c in df.columns if c not in metadata and pd.api.types.is_numeric_dtype(df[c])]
    if regex is not None:
        pat = re.compile(regex)
        cols = [c for c in cols if pat.search(c)]
    return cols


def grouped_split(df: pd.DataFrame, y: np.ndarray, group_col: str, seed: int, test_size: float):
    groups = df[group_col].astype(str).to_numpy()
    if len(np.unique(groups)) < 3:
        raise ValueError("Need at least 3 wells/groups for grouped evaluation")
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_idx, test_idx = next(splitter.split(df, y, groups))
    if len(np.unique(y[train_idx])) < 2 or len(np.unique(y[test_idx])) < 2:
        raise ValueError("Grouped split produced a single-class train/test set; use more wells or another seed")
    return train_idx, test_idx


def fit_score(X: pd.DataFrame, y: np.ndarray, train_idx: np.ndarray, test_idx: np.ndarray) -> dict[str, float]:
    model = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", solver="liblinear", random_state=0)),
        ]
    )
    model.fit(X.iloc[train_idx], y[train_idx])
    score = model.predict_proba(X.iloc[test_idx])[:, 1]
    pred = (score >= 0.5).astype(int)
    return {
        "auroc": float(roc_auc_score(y[test_idx], score)),
        "average_precision": float(average_precision_score(y[test_idx], score)),
        "balanced_accuracy": float(balanced_accuracy_score(y[test_idx], pred)),
    }


def evaluate(
    df: pd.DataFrame,
    *,
    well_col: str,
    dose_col: str,
    time_col: str | None,
    control_dose: float,
    positive_min_dose: float,
    seed: int,
    test_size: float,
    feature_sets: list[FeatureSet],
) -> dict[str, object]:
    required = [well_col, dose_col] + ([time_col] if time_col else [])
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    work = df.copy()
    work["__dose_float"] = dose_to_float(work[dose_col])
    work = work.dropna(subset=["__dose_float", well_col]).reset_index(drop=True)
    keep = np.isclose(work["__dose_float"], control_dose) | (work["__dose_float"] >= positive_min_dose)
    work = work[keep].reset_index(drop=True)
    y = pd.Series(~np.isclose(work["__dose_float"], control_dose), index=work.index).astype(int).to_numpy()
    if len(np.unique(y)) != 2:
        raise ValueError("Filtered rows must include both control and treated positives")

    train_idx, test_idx = grouped_split(work, y, well_col, seed, test_size)
    metadata = metadata_columns(work, required) | {"__dose_float"}

    results: list[dict[str, object]] = []
    for fs in feature_sets:
        cols = numeric_features(work, metadata, fs.regex)
        if not cols:
            results.append({"feature_set": fs.name, "status": "no_numeric_columns", "n_features": 0})
            continue

        measured = fit_score(work[cols], y, train_idx, test_idx)
        well_labels = (work.groupby(work[well_col].astype(str))["__dose_float"].mean() >= positive_min_dose).astype(int)
        rng = np.random.default_rng(seed)
        original_group_labels = well_labels.to_numpy()
        shuffled = {"auroc": float("nan"), "average_precision": float("nan"), "balanced_accuracy": float("nan")}
        shuffle_status = "unavailable"
        shuffle_attempts = 0
        for attempt in range(1, 501):
            shuffled_values = rng.permutation(original_group_labels)
            if np.array_equal(shuffled_values, original_group_labels):
                continue
            shuffled_map = dict(zip(well_labels.index.to_numpy(), shuffled_values))
            y_shuffle = work[well_col].astype(str).map(shuffled_map).astype(int).to_numpy()
            if len(np.unique(y_shuffle[train_idx])) == 2 and len(np.unique(y_shuffle[test_idx])) == 2:
                shuffled = fit_score(work[cols], y_shuffle, train_idx, test_idx)
                shuffle_status = "ok"
                shuffle_attempts = attempt
                break

        results.append(
            {
                "feature_set": fs.name,
                "status": "ok",
                "n_features": len(cols),
                "metrics": measured,
                "well_level_shuffle_control": shuffled,
                "shuffle_control_status": shuffle_status,
                "shuffle_attempts": shuffle_attempts,
                "delta_auroc_vs_shuffle": measured["auroc"] - shuffled["auroc"] if np.isfinite(shuffled["auroc"]) else None,
                "delta_ap_vs_shuffle": measured["average_precision"] - shuffled["average_precision"] if np.isfinite(shuffled["average_precision"]) else None,
            }
        )

    split = {
        "train_rows": int(len(train_idx)),
        "test_rows": int(len(test_idx)),
        "train_wells": int(work.iloc[train_idx][well_col].nunique()),
        "test_wells": int(work.iloc[test_idx][well_col].nunique()),
        "control_dose": control_dose,
        "positive_min_dose": positive_min_dose,
    }
    if time_col:
        split["n_timepoints"] = int(work[time_col].nunique())

    return {
        "status": "measured_external_biology_smoke_test",
        "rows_after_filter": int(len(work)),
        "wells_after_filter": int(work[well_col].nunique()),
        "dose_values_after_filter": sorted(map(float, work["__dose_float"].drop_duplicates().tolist())),
        "split": split,
        "results": results,
        "claim_boundary": "Positive metrics indicate tabular biological signal under grouped split; they are not a raw-image, clinical, or competition-score claim.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--well-col", default="Metadata_Well")
    parser.add_argument("--dose-col", default="Metadata_dose")
    parser.add_argument("--time-col", default="Metadata_Time")
    parser.add_argument("--control-dose", default=0.0, type=float)
    parser.add_argument("--positive-min-dose", default=19.53, type=float)
    parser.add_argument("--test-size", default=0.33, type=float)
    parser.add_argument("--seed", default=0, type=int)
    parser.add_argument("--feature-set", action="append", help="Repeatable NAME:REGEX feature-set selector")
    args = parser.parse_args()

    summary = evaluate(
        read_table(args.table),
        well_col=args.well_col,
        dose_col=args.dose_col,
        time_col=args.time_col if args.time_col else None,
        control_dose=args.control_dose,
        positive_min_dose=args.positive_min_dose,
        seed=args.seed,
        test_size=args.test_size,
        feature_sets=parse_feature_sets(args.feature_set),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
