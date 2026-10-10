"""Frozen track-21 case-study audit: all storytelling numbers are real outputs."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/evidence/ctc/derived_phenotype_features.csv"


def test_selected_single_cell_case_is_66_consecutive_real_observations():
    d = pd.read_csv(SOURCE, dtype={"sequence": str})
    hit = d[d["sequence"].eq("02") & d["track_id"].eq(21)]
    assert len(hit) == 1
    row = hit.iloc[0]
    assert int(row["observations"]) == 66
    assert int(row["duration"]) == 65
    assert int(row["observations"]) == int(row["duration"]) + 1
    assert float(row["path_length"]) == pytest.approx(142.095316, abs=1e-5)
    assert float(row["displacement"]) == pytest.approx(4.289433, abs=1e-5)
    assert float(row["directional_persistence"]) == pytest.approx(0.030187, abs=1e-5)
    assert float(row["track_integrity_score"]) >= 0.89
    assert float(row["phenotype_reliability_score"]) >= 0.5
    assert int(row["parent_count"]) == 0
    assert int(row["child_count"]) == 0
