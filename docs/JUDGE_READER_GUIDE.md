# Judge Reader Guide

This page is the shortest route through the submission evidence. It is written for reviewers who need to understand the biological question, the validated computational path, and the evidence boundaries without reading every artifact in `docs/` first.

## Biological question

Time-lapse microscopy can show more than where a cell is. It can show how a cell moves, persists, divides, changes direction, and participates in lineage structure. The project asks:

> Can a reproducible AI pipeline turn microscopy movies into interpretable single-cell temporal phenotype profiles while clearly separating validated computation from unvalidated biological interpretation?

The current answer is a measured computational prototype: it can generate trajectory-derived phenotype profiles and confidence-gated descriptive groups from real microscopy tracks. It does **not** claim validated biological cell states, drug response, clinical probabilities, or organ-on-a-chip transfer.

## What to read first

1. `README.md` for the public-facing summary and quick reproduction path.
2. `docs/KAGGLE_WRITEUP.md` for the competition submission narrative.
3. `docs/CLAIM_EVIDENCE_MATRIX.md` for claim-by-claim evidence boundaries.
4. `docs/CTC_CELLPOSE_ARTIFACT_AUDIT.md` and `docs/evidence/ctc/full_sequence_metrics.json` for the strongest image-derived CTC evidence.
5. `docs/SUBMISSION_CHECKLIST.md` for final submission blockers.

## Protocol map

| Protocol | What enters the evaluated component | Main result | What it supports | What it does **not** support |
|---|---|---:|---|---|
| Full image-derived CTC path | Raw DIC-C2DH-HeLa frames -> CellposeSAM-v2 -> tracker -> phenotype profiles | Segmentation F1 0.9354; detection F1 0.9684; tracking-edge F1 0.9808 | The public pipeline can run from raw microscopy to tracks and phenotype profiles on two CTC sequences | Official CTC leaderboard status, biological phenotype discovery, or organ-on-a-chip transfer |
| Association isolation | Reference CTC centroids -> temporal association | Edge-association F1 0.99228 | The linker is strong when object detections are trusted | Image segmentation quality or end-to-end biological interpretation |
| CTC TRA/LNK bridge | Reference geometry preserved -> py-ctcmetrics | TRA about 0.997; LNK about 0.979 | External metric sanity check for association-isolation outputs | Official challenge submission score |
| Real CTC phenotype stability | 126 image-derived tracks -> clustering/stability audit | 54 audit-only, 21 descriptive low confidence, 51 descriptive computational groups | Confidence gates prevent over-reading short tracks | Validated biological cell states |
| ALFI cross-domain segmentation | Raw ALFI phase microscopy -> pretrained instance models | CellposeSAM-v2 instance F1 0.2282 on fixed frames | Cross-domain transfer is weak and honestly bounded | A valid ALFI end-to-end cell-state claim |

## Why CellposeSAM-v2 appears in the strongest path

The transparent threshold segmenter is useful for a no-download smoke test and for inspecting data contracts, but it is not the strongest image segmenter. The strongest current raw-image CTC result uses pretrained CellposeSAM-v2 for instance segmentation, then evaluates the repository's detection, association, and phenotype layers downstream.

That is the intended boundary: segmentation can be a replaceable dependency, while the project contribution is the reproducible route from detections/tracks to temporal phenotype profiles, confidence gates, and claim discipline.

## Phenotype claim boundary

The term phenotype is used operationally: trajectory-derived behavioral descriptors such as duration, speed, displacement, directionality, lineage candidates, and reliability diagnostics. Unsupervised clusters are descriptive computational groups unless an independent biological label or perturbation assay validates them.

The current confidence policy blocks or downgrades weak cases instead of presenting every cluster as biology:

- single-observation or insufficient-history tracks remain auditable but are not safe for motion-phenotype interpretation;
- low-confidence groups are descriptive only;
- biological state, treatment-response, clinical, and organ-on-a-chip claims require evidence not yet present in the repository.

## Final submission risks

The remaining risks are presentation and official submission completeness, not core repository architecture:

- final demo video must be public, under 5 minutes, and viewable without login, approval, or payment;
- Kaggle Writeup and technical report links must be pasted into the official submission flow;
- team roster and registration must match the report;
- organ-on-a-chip transfer remains untested and must stay explicit.

## One-sentence reviewer takeaway

This is not a black-box claim that AI discovered biology. It is a reproducible image-to-trajectory-to-phenotype engine with strong CTC tracking evidence, explicit segmentation dependence, confidence-gated interpretation, and clear boundaries on what remains unvalidated.
