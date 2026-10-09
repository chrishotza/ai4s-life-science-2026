from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import tifffile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from ai4s_core import runtime_metadata
from ai4s_imaging import CellposeSegmenter, instances_to_detections
from ai4s_io import DIC_C2DH_HELA_VOXEL_SIZE_UM, ensure_ctc_dataset, load_ctc_tracking
from ai4s_pipeline import PipelineConfig, TemporalPhenotypeEngine
from ai4s_tracking import TrackingConfig, link_metrics
from benchmark_ctc_tra_supervised import (
    MAX_DISTANCE_UM,
    f1_from_counts,
    frame_index,
    keyed_masks,
    keyed_track_masks,
    marker_overlap_match,
    restrict_instances_to_foi,
    segmentation_score,
    truth_edges,
)
from benchmark_ctc_image_e2e import image_files

MAX_TEST_FRAMES = int(os.environ.get("AI4S_CTC_MAX_TEST_FRAMES", "84"))
if not 1 <= MAX_TEST_FRAMES <= 84:
    raise ValueError("AI4S_CTC_MAX_TEST_FRAMES must be between 1 and 84")
MODEL_NAME = "cpsam_v2"
MIN_SIZE = 200
FLOW_THRESHOLD = 0.4
CELLPROB_THRESHOLD = 0.0
INVERT = False


