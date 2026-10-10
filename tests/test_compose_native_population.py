"""Prevent video 'continuity' demos built from repainted or partial masks."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from compose_ctc_population_narrated import validate_native_population


def fixture(tmp_path: Path):
    base = tmp_path / "cellpose_visual_pilot"
    base.mkdir()
    for name in ("model_predicted_instances.npz",
                 "model_predicted_track_nodes.csv",
                 "model_predicted_temporal_edges.csv"):
        (base / name).write_bytes(b"fixture")
    for index in range(24):
        (base / f"pilot_{index:03}.png").write_bytes(b"fixture")
    record = {
        "full_population_mode": True,
        "visualized_frames": 24,
        "first_frame_index": 34,
        "last_frame_index": 57,
        "model_native_colored_ids_by_frame": [[1, 2, 3]] * 24,
        "colors_keyed_by": "model-predicted track_id, NOT per-frame instance_id",
        "no_biological_identity_or_division_claim": True,
        "uncertain_predicted_instances_remain_visible_uncolored": True,
        "predicted_track_count": 8,
        "predicted_temporal_link_count": 50,
    }
    return base, record


def test_native_evidence_is_accepted(tmp_path):
    base, record = fixture(tmp_path)
    info = validate_native_population(record, base)
    assert info["frames"] == 24
    assert info["colored_by_frame"] == [3] * 24
    assert info["native_predicted_tracks"] == 8


@pytest.mark.parametrize("field,bad_value", [
    ("full_population_mode", False),
    ("uncertain_predicted_instances_remain_visible_uncolored", False),
    ("no_biological_identity_or_division_claim", False),
    ("colors_keyed_by", "ephemeral-instance_id"),
    ("first_frame_index", 0),
    ("model_native_colored_ids_by_frame", [[1]] * 23),
])
def test_reject_unproven_continuity_or_wrong_source(tmp_path,field,bad_value):
    base, record = fixture(tmp_path)
    record[field] = bad_value
    with pytest.raises(ValueError):
        validate_native_population(record, base)


def test_native_mask_archive_is_mandatory(tmp_path):
    base, record = fixture(tmp_path)
    (base / "model_predicted_instances.npz").unlink()
    with pytest.raises(FileNotFoundError, match="native predicted masks"):
        validate_native_population(record, base)


def test_all_source_frames_are_required(tmp_path):
    base, record = fixture(tmp_path)
    (base / "pilot_023.png").unlink()
    with pytest.raises(ValueError, match="sequential PNG"):
        validate_native_population(record, base)
