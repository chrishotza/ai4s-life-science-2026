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

A deterministic mutual-nearest-neighbor baseline links detections between adjacent frames under a configurable spatial radius.

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

The Cell Tracking Challenge publishes freely downloadable 2D+time and 3D+time microscopy datasets, including reference tracking annotations and lineage metadata. The repository includes an adapter for `man_track*.tif` and `man_track.txt` data. The exact dataset and sequence used for the final submission must be stated with its conditions of use. 

### 4.3 Organ-on-a-chip validation target

A public Organ-on-a-Chip image dataset contains 3,000+ brightfield microscopy images from multiple cell lines, with sample-quality labels and metadata such as cell type and time after seeding. The dataset is available from Zenodo (DOI 10.5281/zenodo.10203721) under the published dataset terms. A real OoC validation experiment should be added only after the exact files, license terms, and preprocessing route are verified.

## 5. Experimental design

The evaluation should contain three levels:

### A. Unit and regression tests

Verify deterministic behavior of image preprocessing, tracking, lineage inference, phenotype extraction, and clustering.

### B. Controlled synthetic benchmark

Generate trajectories with known motion and temporal links, then measure link precision, recall and F1.

### C. Public microscopy benchmark

Run the complete pipeline on at least one public real microscopy sequence and report:

- detection output;
- number of tracks;
- link precision/recall/F1 where a compatible reference is available;
- lineage/event counts;
- phenotype distribution;
- representative visualizations;
- failure cases.

**Important:** real-data values are intentionally left blank until an actual run is completed.

## 6. Baselines and ablations

The final experimental table should compare:

1. nearest-neighbor association;
2. mutual-nearest-neighbor association;
3. motion-aware or learned association;
4. phenotype discovery with and without temporal features.

For each variant, report tracking metrics and downstream phenotype stability.

## 7. Reliability and limitations

The transparent public baseline has known limitations:

- threshold-based segmentation is not robust to all microscopy modalities;
- nearest-neighbor association can fail under crowding, crossing trajectories, missing detections, and rapid motion;
- lineage inference is candidate-based and should be validated against reference annotations;
- unsupervised clusters are descriptive rather than biological diagnoses.

These limitations are explicit design constraints rather than hidden assumptions.

## 8. Reproducibility

The repository contains:

- Python package configuration;
- lower-bounded scientific dependencies;
- deterministic synthetic generators;
- automated tests;
- Dockerfile;
- GitHub Actions CI;
- public dataset adapter;
- demo entry point.

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