def evaluate_sequence(
    root: Path,
    sequence: str,
    segmenter: CellposeSegmenter,
    on_frame: Callable[[str, list[dict[str, float]]], None] | None = None,
) -> dict[str, object]:
    paths = image_files(root, sequence)[:MAX_TEST_FRAMES]
    masks_by_time = keyed_masks(root, sequence)
    truth_nodes, _, _ = load_ctc_tracking(root / f"{sequence}_GT" / "TRA")
    eval_paths = [p for p in paths if frame_index(p) in masks_by_time]
    if not eval_paths:
        raise RuntimeError(f"No paired raw images/TRA masks for sequence {sequence}")

    frames: list[np.ndarray] = []
    truth_masks: list[np.ndarray] = []
    predictions: list[np.ndarray] = []
    per_frame: list[dict[str, float]] = []
    for path in eval_paths:
        time_index = frame_index(path)
        frame = np.squeeze(tifffile.imread(path))
        truth = np.squeeze(tifffile.imread(masks_by_time[time_index])).astype(np.int32, copy=False)
        if frame.ndim != 2 or truth.ndim != 2 or frame.shape != truth.shape:
            raise ValueError(f"Invalid image/label pair at {path}: {frame.shape} vs {truth.shape}")
        predicted = restrict_instances_to_foi(segmenter.predict_instances(frame))
        frames.append(frame)
        truth_masks.append(truth)
        predictions.append(predicted)
        score = segmentation_score(truth, predicted)
        score["frame"] = float(time_index)
        per_frame.append(score)
        if on_frame is not None:
            on_frame(sequence, per_frame)
        print(
            f"[cellpose] sequence={sequence} frame={time_index} "
            f"GT={int(score['gt_objects'])} pred={int(score['pred_objects'])} "
            f"F1@IoU50={score['f1_iou50']:.3f}",
            flush=True,
        )

    eval_times = [frame_index(path) for path in eval_paths]
    detections = instances_to_detections(np.stack(frames), np.stack(predictions))
    detections["t"] = detections["t"].map(dict(enumerate(eval_times))).astype(int)
    pipeline_config = PipelineConfig(
        tracking=TrackingConfig(
            max_distance_um=MAX_DISTANCE_UM,
            method="mutual_nn",
            voxel_size_um=DIC_C2DH_HELA_VOXEL_SIZE_UM,
        ),
        phenotype_clusters=3,
        phenotype_random_state=17,
    )
    pipeline_result = TemporalPhenotypeEngine(pipeline_config).run(detections)
    tracked = pipeline_result.nodes
    edges = pipeline_result.temporal_edges
    phenotype_profiles = pipeline_result.discovered

    truth_nodes = truth_nodes[truth_nodes["t"].isin(eval_times)].copy()
    gt_track_masks = keyed_track_masks(root, sequence)
    tp, fp, fn, node_mapping = marker_overlap_match(
        tracked,
        truth_nodes[["node_id", "track_id", "t", "z", "y", "x"]],
        dict(zip(eval_times, predictions)),
        gt_track_masks,
    )
    detection = f1_from_counts(tp, fp, fn)
    gt_edge_df = truth_edges(truth_nodes)
    mapped_edge_pairs = {
        (node_mapping[int(row.source_id)], node_mapping[int(row.target_id)])
        for row in edges.itertuples(index=False)
        if int(row.source_id) in node_mapping and int(row.target_id) in node_mapping
    }
    mapped_edge_df = pd.DataFrame(sorted(mapped_edge_pairs), columns=["source_id", "target_id"])
    edge = link_metrics(mapped_edge_df, gt_edge_df)
    frame_df = pd.DataFrame(per_frame)
    profile_path = ROOT / f"ctc_cellpose_phenotypes_seq{sequence}.csv"
    phenotype_profiles.to_csv(profile_path, index=False)
    profile_columns = [
        "track_id",
        "t_start",
        "t_end",
        "duration",
        "observations",
        "observation_fraction",
        "gap_count",
        "displacement",
        "path_length",
        "mean_speed",
        "directional_persistence",
        "track_integrity_score",
        "phenotype_cluster",
        "phenotype_cluster_name",
        "phenotype_assignment_quality",
        "phenotype_reliability_score",
    ]
    profile_columns = [column for column in profile_columns if column in phenotype_profiles.columns]
    profile_records = []
    for row in phenotype_profiles[profile_columns].to_dict(orient="records"):
        profile_records.append(
            {
                key: (
                    None
                    if pd.isna(value)
                    else value.item()
                    if isinstance(value, (np.integer, np.floating, np.bool_))
                    else value
                )
                for key, value in row.items()
            }
        )
    cluster_counts = (
        phenotype_profiles["phenotype_cluster"]
        .value_counts()
        .sort_index()
        .to_dict()
        if "phenotype_cluster" in phenotype_profiles.columns
        else {}
    )

    return {
        "sequence": sequence,
        "frames_evaluated": len(eval_paths),
        "ground_truth_objects_per_frame_mean": float(frame_df["gt_objects"].mean()),
        "predicted_objects_per_frame_mean": float(frame_df["pred_objects"].mean()),
        "segmentation": {
            "mean_precision_iou50": float(frame_df["precision_iou50"].mean()),
            "mean_recall_iou50": float(frame_df["recall_iou50"].mean()),
            "mean_f1_iou50": float(frame_df["f1_iou50"].mean()),
            "mean_matched_iou": float(frame_df["mean_matched_iou"].mean()),
        },
        "detection": {
            **detection,
            "matching_rule": "one-to-one overlap with CTC GT/TRA marker pixels",
        },
        "tracking": {
            "edge_precision": float(edge["precision"]),
            "edge_recall": float(edge["recall"]),
            "edge_f1": float(edge["f1"]),
            "true_positive_links": float(edge["true_positive"]),
            "false_positive_links": float(edge["false_positive"]),
            "false_negative_links": float(edge["false_negative"]),
        },
        "phenotype": {
            "profile_count": int(len(phenotype_profiles)),
            "candidate_lineage_edges": int(len(pipeline_result.lineage_edges)),
            "descriptive_cluster_counts": {
                str(key): int(value) for key, value in cluster_counts.items()
            },
            "mean_speed_um_per_frame": (
                float(phenotype_profiles["mean_speed"].mean())
                if "mean_speed" in phenotype_profiles and len(phenotype_profiles)
                else None
            ),
            "mean_directional_persistence": (
                float(phenotype_profiles["directional_persistence"].mean())
                if "directional_persistence" in phenotype_profiles and len(phenotype_profiles)
                else None
            ),
            "mean_track_integrity_score": (
                float(phenotype_profiles["track_integrity_score"].mean())
                if "track_integrity_score" in phenotype_profiles and len(phenotype_profiles)
                else None
            ),
            "mean_phenotype_reliability_score": (
                float(phenotype_profiles["phenotype_reliability_score"].mean())
                if "phenotype_reliability_score" in phenotype_profiles and len(phenotype_profiles)
                else None
            ),
            "profiles_csv": profile_path.name,
            "profiles": profile_records,
            "interpretation": (
                "Descriptive trajectory-derived groups from the image-to-track pipeline; "
                "not biologically validated phenotype labels."
            ),
        },
        "mean_frame_metrics": {
            key: float(value) for key, value in frame_df.mean(numeric_only=True).to_dict().items()
        },
    }


