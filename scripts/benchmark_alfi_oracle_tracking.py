#!/usr/bin/env python3
"""Isolated tracking benchmark on ALFI *oracle* expert detection boxes.

No raw-image inference. Evaluate temporal edges against ALFI DTLTruth IDs,
excluding lineage parent-child events from the temporal-link metric.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ai4s_tracking import TrackingConfig, track_detections

SEQUENCES = tuple(f"MI{i:02d}" for i in range(1, 9))
METHODS = ("mutual_nn", "hungarian", "velocity_hungarian")
MAX_DISTANCE_PIXELS = 45.0


def parse_csv(path: Path, sequence: str) -> pd.DataFrame:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    df = pd.DataFrame(rows)
    needed = {"ImNo", "ID", "xmin", "ymin", "width", "height"}
    if not needed.issubset(df.columns):
        raise ValueError(f"Unexpected ALFI expert DTL schema: {path}")
    for c in needed:
        df[c] = pd.to_numeric(df[c], errors="raise")
    if df[list(needed)].isna().any().any():
        raise ValueError("Non-numeric expert DTL annotation")
    ambiguous = set(df.loc[
        df.duplicated(["ImNo", "ID"], keep=False), "ID"
    ])
    excluded = int(df["ID"].isin(ambiguous).sum())
    if ambiguous:
        df = df.loc[~df["ID"].isin(ambiguous)].copy()
    df.attrs["ambiguous_expert_id_tracks_excluded"] = len(ambiguous)
    df.attrs["ambiguous_expert_rows_excluded"] = excluded
    if (df[["width", "height"]] <= 0).any().any():
        raise ValueError(f"Invalid expert cell dimensions in {sequence}")
    return df


def oracle_edges(df: pd.DataFrame) -> set[tuple[int, int]]:
    expected = set()
    for _, grp in df.groupby("ID"):
        ordered = grp.sort_values("ImNo")
        for i in range(1, len(ordered)):
            source, target = ordered.iloc[i-1], ordered.iloc[i]
            if int(target["ImNo"])-int(source["ImNo"]) == 1:
                expected.add((int(source["observation_id"]), int(target["observation_id"])))
    return expected


def evaluate_sequence(expert: pd.DataFrame, method: str) -> dict:
    detections = pd.DataFrame(dict(
        t=expert["ImNo"].to_numpy(dtype=int),
        z=np.zeros(len(expert)),
        y=(expert["ymin"] + expert["height"]/2).to_numpy(dtype=float),
        x=(expert["xmin"] + expert["width"]/2).to_numpy(dtype=float),
        area=(expert["width"]*expert["height"]).to_numpy(dtype=float),
        observation_id=expert["observation_id"].to_numpy(dtype=int),
    ))
    nodes, edges = track_detections(detections, TrackingConfig(
        max_distance_um=MAX_DISTANCE_PIXELS, method=method,
        voxel_size_um=(1., 1., 1.), max_frame_gap=1,
    ))
    mapping = dict(zip(nodes["node_id"], nodes["observation_id"]))
    predicted = set(
        (int(mapping[int(row.source_id)]), int(mapping[int(row.target_id)]))
        for row in edges.itertuples(index=False)
    )
    gold = oracle_edges(expert)
    true_positive = len(predicted & gold)
    precision = true_positive / len(predicted) if predicted else 0.
    recall = true_positive / len(gold) if gold else 0.
    f1 = 2*precision*recall/(precision+recall) if precision+recall else 0.
    return dict(
        oracle_detections=len(expert),
        oracle_temporal_edges=len(gold),
        predicted_temporal_edges=len(predicted),
        matched_edges=true_positive,
        spurious_edges=len(predicted-gold),
        missed_edges=len(gold-predicted),
        precision=precision, recall=recall, f1=f1,
    )


def run(directory: Path) -> dict:
    prepared = {}
    sha = {}
    annotation_qc = {}
    for seq in SEQUENCES:
        path = directory/f"{seq}_DTLTruth.csv"
        prepared[seq] = parse_csv(path, seq).reset_index(drop=True)
        prepared[seq]["observation_id"] = np.arange(len(prepared[seq]), dtype=int)
        sha[seq] = hashlib.sha256(path.read_bytes()).hexdigest()
        annotation_qc[seq] = dict(
            ambiguous_tracks_excluded=prepared[seq].attrs.get(
                "ambiguous_expert_id_tracks_excluded", 0),
            ambiguous_rows_excluded=prepared[seq].attrs.get(
                "ambiguous_expert_rows_excluded", 0),
        )
    experiments = {}
    for method in METHODS:
        individual = {
            seq: evaluate_sequence(df, method) for seq, df in prepared.items()
        }
        gt = sum(x["oracle_temporal_edges"] for x in individual.values())
        pd_links = sum(x["predicted_temporal_edges"] for x in individual.values())
        tp = sum(x["matched_edges"] for x in individual.values())
        precision = tp/pd_links if pd_links else 0.
        recall = tp/gt if gt else 0.
        experiments[method] = dict(
            true_edges=gt, predicted_edges=pd_links, true_positive=tp,
            false_positive=pd_links-tp, false_negative=gt-tp,
            edge_precision=precision, edge_recall=recall,
            edge_f1=2*tp/(gt+pd_links) if gt+pd_links else 0.,
            per_sequence=individual,
        )
    return dict(
        status="REAL_ALFI_ORACLE_DETECTIONS_TRACKING_EDGE_BENCHMARK",
        dataset="ALFI MI01-MI08 CC BY, DTLTruth.csv",
        n_sequences=len(SEQUENCES),
        total_expert_observations=int(sum(len(x) for x in prepared.values())),
        max_link_distance_in_pixel_units=MAX_DISTANCE_PIXELS,
        max_frame_gap=1,
        methods=experiments,
        source_sha256=sha,
        annotation_qc=annotation_qc,
        limits=(
            "Expert boxes and identity annotations provided every detection; "
            "no raw image detection. This isolates only the repo's tracking "
            "linking. Parent-child lineage and missing-frame gaps are excluded "
            "from the temporal edge gold set. The 45-pixel gating distance "
            "is fixed, and no cross-sequence model training or threshold "
            "optimization is done. Not evidence of end-to-end phenotype "
            "classification nor official Kaggle score."
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--output", type=Path,
                        default=Path("external_biology/alfi_oracle_tracking/summary.json"))
    args = parser.parse_args()
    result = run(args.annotations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        method: {key: val for key, val in record.items() if key != "per_sequence"}
        for method, record in result["methods"].items()
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
