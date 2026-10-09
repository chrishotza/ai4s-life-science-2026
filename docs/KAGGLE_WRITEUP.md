# Temporal Cellular Phenotype Engine

**Submission category: End-to-End System**  
**Impact area: Single-cell Phenotype Analysis**

## Demo video (required)

**Public video URL:** [ADD FINAL PUBLIC VIDEO URL — maximum duration 5 minutes]

The video must play without login, permission requests, or payment. It demonstrates the real workflow, input microscopy, trajectory/phenotype outputs, measured results, and limitations.

## Public code repository (required)

**Repository:** https://github.com/chrishotza/ai4s-life-science-2026

**Important:** The repository was private at the last verified check. Change visibility to public and verify anonymous access before submitting this URL.

## Project summary

Time-lapse microscopy contains information about how cells move and change, but segmentation and tracking alone do not provide an interpretable description of cellular behavior. The Temporal Cellular Phenotype Engine is a reproducible end-to-end pipeline that transforms microscopy observations into trajectory-level temporal phenotype profiles.

The system combines transparent image preprocessing, cell detection, deterministic temporal association, trajectory reconstruction, lineage/event representation, temporal feature extraction, and unsupervised phenotype discovery. For each trajectory, it reports measurements such as duration, displacement, path geometry, mean speed, directional persistence, temporal integrity, and lineage-derived context where available. The goal is to make cellular dynamics easier to compare and inspect, rather than treating a track ID as the final scientific output.

On DIC-C2DH-HeLa sequences 01 and 02 from the Cell Tracking Challenge, a physical-unit sweep selected mutual-nearest-neighbor association with an 8.0 µm gate. Using reference track centroids as detections, this association-isolation benchmark achieved mean precision 0.99135, mean recall 0.99322, and mean edge F1 0.99228. In a downstream trajectory-feature preservation experiment on the same reference centroids, mean trajectory coverage was 0.9451, median coverage 1.0000, and directional-persistence MAE 0.0439.

These results measure temporal association and preservation of trajectory-derived features. They are not image-segmentation scores, biological phenotype classification scores, or official Cell Tracking Challenge leaderboard scores. Controlled synthetic perturbation experiments assess robustness but do not substitute for independent biological validation.

The implementation includes reproducible setup, tests, benchmark scripts, CI, Docker support, and a direct demo entry point. The next validation step is to test phenotype profiles against independently annotated biological perturbations.

## Technical report

**Full technical report:** [ADD PUBLIC REPORT URL IF HOSTED SEPARATELY; otherwise paste the report below this section.]

The report should cover problem and use case, data sources and licenses, architecture, methods, implementation, experimental protocol, results, failure modes and limitations, potential impact, and exact reproduction commands. The repository currently contains the draft at `docs/TECHNICAL_REPORT.md`.

## Reproducibility

The repository README documents environment setup and the `python demo.py` entry point. Quantitative experiments and their claim boundaries are documented in `docs/RESULTS.md` and `docs/CTC_OFFICIAL_VALIDATION.md`. The evaluated CTC association benchmark uses reference centroids as detections, isolating association from segmentation.

## Data use and limitations

The CTC microscopy sequences are public benchmark data downloaded transiently for evaluation and are not redistributed in this repository. Dataset provenance and evaluator versions are recorded in the technical documentation.

The public baseline uses threshold-based segmentation, which is not universal across microscopy modalities. Tracking can fail under crowding, rapid motion, and missing observations; the bounded-gap branch remains experimental. Lineage events are candidate inferences unless validated against reference annotations. Unsupervised phenotype groups are descriptive, and biological validity requires independent labels or perturbation metadata.

## Required external registration

The competition page requires a separate team registration form in addition to the Kaggle Writeup. Complete it before the final submission.