def main() -> None:
    dataset_root = ensure_ctc_dataset(ROOT / ".benchmark_cache")
    segmenter = CellposeSegmenter(
        model_name=MODEL_NAME,
        min_size=MIN_SIZE,
        flow_threshold=FLOW_THRESHOLD,
        cellprob_threshold=CELLPROB_THRESHOLD,
        invert=INVERT,
    )
    protocol = {
        "dataset": "DIC-C2DH-HeLa",
        "model": MODEL_NAME,
        "model_source": "upstream pretrained Cellpose model; no CTC evaluation labels used to fit model weights",
        "model_parameters": {
            "min_size": MIN_SIZE,
            "flow_threshold": FLOW_THRESHOLD,
            "cellprob_threshold": CELLPROB_THRESHOLD,
            "invert": INVERT,
        },
        "evaluation": f"first {MAX_TEST_FRAMES} paired frames from each CTC sequence",
        "segmentation_match": "one-to-one instance IoU >= 0.5",
        "detection_match": "one-to-one predicted-instance coverage of >50% of complete-coverage CTC GT/TRA marker pixels",
        "tracking": f"mutual-nearest-neighbor; {MAX_DISTANCE_UM} um gate",
        "phenotype": (
            "TemporalPhenotypeEngine extracts per-track motion, integrity, and descriptive "
            "unsupervised groups from the Cellpose-derived observations."
        ),
        "claim_boundary": (
            "Independent pretrained-model inference on raw held-out images. "
            "CTC masks are used only for scoring; GT/TRA markers are matched by predicted-instance "
            "overlap rather than expecting marker-region centroids to equal whole-cell centroids. "
            "This is not an official CTC leaderboard score "
            "The downstream phenotype profiles are measured product outputs but are not scored "
            "against independent biological phenotype labels."
        ),
        "license_note": (
            "Review upstream Cellpose model/weight licensing before redistribution or commercial use."
        ),
    }
    output_path = ROOT / "ctc_cellpose_e2e_results.json"
    sequences: list[dict[str, object]] = []

    def write_checkpoint(
        status: str,
        current_sequence: str | None = None,
        frame_metrics: list[dict[str, float]] | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "status": status,
            "runtime": runtime_metadata(),
            "protocol": protocol,
            "sequences": sequences,
        }
        if current_sequence is not None:
            payload["current_sequence"] = {
                "sequence": current_sequence,
                "frames_evaluated": len(frame_metrics or []),
                "frame_metrics": frame_metrics or [],
                "sequence_summary_pending": True,
            }
        if status == "completed":
            payload["aggregate"] = {
                "mean_segmentation_f1_iou50": float(np.mean([
                    sequence["segmentation"]["mean_f1_iou50"] for sequence in sequences
                ])),
                "mean_detection_f1": float(np.mean([
                    sequence["detection"]["f1"] for sequence in sequences
                ])),
                "mean_tracking_edge_f1": float(np.mean([
                    sequence["tracking"]["edge_f1"] for sequence in sequences
                ])),
            }
        temporary_path = output_path.with_suffix(".json.tmp")
        temporary_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        temporary_path.replace(output_path)

    write_checkpoint("in_progress")
    for sequence_name in ("01", "02"):
        result = evaluate_sequence(
            dataset_root,
            sequence_name,
            segmenter,
            on_frame=lambda name, metrics: write_checkpoint("in_progress", name, metrics),
        )
        sequences.append(result)
        write_checkpoint("in_progress")

    write_checkpoint("completed")
    print(json.dumps(json.loads(output_path.read_text(encoding="utf-8"))["aggregate"], indent=2))
    print(f"Evidence written to {output_path}")


if __name__ == "__main__":
    main()
