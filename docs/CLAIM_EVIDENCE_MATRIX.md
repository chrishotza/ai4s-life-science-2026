# Claim Evidence Matrix

This file is the reviewer-facing evidence map for the submission. It separates what the project may claim from what it must not claim. Every high-value public claim should point to a reproducible artifact, report section, workflow run, or committed JSON file.

## Interpretation policy

The submission is allowed to claim reproducible computational evidence for a temporal cellular phenotype engine. It is not allowed to imply official competition ranking, biological cell-state validation, drug-response validation, or transfer to organ-on-a-chip data.

The confidence-gated phenotype artifact is the final authority for phenotype interpretation permissions on the real CTC CellposeSAM-v2 phenotype profiles:

- `audit_only`: retained for traceability, blocked from motion-phenotype claims.
- `descriptive_low_confidence`: enough temporal history, but reliability is below the descriptive threshold.
- `descriptive_ok`: permitted only as descriptive computational phenotype grouping.

## Permitted claims and evidence

| Claim ID | Public claim | Status | Primary evidence | Allowed wording | Blocked wording |
|---|---|---:|---|---|---|
| CTC-IMG-FULL | The CellposeSAM-v2 image-derived pipeline ran on 168 DIC-C2DH-HeLa frames and produced segmentation, detection, temporal-link, and phenotype artifacts. | Supported | `docs/evidence/ctc/full_sequence_metrics.json`; `docs/evidence/ctc/derived_phenotype_features.csv`; `docs/KAGGLE_WRITEUP.md` | "internal CTC image-derived evaluation" | "official CTC leaderboard score" |
| CTC-REF-ASSOC | Reference-centroid association achieved mean precision 0.99135, recall 0.99322, and F1 0.99228. | Supported with boundary | `docs/RESULTS.md`; `docs/KAGGLE_WRITEUP.md`; `docs/TECHNICAL_REPORT.md` | "association-isolation with reference centroids" | "segmentation score" or "end-to-end image score" |
| CTC-TRA-LNK | External `py-ctcmetrics==1.3.3` association-isolation scoring produced TRA/LNK values above 0.97 on both sequences with preserved reference geometry. | Supported with boundary | `docs/KAGGLE_WRITEUP.md`; `docs/TECHNICAL_REPORT.md` | "reference-geometry association-isolation TRA/LNK" | "official Cell Tracking Challenge leaderboard score" |
| CTC-PHENO-FEATURE | The tracker preserves downstream trajectory-derived phenotype features under the reference-centroid association protocol. | Supported with boundary | `docs/KAGGLE_WRITEUP.md`; `docs/RESULTS.md` | "trajectory-derived phenotype feature preservation" | "biological phenotype classification" |
| CTC-PHENO-STABILITY | Real CTC phenotype clusters are computationally stable enough to report as descriptive groups, but not biological labels. | Supported with boundary | `docs/evidence/ctc/stability_summary.json`; `docs/CTC_REAL_PHENOTYPE_STABILITY.md` | "descriptive unsupervised computational groups" | "validated cell states" |
| CTC-CONFIDENCE-GATE | Of 126 real CTC phenotype profiles, 54 are audit-only, 21 are descriptive low-confidence, and 51 are descriptive OK; 75 are blocked from biological claims. | Supported | `docs/evidence/ctc/confidence_gated_phenotype_summary.json`; `ai4s_phenotype.confidence.gate_phenotype_profiles` | "confidence-gated interpretation permissions" | "all 126 tracks validate phenotypes" |
| ALFI-TEMPORAL-PROBE | In the expert-track ALFI study, temporal motion history improved mitosis-stage macro-F1 from 0.5138 to 0.5676. | Exploratory only | `docs/ALFI_PRODUCT_TEMPORAL_PROBE_RESULTS.md` | "expert-track temporal probe" | "automatic image-to-biological-stage classifier" |
| ALFI-IMAGE-GAP | The ALFI image-domain detection benchmark is weak and exposes a generalization gap. | Supported limitation | `docs/ALFI_PRODUCT_TEMPORAL_PROBE_RESULTS.md`; `docs/KAGGLE_WRITEUP.md` | "generalization gap" | "validated on organ-on-a-chip data" |
| PRODUCT-EXECUTION | The repository contains a runnable microscopy-to-phenotype product entry point that emits observations, tracks, temporal links, phenotype tables, summaries, and visualizations. | Supported | `scripts/analyze_microscopy.py`; `README.md`; `docs/KAGGLE_WRITEUP.md` | "runnable product path" | "universal microscope segmenter" |
| REPRODUCIBILITY | The submission includes deterministic tests, CI, lockfiles, workflow artifacts, provenance hashes, and formal claim audits. | Supported | `.github/workflows/ci.yml`; `scripts/validate_submission_claims.py`; lockfiles; evidence JSON files | "reproducible audit trail" | "clinically validated" |
| VIS-TRACK-CONTINUITY | The video renderer can maintain a stable hue per predicted track ID and suppress visually ambiguous mask associations; a 24-frame whole-field preview exists. | Supported **as a visualization/QA implementation only** | `src/ai4s_imaging/identity_confidence.py`; `docs/VIDEO_V17_FULL_POPULATION_QA.md`; `.github/workflows/ctc-population-identity.yml` | "model-predicted temporal identity with uncertainty-aware rendering" | "biologically verified identical cell across all frames", "validated daughter lineages", or "official Kaggle V17 video" |

## Explicitly blocked claims

The following statements must remain absent from public submission text unless new independent evidence is added:

1. The project wins or matches an official CTC leaderboard result.
2. The reference-centroid association benchmark is an image segmentation benchmark.
3. The unsupervised phenotype clusters are validated biological cell states.
4. The ALFI temporal probe is an automatic image-to-stage product benchmark.
5. The system is validated on organ-on-a-chip data.
6. The confidence-gated CTC groups prove drug response, perturbation response, or disease biology.
7. All 126 real CTC tracks are safe for motion-phenotype interpretation.

## Reviewer-facing summary

The defensible claim is narrower and stronger than an inflated claim: this is a reproducible temporal phenotype engine with explicit evidence gates. The strongest evidence supports the association layer, trajectory-derived feature preservation, runnable image-to-phenotype execution, and confidence-gated descriptive phenotype reporting. The project deliberately blocks biological and leaderboard claims where the evidence does not support them.
