"""Verify bounded-error geometry and actual frozen CTC phenotype evidence."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pandas as pd
import pytest

from scripts.audit_ctc_centroid_error_bounds import (
    INPUT,
    STABILITY,
    _classify,
    generate,
    persistence_interval,
)


def test_triangle_inequality_interval_exact_at_zero_error():
    lo, hi = persistence_interval(6, 18.0, 3.6, 0.0)
    assert lo == pytest.approx(0.20)
    assert hi == pytest.approx(0.20)


def test_center_jitter_expands_conservative_interval():
    epsilons = (0.0, 0.05, 0.1, 0.25, 0.5, 1.0)
    intervals = [persistence_interval(66, 142.095316, 4.289433, e) for e in epsilons]
    assert [lo for lo, _ in intervals] == sorted(
        [lo for lo, _ in intervals], reverse=True
    )
    assert [hi for _, hi in intervals] == sorted(hi for _, hi in intervals)
    assert _classify(*intervals[0], .20) == "certain_below"
    assert _classify(*intervals[3], .20) == "certain_below"
    assert _classify(*intervals[-1], .20) == "indeterminate"


def test_no_false_certainty_if_path_error_can_exhaust_total_path():
    lower, upper = persistence_interval(5, 2.0, 0.25, 0.5)
    assert lower == pytest.approx(0.0)
    assert upper == 1.0
    assert _classify(lower, upper, 0.2) == "indeterminate"


@pytest.mark.parametrize(
    "params",
    [(2, 1.0, .5, .1), (3, 2., 3., .1), (3, 1., 0., -.1),
     (3, math.nan, .1, .2)],
)
def test_invalid_physical_inputs_block_analysis(params):
    with pytest.raises(ValueError):
        persistence_interval(*params)


def test_actual_126_profile_export_gate_and_error_sensitivity():
    raw = INPUT.read_bytes()
    data = pd.read_csv(INPUT, dtype={"sequence": str})
    stability = json.loads(STABILITY.read_text(encoding="utf-8"))
    r = generate(data, stability, input_sha=hashlib.sha256(raw).hexdigest())
    assert r["provenance"]["input_profiles"] == 126
    assert r["provenance"]["production_gate_descriptive_profiles"] == 51
    assert r["pixel_size_um_xy"] == .19
    assert r["status"].endswith("NOT_MEASURED_CENTROID_ERROR")
    scenarios = {p["max_centroid_error_um"]: p for p in r["scenarios"]}
    assert scenarios[0.0]["classification_bounds"]["all"] == {
        "n": 51, "observed_below": 33,
        "certain_below": 33, "indeterminate": 0,
        "certain_at_or_above": 18,
    }
    assert scenarios[0.25]["classification_bounds"]["all"]["certain_below"] == 15
    assert scenarios[0.5]["classification_bounds"]["all"]["certain_below"] == 6
    assert scenarios[1.0]["classification_bounds"]["all"]["certain_below"] == 0
    for row in r["scenarios"]:
        assert sum(
            row["classification_bounds"][seq]["n"] for seq in ("01", "02")
        ) == 51
        assert row["classification_bounds"]["all"]["observed_below"] == 33
    assert len(scenarios[0.25]["measured_example_tracks"]) == 2


def test_actual_report_is_order_independent():
    raw = INPUT.read_bytes()
    data = pd.read_csv(INPUT, dtype={"sequence": str})
    stable = json.loads(STABILITY.read_text(encoding="utf-8"))
    sha = hashlib.sha256(raw).hexdigest()
    assert generate(data, stable, input_sha=sha) == generate(
        data.sample(frac=1, random_state=29), stable, input_sha=sha
    )
