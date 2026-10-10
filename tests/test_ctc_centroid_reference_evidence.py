"""No-inference integrity checks for the 193 verified CTC centroid matches."""
from __future__ import annotations

import copy
import csv
import hashlib
import io
import json

import pytest

from scripts.validate_ctc_centroid_reference_evidence import (
    MATCHES, REPORT, audit, percentile,
)


def test_exact_frozen_real_inference_reconstructs_metrics():
    report=json.loads(REPORT.read_text(encoding="utf-8"))
    output=audit(report,MATCHES.read_bytes())
    assert output["verified_matched_objects"]==193
    assert output["median_offset_um"]==pytest.approx(0.909312,abs=1e-6)
    assert output["p95_offset_um"]==pytest.approx(2.700614,abs=1e-6)
    assert output["source_csv_sha256"]==report["experiment"]["per_match_csv_sha256"]
    assert report["pooled"]["reference_instances"]==199
    assert report["pooled"]["predicted_instances"]==211


def test_detects_changed_output_summary():
    report=json.loads(REPORT.read_text(encoding="utf-8"))
    report["pooled"]["centroid_offset_um"]["p95"]+=0.1
    with pytest.raises(ValueError,match="p95"):
        audit(report,MATCHES.read_bytes())


def test_detects_tampered_file_even_if_numeric_csv_is_parseable():
    report=json.loads(REPORT.read_text(encoding="utf-8"))
    corrupt=MATCHES.read_bytes().replace(b"0.19",b"0.20",1)
    if corrupt==MATCHES.read_bytes():
        corrupt=MATCHES.read_bytes().replace(b"01",b"09",1)
    with pytest.raises(ValueError,match="checksum"):
        audit(report,corrupt)


def test_rejects_object_duplicate_even_when_sha_is_recomputed():
    report=json.loads(REPORT.read_text(encoding="utf-8"))
    rows=list(csv.DictReader(io.StringIO(MATCHES.read_text(encoding="utf-8"))))
    rows.append(rows[0].copy())
    out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    corrupted=out.getvalue().encode()
    report["experiment"]["per_match_csv_sha256"]=hashlib.sha256(corrupted).hexdigest()
    with pytest.raises(ValueError,match="one-to-one"):
        audit(report,corrupted)


def test_percentile_uses_linear_interpolation():
    assert percentile([0.,10.,20.,30.],95)==pytest.approx(28.5)
    assert percentile([1.],95)==1
    with pytest.raises(ValueError):
        percentile([],95)
