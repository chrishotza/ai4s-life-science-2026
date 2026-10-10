"""The abstract must be accurate without duplicating all auxiliary controls."""
from __future__ import annotations

from scripts.validate_submission_claims import (
    CAVEAT_FILES,
    CRITICAL_VALUE_FILES,
    CRITICAL_VALUES,
    ROOT,
    SUMMARY_HEADLINE_VALUES,
)


def test_condensed_summary_keeps_core_image_derived_evidence():
    summary = (ROOT / "docs/KAGGLE_SUMMARY.md").read_text(encoding="utf-8").lower()
    for value in SUMMARY_HEADLINE_VALUES:
        assert value.lower() in summary
    assert "reference centroids" in summary
    assert "biological phenotype classification" in summary
    assert "not official cell tracking challenge leaderboard scores" in summary
    assert "168 raw frames" in summary


def test_detailed_protocol_sources_retain_all_control_scores():
    assert ROOT / "docs/RESULTS.md" in CRITICAL_VALUE_FILES
    assert ROOT / "docs/KAGGLE_WRITEUP.md" in CRITICAL_VALUE_FILES
    assert ROOT / "docs/TECHNICAL_REPORT.md" in CRITICAL_VALUE_FILES
    assert ROOT / "docs/KAGGLE_SUMMARY.md" not in CRITICAL_VALUE_FILES
    for doc in CRITICAL_VALUE_FILES:
        text = doc.read_text(encoding="utf-8")
        for value in CRITICAL_VALUES:
            assert value in text, (str(doc), value)
    assert ROOT / "docs/KAGGLE_SUMMARY.md" in CAVEAT_FILES
