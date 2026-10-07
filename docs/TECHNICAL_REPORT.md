# Technical Report — Temporal Cellular Phenotype Engine

## 1. Project summary

The Temporal Cellular Phenotype Engine is an end-to-end microscopy analysis pipeline designed to turn time-lapse cell observations into interpretable dynamic phenotype profiles.

The core hypothesis is that biological information is often contained not only in a cell's appearance at one frame, but in its trajectory: persistence, motility, temporal stability, division behavior, and lineage context.

The system therefore combines image-to-detection preprocessing, temporal association, 3-D tracking, lineage/event inference, feature extraction, and unsupervised phenotype discovery.

## 2. Problem

Many microscopy workflows provide segmentation masks or tracks but stop before producing a compact, interpretable description of cellular state.

The competition target is single-cell phenotype analysis. The system addresses that target by treating tracking as infrastructure for downstream temporal phenotype discovery.

## 3. System architecture

### 3.1 Microscopy preprocessing

The public baseline uses transparent thresholding and connected components to convert microscopy frames into object centroids and basic intensity/area measurements.

### 3.2 Temporal association

The tracker supports three deterministic association strategies:

1. mutual-nearest-neighbor;
2. globally optimal Hungarian assignment;
3. constant-velocity prediction followed by Hungarian assignment.

Distances can be computed in physical units using sequence-specific voxel sizes.

### 3.3 Lineage and events

Candidate parent-to-daughter events are inferred from terminated tracks and newly appearing nearby tracks. Public Cell Tracking Challenge metadata can also be loaded directly when available.

### 3.4 Temporal phenotype extraction

For each track, the engine computes:

- duration;
- number of observations;
- displacement;
- path length;
- mean speed;
- directional persistence;
- parent count;
- child count;
- descendant count;
- division-event flag.

### 3.5 Phenotype discovery

Standardized temporal features are clustered with K-Means to obtain unsupervised behavioral groups. The clusters are reported together with interpretable feature summaries rather than opaque class IDs alone.

## 4. Data

### 4.1 Synthetic benchmark

The repository contains deterministic microscopy-like image generators and trajectory ground truth for regression testing and controlled perturbation experiments.

### 4.2 Cell Tracking Challenge

The Cell Tracking Challenge publishes freely downloadable 2D+time and 3D+time microscopy datasets, including reference tracking annotations and lineage metadata. The repository includes an adapter for `man_track*.tif` and `man_track.txt` data.

### 4.3 Organ-on-a-chip validation target

A public Organ-on-a-Chip image dataset is identified as a candidate secondary validation source. The exact files, license terms, and preprocessing route must be verified before using it in the final submission.

## 5. Experimental design

The evaluation contains three levels:

### A. Unit and regression tests

Deterministic tests cover image preprocessing, tracking, lineage inference, phenotype extraction, clustering, and public CTC loading.

### B. Controlled synthetic benchmark

Known 3-D trajectories and exact temporal links are used to test association metrics and regression behavior.

### C. Public microscopy benchmark

The CTC experiment uses DIC-C2DH-HeLa sequences 01 and 02. The current association benchmark feeds reference track centroids as detections, isolating the temporal-association problem from segmentation.

### Measured CTC association results

An initial mutual-nearest-neighbor run achieved:

| Sequence | Precision | Recall | F1 |
|---|---:|---:|---:|
| 01 | 1.0000 | 0.8401 | 0.9131 |
| 02 | 0.9977 | 0.8597 | 0.9236 |

A physical-unit ablation at 3.0 µm produced:

| Method | Mean precision | Mean recall | Mean F1 |
|---|---:|---:|---:|
| Hungarian | 0.99734 | 0.90736 | **0.95015** |
| Mutual NN | 0.99734 | 0.90736 | **0.95015** |
| Velocity Hungarian | 0.99730 | 0.89283 | 0.94212 |

For Hungarian at 3.0 µm, the per-sequence F1 values were 0.94192 and 0.95838.

These results indicate that the dominant error is missed association rather than false linkage. The benchmark therefore motivates continuity-recovery experiments rather than indiscriminate gating expansion.

A wider 3.0–8.0 µm sweep is implemented and executed independently to test this hypothesis.

## 6. Baselines and ablations

The final experimental table should compare:

1. mutual nearest neighbor;
2. Hungarian assignment;
3. constant-velocity Hungarian assignment;
4. distance/gating sensitivity;
5. phenotype discovery with and without temporal features.

For each variant, report tracking metrics and downstream phenotype stability.

## 7. Reliability and limitations

The transparent public baseline has known limitations:

- threshold-based segmentation is not robust to all microscopy modalities;
- temporal association can fail under crowding, crossing trajectories, missing detections, and rapid motion;
- lineage inference is candidate-based and should be validated against reference annotations;
- unsupervised clusters are descriptive rather than biological diagnoses;
- the CTC association results use reference centroids and therefore do not measure the full image-to-phenotype pipeline.

These limitations are explicit design constraints rather than hidden assumptions.

## 8. Reproducibility

The repository contains:

- Python package configuration;
- scientific dependencies;
- deterministic synthetic generators;
- automated tests;
- Dockerfile;
- GitHub Actions CI;
- public dataset adapter;
- benchmark scripts;
- demo entry point.

The CI test suite currently passes on Python 3.11.

## 9. Scientific impact

The intended output is a dynamic phenotype representation that can support:

- cell-state characterization;
- motility analysis;
- abnormal-behavior screening;
- lineage-aware phenotype analysis;
- downstream perturbation studies.

## 10. Final submission evidence

The final Kaggle submission should only claim quantitative performance that is directly reproduced by the public repository.

Required evidence before submission:

- at least one real microscopy benchmark;
- quantitative baseline comparison;
- representative visual results;
- limitations/failure cases;
- public code;
- 5-minute demo video;
- final technical report.
