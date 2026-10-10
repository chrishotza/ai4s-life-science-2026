"""Consistency and interpretation checks for focused division-neighborhood QA."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/ctc/segmentation_division_neighborhood_24_frames.json"


def test_consecutive_frame_quality_and_frozen_metrics():
    record = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    frames = record["per_frame"]
    assert len(frames) == 24
    assert [x["frame"] for x in frames] == list(range(34, 58))
    values = [x["segmentation_f1_iou50"] for x in frames]
    assert all(0.0 <= value <= 1.0 for value in values)
    assert sum(values) / len(values) == pytest.approx(
        record["mean_per_frame_segmentation_f1_iou50"], abs=1e-12
    )
    assert record["mean_per_frame_segmentation_f1_iou50"] == pytest.approx(0.9559062589)
    assert record["lowest_frame"]["frame"] == 51
    assert record["predicted_tracks_exported"] == 17
    assert record["predicted_temporal_links_exported"] == 272


def test_division_claim_is_strictly_blocked():
    record = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert "NOT_AUTOMATIC_DIVISION_VALIDATION" in record["status"]
    assert record["source"]["artifact_id"] == 11649936578
    assert "reference lineage metadata used to choose" in record["source"]["selection"].lower()
    assert len(record["source"]["original_metrics_sha256"]) == 64
    assert any("do NOT establish" in caveat for caveat in record["boundaries"])
    assert any("event-enriched" in caveat for caveat in record["boundaries"])
