from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs" / "CLAIM_EVIDENCE_MATRIX.md"


REQUIRED_CLAIM_IDS = {
    "CTC-IMG-FULL",
    "CTC-REF-ASSOC",
    "CTC-TRA-LNK",
    "CTC-PHENO-FEATURE",
    "CTC-PHENO-STABILITY",
    "CTC-CONFIDENCE-GATE",
    "ALFI-TEMPORAL-PROBE",
    "ALFI-IMAGE-GAP",
    "PRODUCT-EXECUTION",
    "REPRODUCIBILITY",
}

REQUIRED_BLOCKED_CLAIMS = (
    "official CTC leaderboard result",
    "reference-centroid association benchmark is an image segmentation benchmark",
    "unsupervised phenotype clusters are validated biological cell states",
    "automatic image-to-stage product benchmark",
    "validated on organ-on-a-chip data",
    "All 126 real CTC tracks are safe for motion-phenotype interpretation",
)

REQUIRED_EVIDENCE_FILES = (
    "docs/evidence/ctc/full_sequence_metrics.json",
    "docs/evidence/ctc/derived_phenotype_features.csv",
    "docs/evidence/ctc/stability_summary.json",
    "docs/evidence/ctc/confidence_gated_phenotype_summary.json",
    "scripts/validate_submission_claims.py",
)


def test_claim_evidence_matrix_lists_required_claims_and_boundaries():
    text = MATRIX.read_text(encoding="utf-8")

    for claim_id in sorted(REQUIRED_CLAIM_IDS):
        assert claim_id in text

    for blocked in REQUIRED_BLOCKED_CLAIMS:
        assert blocked in text

    for path in REQUIRED_EVIDENCE_FILES:
        assert path in text

    assert "biological phenotype classification" in text
    assert "official Cell Tracking Challenge leaderboard score" in text
    assert "confidence-gated interpretation permissions" in text


def test_claim_evidence_matrix_keeps_supported_and_blocked_claims_separate():
    text = MATRIX.read_text(encoding="utf-8")
    permitted_section = text.split("## Permitted claims and evidence", 1)[1]
    blocked_section = text.split("## Explicitly blocked claims", 1)[1]

    assert "CTC-CONFIDENCE-GATE" in permitted_section
    assert "75 are blocked from biological claims" in permitted_section
    assert "The system is validated on organ-on-a-chip data" in blocked_section
    assert "All 126 real CTC tracks are safe" in blocked_section
